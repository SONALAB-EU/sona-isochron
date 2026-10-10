"""Final meaning judge, for evaluation only (never used by the repair loop).

A model of another family than Apertus, reached through JUDGE_NAME,
JUDGE_BASE_URL and JUDGE_API_KEY: Qwen3-8B (Q4_K_M GGUF) under llama-server
locally in phase 2, Qwen3-14B (BF16) under vLLM on the HPC; both Apache-2.0.
It runs only after generation, with the Apertus server stopped; this module
refuses to start while the Apertus endpoint (LLM_BASE_URL) answers.
Thinking is off, temperature 0, seed 0.

1. For each source sentence, the judge lists its facts once (judge_facts_v1).
   The list is cached and reused for every system and output.
2. For each output, it marks each fact as kept, dropped or changed, and lists
   any added facts (judge_compare_v1).

Metrics per output: fact recall = kept ÷ facts; added = at least one added fact.

Validation suites: data/nli_controls.jsonl (whole clauses deleted or inserted,
negations) and data/judge_controls_de.jsonl (one qualifier, number or modal
changed, one fact inserted, and same-meaning edits; built by
isochron.data.build_judge_controls). Any judge is validated on both.

    uv run python -m isochron.judge controls --suite hard --compare-prompt perfact_v3   (validation)
    uv run python -m isochron.judge runs RUN_DIR [...] --compare-prompt perfact_v3      (judge run outputs)

Judging is resumable: every answer is cached in results/raw/judge_cache.jsonl
(or the file ISOCHRON_JUDGE_CACHE names, one per cluster job), keyed by the
served model, the prompt and the rendered request, so a second pass only asks
what is missing. --workers N sends N items at once (for vLLM).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from isochron.config import ConfigError, LLMConfig
from isochron.llm import ChatClient
from isochron.prompts import Prompt
from isochron.provenance import git_commit
from isochron.run import backend_info
from isochron.schema import ControlPair, read_jsonl

GENERATION: dict[str, Any] = {
    "temperature": 0.0,
    "max_tokens": 1024,
    "chat_template_kwargs": {"enable_thinking": False},
}
SEED = 0
STATUSES = ("kept", "dropped", "changed")
CACHE = Path(os.environ.get("ISOCHRON_JUDGE_CACHE", "results/raw/judge_cache.jsonl"))


def first_object(raw: str, check) -> tuple[dict | None, str | None]:
    """The first JSON object in raw for which check(obj) returns None (no error)."""
    decoder, error, decoded_error = json.JSONDecoder(), "no JSON object", None
    for m in re.finditer(r"\{", raw):
        try:
            obj, _ = decoder.raw_decode(raw, m.start())
        except json.JSONDecodeError as e:
            error = error if error != "no JSON object" else f"invalid JSON: {e.msg}"
            continue
        problem = check(obj) if isinstance(obj, dict) else "not an object"
        if problem is None:
            return obj, None
        decoded_error = decoded_error or problem  # the outermost object's problem is the informative one
    return None, decoded_error or error


def check_facts(obj: dict) -> str | None:
    facts = obj.get("facts")
    if not isinstance(facts, list) or not facts or not all(isinstance(f, str) and f.strip() for f in facts):
        return 'no non-empty "facts" list of strings'
    return None


def check_compare(n_facts: int):
    def check(obj: dict) -> str | None:
        facts, added = obj.get("facts"), obj.get("added", [])
        if not isinstance(facts, list) or not all(isinstance(f, dict) and f.get("status") in STATUSES for f in facts):
            return 'no "facts" list with kept/dropped/changed statuses'
        if len(facts) != n_facts:
            return f"{len(facts)} judged facts instead of {n_facts}"
        if not isinstance(added, list) or not all(isinstance(a, str) for a in added):
            return '"added" is not a list of strings'
        return None
    return check


def check_added(obj: dict) -> str | None:
    added = obj.get("added")
    if not isinstance(added, list) or not all(isinstance(a, str) for a in added):
        return 'no "added" list of strings'
    return None


def parse_status(raw: str) -> tuple[dict | None, str | None]:
    """A one-word answer: the first kept / changed / dropped in it."""
    m = re.search(r"\b(kept|changed|dropped)\b", raw, re.IGNORECASE)
    return ({"status": m.group(1).lower()}, None) if m else (None, "no kept/changed/dropped in the answer")


PERFACT = "perfact_v3"  # one call per fact (judge_fact_v3) plus one call for added facts (judge_added_v3)


def verdict(judged: dict) -> dict[str, Any]:
    statuses = [f["status"] for f in judged["facts"]]
    added = [a for a in judged.get("added", []) if a.strip(" .…")]  # ignore empty and "..." placeholders
    return {"recall": statuses.count("kept") / len(statuses), "n_facts": len(statuses),
            "dropped": statuses.count("dropped"), "changed": statuses.count("changed"),
            "added": len(added), "added_any": bool(added)}


class Judge:
    def __init__(self, compare_prompt: str = "judge_compare_v1", quantisation: str | None = None) -> None:
        try:
            self.config = LLMConfig.from_env(prefix="JUDGE")
        except ConfigError as e:
            sys.exit(f"{e}: the judge needs JUDGE_NAME, JUDGE_BASE_URL and JUDGE_API_KEY")
        self._refuse_if_apertus_is_up()
        self.backend = backend_info(self.config)
        self.backend.pop("samplers", None)  # judge requests send no sampler order; temperature 0 is greedy
        path = str(self.backend.get("model_path") or "") + " " + self.config.name
        if "apertus" in path.lower():
            sys.exit(f"the judge endpoint serves {path!r}: the judge must not be Apertus")
        quant = re.search(r"(?i)(Q\d_K_[MSL]|Q\d_\d|Q\d_K|F16|BF16)", str(self.backend.get("model_path") or ""))
        self.quantisation = quantisation or (quant.group(1).upper() if quant else "unknown")
        self.client = ChatClient(self.config, timeout=300)
        self.facts_prompt = Prompt.load("judge_facts_v1")
        self.perfact = compare_prompt == PERFACT
        if self.perfact:
            self.fact_prompt, self.added_prompt = Prompt.load("judge_fact_v3"), Prompt.load("judge_added_v3")
            self.compare_prompts = [self.fact_prompt, self.added_prompt]
        else:
            self.compare_prompt = Prompt.load(compare_prompt)
            self.compare_prompts = [self.compare_prompt]
        self.cache = self._load_cache()
        self._lock = threading.Lock()
        self._inflight: dict[str, Future] = {}

    def _refuse_if_apertus_is_up(self) -> None:
        try:
            apertus = LLMConfig.from_env()
        except ConfigError:
            return
        if apertus.base_url == self.config.base_url:
            sys.exit("JUDGE_BASE_URL equals LLM_BASE_URL: the judge must be a separate server")
        try:
            httpx.get(f"{apertus.base_url}/models", headers={"Authorization": f"Bearer {apertus.api_key}"}, timeout=3)
        except httpx.TransportError:
            return  # nothing listens: the Apertus server is stopped
        sys.exit(f"the Apertus endpoint {apertus.base_url} still answers: stop it before running the judge")

    def _load_cache(self) -> dict[str, dict]:
        if not CACHE.exists():
            return {}
        return {e["key"]: e for e in map(json.loads, CACHE.read_text(encoding="utf-8").splitlines()) if e}

    def _ask(self, kind: str, prompt: Prompt, parse, lang: str, text: str,
             max_tokens: int | None = None, **values: Any) -> dict:
        """parse(raw) -> (parsed object or None, error or None)."""
        rendered = prompt.render(lang, None, text, **values)
        served = f"{self.config.name}\0{self.backend.get('model_path')}\0{self.backend.get('build_info')}"
        extra = f"\0max_tokens={max_tokens}" if max_tokens else ""
        key = hashlib.sha256(f"{kind}\0{served}\0{prompt.sha256}\0{rendered}{extra}".encode()).hexdigest()
        with self._lock:  # one request per key, even when several threads need it at once
            if key in self.cache:
                return self.cache[key]
            pending, owner = self._inflight.get(key), key not in self._inflight
            if owner:
                pending = self._inflight[key] = Future()
        if not owner:
            return pending.result()
        try:
            gen = {**GENERATION, **({"max_tokens": max_tokens} if max_tokens else {})}
            res = self.client.chat([{"role": "user", "content": rendered}], seed=SEED, **gen)
            obj, error = parse(res.text)
            entry = {"key": key, "kind": kind, "raw": res.text, "parsed": obj, "error": error,
                     "finish_reason": res.finish_reason, "timings": res.raw.get("timings")}
            with self._lock:
                CACHE.parent.mkdir(parents=True, exist_ok=True)
                with open(CACHE, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                self.cache[key] = entry
                del self._inflight[key]
        except BaseException as e:
            with self._lock:
                del self._inflight[key]
            pending.set_exception(e)
            raise
        pending.set_result(entry)
        return entry

    def facts(self, source: str, lang: str) -> list[str] | None:
        e = self._ask("facts", self.facts_prompt, lambda raw: first_object(raw, check_facts), lang, source)
        return [f.strip() for f in e["parsed"]["facts"]] if e["parsed"] else None

    def compare(self, facts: list[str], output: str, lang: str, original: str) -> dict[str, Any]:
        """v1 sees only the fact list; v2 also sees the original; perfact_v3 asks one question per fact."""
        if self.perfact:
            judged_facts = []
            for f in facts:
                e = self._ask("fact", self.fact_prompt, parse_status, lang, output, max_tokens=16,
                              original=original, fact=f)
                if not e["parsed"]:
                    return {"valid": False, "error": f"fact answer: {e['error']}"}
                judged_facts.append({"fact": f, "status": e["parsed"]["status"]})
            e = self._ask("added", self.added_prompt, lambda raw: first_object(raw, check_added), lang, output,
                          original=original)
            if not e["parsed"]:
                return {"valid": False, "error": f"added answer: {e['error']}"}
            judged = {"facts": judged_facts, "added": e["parsed"]["added"]}
            return {"valid": True, **verdict(judged), "judged": judged}
        listing = "\n".join(f"{i}. {f}" for i, f in enumerate(facts, 1))
        e = self._ask("compare", self.compare_prompt, lambda raw: first_object(raw, check_compare(len(facts))),
                      lang, output, facts=listing, original=original, n_facts=len(facts))
        if not e["parsed"]:
            return {"valid": False, "error": e["error"]}
        return {"valid": True, **verdict(e["parsed"]), "judged": e["parsed"]}

    def describe(self) -> dict[str, Any]:
        return {"model": self.config.name, "endpoint": self.config.base_url, "backend": self.backend,
                "quantisation": self.quantisation, "generation": GENERATION, "seed": SEED,
                "mode": PERFACT if self.perfact else "single call",
                "prompts": {p.name: p.sha256 for p in (self.facts_prompt, *self.compare_prompts)}}


def complete(v: dict[str, Any]) -> bool:
    return v["recall"] == 1 and not v["added_any"]


SUITES: dict[str, dict[str, Any]] = {
    "nli": {
        "file": Path("data/nli_controls.jsonl"),
        "about": "20 German and 20 French FLEURS train sentences × 5 control types",
        "expected": {
            "identity": ("recall 1, nothing added", complete),
            "paraphrase": ("recall 1, nothing added", complete),
            "clause_deleted": ("recall < 1, nothing added", lambda v: v["recall"] < 1 and not v["added_any"]),
            "clause_inserted": ("recall 1, something added", lambda v: v["recall"] == 1 and v["added_any"]),
            "negation": ("recall < 1", lambda v: v["recall"] < 1),
        },
        "nli": {
            "identity": lambda m: m.kept, "paraphrase": lambda m: m.kept,
            "clause_deleted": lambda m: m.dropped and not m.added,
            "clause_inserted": lambda m: m.added and not m.dropped, "negation": lambda m: not m.kept,
        },
        "nli_rule": "identity and paraphrase kept; deletion dropped only; insertion added only; negation not kept",
    },
    "hard": {
        "file": Path("data/judge_controls_de.jsonl"),
        "about": ("60 German FLEURS train sentences, each paired with itself; 40 with one modal, number or qualifier "
                  "change, 20 with one inserted fact, and 20 of the changed ones also with a same-meaning edit"),
        "expected": {
            "identity": ("complete: recall 1, nothing added", complete),
            "same_meaning": ("complete: recall 1, nothing added", complete),
            "modal_changed": ("not complete", lambda v: not complete(v)),
            "number_changed": ("not complete", lambda v: not complete(v)),
            "qualifier_changed": ("not complete", lambda v: not complete(v)),
            "fact_inserted": ("something added", lambda v: v["added_any"]),
        },
        "nli": {
            "identity": lambda m: m.kept, "same_meaning": lambda m: m.kept,
            "modal_changed": lambda m: not m.kept, "number_changed": lambda m: not m.kept,
            "qualifier_changed": lambda m: not m.kept, "fact_inserted": lambda m: m.added,
        },
        "nli_rule": "identity and same meaning kept; a changed modal, number or qualifier not kept; an inserted "
                    "fact added",
    },
}
CHANGED = ("modal_changed", "number_changed", "qualifier_changed")


def control_half(pairs: list[ControlPair], half: str, suite: str = "nli") -> list[ControlPair]:
    """Half A tunes judge prompts, half B is held out.

    nli:  per language, the 10 base sentences with the lowest FLEURS ids are half A.
    hard: per edit type (modal, number, qualifier, inserted), the lower half of the base sentences by FLEURS id
          is half A; a sentence's identity and same-meaning pairs go with it.
    """
    if half == "all":
        return pairs
    if suite == "nli":
        def group(p: ControlPair) -> str:
            return p.lang
    else:
        kind = {p.fleurs_id: p.control for p in pairs if p.control not in ("identity", "same_meaning")}

        def group(p: ControlPair) -> str:
            return kind[p.fleurs_id]
    keep = set()
    for g in {group(p) for p in pairs}:
        ids = sorted({int(p.fleurs_id) for p in pairs if group(p) == g})
        chosen = ids[: len(ids) // 2] if half == "A" else ids[len(ids) // 2:]
        keep |= {(g, str(i)) for i in chosen}
    return [p for p in pairs if (group(p), p.fleurs_id) in keep]


def controls(out_path: Path, half: str = "all", compare_prompt: str = "judge_compare_v1", suite: str = "nli",
             quantisation: str | None = None, workers: int = 1) -> None:
    from isochron.metrics.meaning import NLI

    spec = SUITES[suite]
    expected = spec["expected"]
    pairs = control_half(list(read_jsonl(spec["file"], ControlPair)), half, suite)
    judge = Judge(compare_prompt, quantisation)
    started = datetime.now(timezone.utc)

    def one(p: ControlPair) -> tuple[ControlPair, list[str] | None, dict]:
        facts = judge.facts(p.source, p.lang)
        v = judge.compare(facts, p.output, p.lang, p.source) if facts else {"valid": False, "error": "no facts"}
        return p, facts, v

    with ThreadPoolExecutor(max_workers=workers) as pool:
        rows = list(pool.map(one, pairs))
    for i, (p, _, v) in enumerate(rows, 1):
        print(f"  {i}/{len(pairs)} {p.id}: {v.get('recall', '-')} added {v.get('added', '-')}"
              f"{'' if v['valid'] else ' INVALID ' + v['error']}", flush=True)
    nli = NLI()
    meanings = nli.meaning([p.source for p in pairs], [p.output for p in pairs])

    langs = sorted({p.lang for p in pairs})
    table = ["| Control | Expected (judge) | " + " | ".join(lang.upper() for lang in langs) + " | All | NLI, all |",
             "|---------|------------------|" + "---:|" * (len(langs) + 2)]
    accuracies = []
    for control, (expect, ok_if) in expected.items():
        cells = []
        for lang in (*langs, None):
            sel = [(p, v) for p, _, v in rows if p.control == control and lang in (None, p.lang)]
            ok = sum(v["valid"] and ok_if(v) for _, v in sel)
            cells.append(f"{100 * ok / len(sel):.0f} % ({ok}/{len(sel)})" if sel else "–")
            if lang is None and sel:
                accuracies.append(ok / len(sel))
        nli_ok = [spec["nli"][control](m) for p, m in zip(pairs, meanings) if p.control == control]
        cells.append(f"{100 * sum(nli_ok) / len(nli_ok):.0f} % ({sum(nli_ok)}/{len(nli_ok)})" if nli_ok else "–")
        table.append(f"| {control} | {expect} | " + " | ".join(cells) + " |")

    valid = [(p, v, m) for (p, _, v), m in zip(rows, meanings) if v["valid"]]
    agree = sum(complete(v) == m.kept for _, v, m in valid)
    agree_text = f"{agree}/{len(valid)} = {100 * agree / len(valid):.0f} %" if valid else "– (no valid judge answers)"
    invalid = [(p, v) for p, _, v in rows if not v["valid"]]
    wrong = [(p, v) for p, _, v in rows if v["valid"] and not expected[p.control][1](v)]
    extra = []
    if suite == "hard":
        flagged = [v for p, _, v in rows if p.control in CHANGED and v["valid"] and not complete(v)]
        by_fact = sum(v["recall"] < 1 for v in flagged)
        extra = [f"Of the {len(flagged)} changed pairs the judge does not call complete, {by_fact} are caught through "
                 "a fact marked changed or dropped, the rest only through added information.", ""]
    lines = [
        f"# Meaning judge validation: {'NLI control suite' if suite == 'nli' else 'hard controls (German)'}",
        "",
        f"- Date: {started:%Y-%m-%d %H:%M} UTC",
        f"- Git commit: {git_commit()}",
        f"- Judge: {json.dumps(judge.describe(), ensure_ascii=False)}",
        f"- NLI (last column and agreement): {nli.describe()}",
        "- TTS: none. Seeds: judge seed 0 at temperature 0 (greedy)",
        f"- n: {len(pairs)} pairs, half {half} of {spec['file']} (all = {spec['about']}; half A tunes judge prompts, "
        "half B is held out; see isochron.judge.control_half)",
        f"- Invalid judge answers: {len(invalid)}",
        f"- Mean accuracy over the {len(accuracies)} control types: "
        + (f"{100 * sum(accuracies) / len(accuracies):.0f} %" if accuracies else "–"),
        "",
        "A pair counts as judged correctly when the judge's verdict matches its control type. The last column",
        f"repeats the NLI on the same pairs (its rule: {spec['nli_rule']}).",
        "",
        *table,
        "",
        *extra,
        f"Agreement between the judge and the NLI on \"kept\" (judge: recall 1 and nothing added; NLI: entailment both "
        f"ways): {agree_text}.",
        "",
        f"## Pairs judged wrong ({len(wrong)}) or invalid ({len(invalid)})",
        "",
        "| Id | Recall | Added | Edit | Output |",
        "|----|-------:|------:|------|--------|",
        *[f"| {p.id} | {v['recall']:.2f} | {v['added']} | {p.note or ''} | {p.output} |" for p, v in wrong],
        *[f"| {p.id} | invalid | {v['error']} | {p.note or ''} | {p.output} |" for p, v in invalid],
    ]
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {out_path.resolve()}")


def judge_runs(runs: list[Path], compare_prompt: str = "judge_compare_v1", quantisation: str | None = None,
               workers: int = 1) -> None:
    """Judge both conditions of every item of each run; writes judge.jsonl and judge_config.json into the run."""
    judge = Judge(compare_prompt, quantisation)
    for run in runs:
        cfg = json.loads((run / "config.json").read_text(encoding="utf-8"))
        items = [json.loads(line) for line in open(run / "items.jsonl", encoding="utf-8") if line.strip()]

        def one(it: dict[str, Any]) -> dict[str, Any]:
            facts = judge.facts(it["input"], cfg["lang"])
            res: dict[str, Any] = {"id": it["id"], "level": it["level"], "seed": it["seed"], "facts": facts}
            for cond, cand in (("without", it.get("closest_round0")), ("with", it.get("final"))):
                if not facts:
                    res[cond] = {"valid": False, "error": "no facts for the source"}
                elif not cand:  # no output keeps no fact; whether it adds any is undefined
                    res[cond] = {"valid": True, "no_output": True, "recall": 0.0, "added_any": None}
                else:
                    res[cond] = judge.compare(facts, cand["text"], cfg["lang"], it["input"])
            return res

        with ThreadPoolExecutor(max_workers=workers) as pool:
            out = []
            for i, res in enumerate(pool.map(one, items), 1):
                out.append(res)
                print(f"  {run.name} {i}/{len(items)} {res['id']} L{res['level']} s{res['seed']}: "
                      f"without {res['without'].get('recall', '-')} / with {res['with'].get('recall', '-')}", flush=True)
        (run / "judge.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out), encoding="utf-8")
        (run / "judge_config.json").write_text(json.dumps({"date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                                            "git_commit": git_commit(), **judge.describe()},
                                                           ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {run / 'judge.jsonl'}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Final meaning judge (evaluation only).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("controls", help="validate the judge on a control suite")
    c.add_argument("--suite", choices=sorted(SUITES), default="nli")
    c.add_argument("--out", type=Path, help="default: results/judge_validation_<suite>.md")
    c.add_argument("--half", choices=("A", "B", "all"), default="all")
    for name, p in (("runs", sub.add_parser("runs", help="judge run directories")),
                    ("pilot", sub.add_parser("pilot", help="the same as runs (kept for the phase 2 commands)"))):
        p.add_argument("runs", type=Path, nargs="+")
    for p in sub.choices.values():
        p.add_argument("--compare-prompt", default="judge_compare_v1", help=f"judge_compare_v1, judge_compare_v2 or {PERFACT}")
        p.add_argument("--quantisation", help="what the judge server serves, if not in its model path (e.g. BF16)")
        p.add_argument("--workers", type=int, default=1, help="requests in flight at once")
    args = ap.parse_args()
    if args.cmd == "controls":
        controls(args.out or Path(f"results/judge_validation_{args.suite}.md"), args.half, args.compare_prompt,
                 args.suite, args.quantisation, args.workers)
    else:
        judge_runs(args.runs, args.compare_prompt, args.quantisation, args.workers)


if __name__ == "__main__":
    main()
