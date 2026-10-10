"""Final meaning judge, for evaluation only (never used by the repair loop).

Qwen3-8B (Q4_K_M GGUF, Apache-2.0, a different model family from Apertus),
served by llama-server and reached through JUDGE_NAME, JUDGE_BASE_URL and
JUDGE_API_KEY. It runs only after generation, with the Apertus server stopped;
this module refuses to start while the Apertus endpoint (LLM_BASE_URL) answers.
Thinking is off, temperature 0, seed 0.

1. For each source sentence, the judge lists its facts once (judge_facts_v1).
   The list is cached and reused for every system and output.
2. For each output, it marks each fact as kept, dropped or changed, and lists
   any added facts (judge_compare_v1).

Metrics per output: fact recall = kept ÷ facts; added = at least one added fact.

    uv run python -m isochron.judge controls              (validation on the NLI control suite)
    uv run python -m isochron.judge pilot RUN_DIR [...]   (judge pilot outputs)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import defaultdict
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
CACHE = Path("results/raw/judge_cache.jsonl")


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


def verdict(judged: dict) -> dict[str, Any]:
    statuses = [f["status"] for f in judged["facts"]]
    added = [a for a in judged.get("added", []) if a.strip(" .…")]  # ignore empty and "..." placeholders
    return {"recall": statuses.count("kept") / len(statuses), "n_facts": len(statuses),
            "dropped": statuses.count("dropped"), "changed": statuses.count("changed"),
            "added": len(added), "added_any": bool(added)}


class Judge:
    def __init__(self, compare_prompt: str = "judge_compare_v1") -> None:
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
        self.quantisation = quant.group(1).upper() if quant else "unknown"
        self.client = ChatClient(self.config, timeout=300)
        self.facts_prompt, self.compare_prompt = Prompt.load("judge_facts_v1"), Prompt.load(compare_prompt)
        self.cache = self._load_cache()

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

    def _ask(self, kind: str, prompt: Prompt, check, lang: str, text: str, **values: Any) -> dict:
        rendered = prompt.render(lang, None, text, **values)
        served = f"{self.config.name}\0{self.backend.get('model_path')}\0{self.backend.get('build_info')}"
        key = hashlib.sha256(f"{kind}\0{served}\0{prompt.sha256}\0{rendered}".encode()).hexdigest()
        if key in self.cache:
            return self.cache[key]
        res = self.client.chat([{"role": "user", "content": rendered}], seed=SEED, **GENERATION)
        obj, error = first_object(res.text, check)
        entry = {"key": key, "kind": kind, "raw": res.text, "parsed": obj, "error": error,
                 "finish_reason": res.finish_reason, "timings": res.raw.get("timings")}
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        with open(CACHE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self.cache[key] = entry
        return entry

    def facts(self, source: str, lang: str) -> list[str] | None:
        e = self._ask("facts", self.facts_prompt, check_facts, lang, source)
        return [f.strip() for f in e["parsed"]["facts"]] if e["parsed"] else None

    def compare(self, facts: list[str], output: str, lang: str, original: str) -> dict[str, Any]:
        """v1 prompts see only the fact list; v2 also sees the original sentence."""
        listing = "\n".join(f"{i}. {f}" for i, f in enumerate(facts, 1))
        e = self._ask("compare", self.compare_prompt, check_compare(len(facts)), lang, output,
                      facts=listing, original=original, n_facts=len(facts))
        if not e["parsed"]:
            return {"valid": False, "error": e["error"]}
        return {"valid": True, **verdict(e["parsed"]), "judged": e["parsed"]}

    def describe(self) -> dict[str, Any]:
        return {"model": self.config.name, "endpoint": self.config.base_url, "backend": self.backend,
                "quantisation": self.quantisation, "generation": GENERATION, "seed": SEED,
                "prompts": {p.name: p.sha256 for p in (self.facts_prompt, self.compare_prompt)}}


EXPECTED = {
    "identity": lambda v: v["recall"] == 1 and not v["added_any"],
    "paraphrase": lambda v: v["recall"] == 1 and not v["added_any"],
    "clause_deleted": lambda v: v["recall"] < 1 and not v["added_any"],
    "clause_inserted": lambda v: v["recall"] == 1 and v["added_any"],
    "negation": lambda v: v["recall"] < 1,
}
NLI_EXPECTED = {
    "identity": lambda m: m.kept, "paraphrase": lambda m: m.kept,
    "clause_deleted": lambda m: m.dropped and not m.added,
    "clause_inserted": lambda m: m.added and not m.dropped, "negation": lambda m: not m.kept,
}


def control_half(pairs: list[ControlPair], half: str) -> list[ControlPair]:
    """Half A: per language, the 10 base sentences with the lowest FLEURS ids; half B: the other 10."""
    if half == "all":
        return pairs
    keep = set()
    for lang in {p.lang for p in pairs}:
        ids = sorted({int(p.fleurs_id) for p in pairs if p.lang == lang})
        chosen = ids[: len(ids) // 2] if half == "A" else ids[len(ids) // 2:]
        keep |= {(lang, str(i)) for i in chosen}
    return [p for p in pairs if (p.lang, p.fleurs_id) in keep]


def controls(out_path: Path, half: str = "all", compare_prompt: str = "judge_compare_v1") -> None:
    from isochron.metrics.meaning import NLI

    pairs = control_half(list(read_jsonl(Path("data/nli_controls.jsonl"), ControlPair)), half)
    judge = Judge(compare_prompt)
    started = datetime.now(timezone.utc)
    rows = []
    for i, p in enumerate(pairs, 1):
        facts = judge.facts(p.source, p.lang)
        v = judge.compare(facts, p.output, p.lang, p.source) if facts else {"valid": False, "error": "no facts"}
        rows.append((p, facts, v))
        print(f"  {i}/{len(pairs)} {p.id}: {v.get('recall', '-')} added {v.get('added', '-')}"
              f"{'' if v['valid'] else ' INVALID ' + v['error']}", flush=True)
    nli = NLI()
    meanings = nli.meaning([p.source for p in pairs], [p.output for p in pairs])

    langs = sorted({p.lang for p in pairs})
    table = ["| Control | Expected (judge) | " + " | ".join(lang.upper() for lang in langs) + " | All | NLI, all |",
             "|---------|------------------|" + "---:|" * (len(langs) + 2)]
    for control in EXPECTED:
        cells = []
        for lang in (*langs, None):
            sel = [(p, v) for p, _, v in rows if p.control == control and lang in (None, p.lang)]
            ok = sum(v["valid"] and EXPECTED[control](v) for _, v in sel)
            cells.append(f"{100 * ok / len(sel):.0f} % ({ok}/{len(sel)})")
        nli_ok = [NLI_EXPECTED[control](m) for p, m in zip(pairs, meanings) if p.control == control]
        cells.append(f"{100 * sum(nli_ok) / len(nli_ok):.0f} % ({sum(nli_ok)}/{len(nli_ok)})")
        expect = {"identity": "recall 1, nothing added", "paraphrase": "recall 1, nothing added",
                  "clause_deleted": "recall < 1, nothing added", "clause_inserted": "recall 1, something added",
                  "negation": "recall < 1"}[control]
        table.append(f"| {control} | {expect} | " + " | ".join(cells) + " |")

    valid = [(p, v, m) for (p, _, v), m in zip(rows, meanings) if v["valid"]]
    agree = sum((v["recall"] == 1 and not v["added_any"]) == m.kept for _, v, m in valid)
    agree_text = f"{agree}/{len(valid)} = {100 * agree / len(valid):.0f} %" if valid else "– (no valid judge answers)"
    invalid = [(p, v) for p, _, v in rows if not v["valid"]]
    wrong = [(p, v) for p, _, v in rows if v["valid"] and not EXPECTED[p.control](v)]
    lines = [
        "# Meaning judge validation on the NLI control suite",
        "",
        f"- Date: {started:%Y-%m-%d %H:%M} UTC",
        f"- Git commit: {git_commit()}",
        f"- Judge: {json.dumps(judge.describe(), ensure_ascii=False)}",
        f"- NLI (last column and agreement): {nli.describe()}",
        "- TTS: none. Seeds: judge seed 0 at temperature 0 (greedy)",
        f"- n: {len(pairs)} pairs, half {half} of data/nli_controls.jsonl (all = 20 German and 20 French FLEURS train "
        "sentences × 5 control types; half A = per language the 10 base sentences with the lowest FLEURS ids, "
        "used to tune judge prompts; half B = the other 10, held out)",
        f"- Invalid judge answers: {len(invalid)}",
        "",
        "A pair counts as judged correctly when the judge's verdict matches its control type. The last column",
        "repeats the NLI on the same pairs (its rule: identity and paraphrase kept; deletion dropped only;",
        "insertion added only; negation not kept).",
        "",
        *table,
        "",
        f"Agreement between the judge and the NLI on \"kept\" (judge: recall 1 and nothing added; NLI: entailment both "
        f"ways): {agree_text}.",
        "",
        f"## Pairs judged wrong ({len(wrong)}) or invalid ({len(invalid)})",
        "",
        "| Id | Recall | Added | Output |",
        "|----|-------:|------:|--------|",
        *[f"| {p.id} | {v['recall']:.2f} | {v['added']} | {p.output} |" for p, v in wrong],
        *[f"| {p.id} | invalid | {v['error']} | {p.output} |" for p, v in invalid],
    ]
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {out_path.resolve()}")


def pilot(runs: list[Path], compare_prompt: str = "judge_compare_v1") -> None:
    judge = Judge(compare_prompt)
    for run in runs:
        cfg = json.loads((run / "config.json").read_text(encoding="utf-8"))
        items = [json.loads(line) for line in open(run / "items.jsonl", encoding="utf-8") if line.strip()]
        out = []
        for i, it in enumerate(items, 1):
            facts = judge.facts(it["input"], cfg["lang"])
            res: dict[str, Any] = {"id": it["id"], "level": it["level"], "seed": it["seed"], "facts": facts}
            for cond, cand in (("without", it.get("closest_round0")), ("with", it.get("final"))):
                if not facts:
                    res[cond] = {"valid": False, "error": "no facts for the source"}
                elif not cand:  # no output keeps no fact; whether it adds any is undefined
                    res[cond] = {"valid": True, "no_output": True, "recall": 0.0, "added_any": None}
                else:
                    res[cond] = judge.compare(facts, cand["text"], cfg["lang"], it["input"])
            out.append(res)
            print(f"  {run.name} {i}/{len(items)} {it['id']} L{it['level']}: "
                  f"without {res['without'].get('recall', '-')} / with {res['with'].get('recall', '-')}", flush=True)
        (run / "judge.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out), encoding="utf-8")
        (run / "judge_config.json").write_text(json.dumps({"date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                                            "git_commit": git_commit(), **judge.describe()},
                                                           ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {run / 'judge.jsonl'}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Final meaning judge (evaluation only).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("controls")
    c.add_argument("--out", type=Path, default=Path("results/judge_validation.md"))
    c.add_argument("--half", choices=("A", "B", "all"), default="all")
    c.add_argument("--compare-prompt", default="judge_compare_v1")
    p = sub.add_parser("pilot")
    p.add_argument("runs", type=Path, nargs="+")
    p.add_argument("--compare-prompt", default="judge_compare_v1")
    args = ap.parse_args()
    if args.cmd == "controls":
        controls(args.out, args.half, args.compare_prompt)
    else:
        pilot(args.runs, args.compare_prompt)


if __name__ == "__main__":
    main()
