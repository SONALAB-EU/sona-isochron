"""The Hugging Face dataset (data/hf_dataset/): steps 2 and 4, every output with its per-line scores.

The hackathon template asks for three components; each is a JSONL config with a dev split (exploratory)
and a test split (the reported numbers):
- evaluation dataset: step2_inputs and step4_inputs, one row per test case, with the human reference;
- model response dataset: step2_responses and step4_responses, one row per output of every system,
  seed and setting, with its scores (lengths, fit, the NLI checks, the judge, the language check, rounds);
  judge_controls: the planted meaning controls with every check's verdict;
- metadata: one row per sentence or control pair with its licence and source, and runs: each run's
  configuration (model, quantisation, prompts and their hashes, seeds, commits), without local paths.
Two more configs, both on test sources: native_check, the 50 lines of the native-speaker check as rated
(system labels from the key, the ratings with protocol v2.34's copies for identical pairs, the rater's
comments), and timing, the durations of every timing test (results/time_check/; no audio).

`build` reads the raw runs (results/raw/, not in git) and scores every output as the report tools do
(isochron.pilot_report for step 2, isochron.step4_report for step 4, isochron.meaning_check for the second
NLI): the step 4 test NLI scores come from step4_report's cache; step 4 dev's were never cached, so they
are scored again with the same model and device on this machine, into a working copy of that cache
(--nli-cache), so results/raw/ is only read. `check` recomputes the tables of the results files from the
exported files alone and lists every cell that differs, and every row that one side lacks.

    uv run python -m isochron.hf_export build --out data/hf_dataset --nli-cache FILE
    uv run python -m isochron.hf_export check --dir data/hf_dataset
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np

from isochron.language import check as check_language
from isochron.metrics.length import length
from isochron.pilot_report import answered, ci, complete, rows_for, valid
from isochron.provenance import git_commit
from isochron.step2_report import first_table, paired_diff

RAW = Path("results/raw")
ROLE = {"dev": "exploratory", "test": "reported"}
STEP2 = {"dev": ["20261009T155640Z_pilot_v1_de_dev", "20261009T161226Z_pilot_v2a_de_dev",
                 "20261009T163426Z_pilot_v2b_de_dev", "20261009T165135Z_pilot_v2c_de_dev"],
         "test": ["hpc_8b_step2_de_test", "hpc_8b_step2_fr_test"]}
STEP4 = {"dev": ["hpc_8b_step4_dev"], "test": ["hpc_8b_step4_test", "hpc_8b_step4_test_fr"]}
STEP4_TEST_NLI = RAW / "step4_test_nli_cache.jsonl"
SECOND_NLI = RAW / "meaning_check"
VALIDATION = "results/judge_validation_{suite}_v3_qwen3-14b_hpc_8b.md"
CONFIGS = ("step2_inputs", "step2_responses", "step4_inputs", "step4_responses", "judge_controls", "native_check",
           "timing", "metadata", "runs")
NATIVE = Path("results/native_check")
NATIVE_MARKS = NATIVE / "returned/german_lines_rated_part1.xlsx"  # the rater's marks and comments
NATIVE_AS_RATED = NATIVE / "returned/step4_sheet_de_as_rated.csv"  # the texts as the rater saw them
NATIVE_KEY = NATIVE / "step4_key_de.csv"
TIMING = Path("results/time_check")
TIMING_TESTS = {  # name: durations file, results file, TTS, whether its seconds are valid
    "chatterbox": (TIMING / "durations.csv", "results/time_check.md",
                   "Chatterbox multilingual (chatterbox-tts 0.1.7, MIT), default voice", False),
    "qwen3_tts": (TIMING / "durations_qwen.csv", "results/time_check_qwen.md",
                  "Qwen3-TTS-12Hz-1.7B-CustomVoice @ 0c0e305 (Apache-2.0), voice Aiden", True),
    "qwen3_tts_calibrated": (TIMING / "calibrated/durations.csv", "results/time_check_calibrated.md",
                             "Qwen3-TTS-12Hz-1.7B-CustomVoice @ 0c0e305 (Apache-2.0), voice Aiden", True),
    "demo_voices": (TIMING / "demo_voices/durations.csv", None,
                    "Qwen3-TTS-12Hz-1.7B-CustomVoice @ 0c0e305 (Apache-2.0)", True),
}
LOOPBACK = "local OpenAI-compatible server on loopback (127.0.0.1)"


@lru_cache(maxsize=None)
def language(text: str, lang: str) -> tuple[str, float, bool]:
    c = check_language(text, lang)
    return c.label, c.p, c.wrong


@lru_cache(maxsize=None)
def size(text: str, unit: str, lang: str) -> int:
    return length(text, unit, lang, "espeak")


def scrub(obj: Any) -> Any:
    """A run configuration without local paths: model paths dropped, endpoints named, item id lists dropped."""
    if isinstance(obj, dict):
        return {k: (LOOPBACK if k == "endpoint" else scrub(v)) for k, v in obj.items() if k not in ("model_path", "ids")}
    if isinstance(obj, list):
        return [scrub(v) for v in obj]
    return obj


@lru_cache(maxsize=None)
def fleurs(split: str, lang: str) -> dict[str, dict[str, Any]]:
    path = Path(f"data/fleurs_{lang}_{split}.jsonl")
    return {r["id"]: r for r in map(json.loads, path.read_text(encoding="utf-8").splitlines()) if r}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def judge_fields(v: dict[str, Any] | None, wrong: bool, step: int) -> dict[str, Any]:
    """The judge's verdict on one output; recall as the reports score it (a wrong-language output keeps nothing).
    Valid as each report counts it: step 2 (pilot_report.valid) after that rule, step 4 (step4_report) before."""
    v = v or {}
    judged = v.get("judged") or {}
    recall = 0.0 if wrong else v.get("recall")
    return {"judge_valid": bool(v.get("valid")) and (recall if step == 2 else v.get("recall")) is not None,
            "judge_recall": None if recall is None else float(recall),
            "judge_n_facts": v.get("n_facts"), "judge_dropped": v.get("dropped"), "judge_changed": v.get("changed"),
            "judge_added_count": v.get("added") if isinstance(v.get("added"), int) else None,
            "judge_added_any": None if wrong else v.get("added_any"),
            "judge_facts": [{"fact": f["fact"], "status": f["status"]} for f in judged.get("facts", [])] or None,
            "judge_added": list(judged.get("added", [])) or None}


def run_row(run: str, step: int, split: str, cfg: dict[str, Any], judge_cfg: dict[str, Any] | None) -> dict[str, Any]:
    prompts = cfg["prompts"].values() if "prompts" in cfg else [cfg["prompt"], cfg["revise_prompt"]]
    return {"run": run, "step": step, "split": split, "split_role": ROLE[split], "date": cfg["date"],
            "git_commit": cfg["git_commit"], "model": cfg["model"], "quantisation": cfg["quantisation"],
            "backend": cfg["backend"].get("build_info") or cfg["backend"].get("type"),
            "langs": cfg.get("langs") or [cfg["lang"]], "seeds": cfg["seeds"],
            "prompts": [{"name": p["name"], "sha256": p["sha256"]} for p in prompts],
            "judge_model": judge_cfg["model"] if judge_cfg else None,
            "judge_quantisation": judge_cfg["quantisation"] if judge_cfg else None,
            "judge_git_commit": judge_cfg["git_commit"] if judge_cfg else None,
            "config_json": json.dumps(scrub(cfg), ensure_ascii=False),
            "judge_config_json": json.dumps(scrub(judge_cfg), ensure_ascii=False) if judge_cfg else None}


def step2(split: str) -> tuple[list[dict], list[dict], list[dict]]:
    """step2_inputs, step2_responses and runs rows for one split."""
    inputs: dict[str, dict] = {}
    responses, runs = [], []
    for name in STEP2[split]:
        run = RAW / name
        cfg, rows = rows_for(run)
        judge_cfg = json.loads((run / "judge_config.json").read_text(encoding="utf-8"))
        runs.append(run_row(name, 2, split, cfg, judge_cfg))
        lang, ref = cfg["lang"], fleurs(split, cfg["lang"])
        items = {(it["id"], it["level"], it["seed"]): it for it in read_jsonl(run / "items.jsonl")}
        judged = {(j["id"], j["level"], j["seed"]): j for j in read_jsonl(run / "judge.jsonl")}
        for r in rows:
            it = items[r["id"], r["level"], r["seed"]]
            cand = it["closest_round0"] if r["cond"] == "without" else it["final"]
            case = f"step2/{split}/{lang}/{r['id']}/L{r['level']}"
            inputs.setdefault(case, {
                "case_id": case, "split": split, "split_role": ROLE[split], "lang": lang, "fleurs_id": r["id"],
                "level": r["level"], "input_text": it["input"], "input_syllables": size(it["input"], "syllables", lang),
                "target_syllables": it["target"], "source_en": ref[r["id"]]["src_text"],
                "license": ref[r["id"]]["license"]})
            text = cand["text"] if cand else None
            label, p, _ = language(text, lang) if text else (None, None, False)
            responses.append({
                "row_id": f"{name}/{r['id']}/L{r['level']}/s{r['seed']}/{r['cond']}", "case_id": case,
                "split": split, "split_role": ROLE[split], "run": name, "variant": r["variant"],
                "prompt": cfg["prompt"]["name"], "lang": lang, "fleurs_id": r["id"], "level": r["level"],
                "seed": r["seed"], "condition": r["cond"], "output_text": text, "no_output": r["no_output"],
                "output_syllables": r["syllables"], "output_chars": size(text, "chars", lang) if text else None,
                "output_words": size(text, "words", lang) if text else None, "target_syllables": r["target"],
                "ratio": r["ratio"], "fit": r["fit"],
                "language_label": label, "language_p": p, "wrong_language": r["wrong_language"],
                "nli_forward": cand.get("forward") if cand else None,
                "nli_backward": cand.get("backward") if cand else None,
                "nli_kept": r["nli_kept"], "nli_added": bool(cand and cand.get("added")) and not r["wrong_language"],
                "nli_dropped": bool(cand and cand.get("dropped")) and not r["wrong_language"],
                **judge_fields(judged[r["id"], r["level"], r["seed"]][r["cond"]], r["wrong_language"], 2),
                "fit_and_complete": complete(r), "rounds": r["rounds"], "retries": r["retries"],
                "time_s": float(r["secs"])})
    return list(inputs.values()), responses, runs


class CachedOnly:
    """The test split's NLI: every pair is already in step4_report's cache, so nothing is scored again."""

    def __init__(self, describe: str) -> None:
        self._describe = describe

    def describe(self) -> str:
        return self._describe

    def meaning(self, premises, hypotheses):
        raise SystemExit(f"{len(premises)} step 4 test pairs are not in {STEP4_TEST_NLI}")


def step4(split: str, nli_cache: Path) -> tuple[list[dict], list[dict], list[dict]]:
    """step4_inputs, step4_responses and runs rows for one split. nli_cache is a working copy of
    step4_report's test cache (results/raw/ is never written); step 4 dev's pairs are scored into it."""
    from isochron.meaning_check import key, read_cache
    from isochron.metrics.meaning import NLI
    from isochron.step4_report import SYSTEMS, TOLERANT, attach_judge, outputs, score

    runs, items, judged, judge_cfgs = [], [], {}, []
    for name in STEP4[split]:
        run = RAW / name
        cfg = json.loads((run / "config.json").read_text(encoding="utf-8"))
        jc = json.loads((run / "judge_config.json").read_text(encoding="utf-8")) if (run / "judge.jsonl").exists() else None
        runs.append(run_row(name, 4, split, cfg, jc))
        for it in read_jsonl(run / "items.jsonl"):
            items.append({**it, "run": name})
        if jc:
            judge_cfgs.append(jc)
            judged.update({(j["id"], j["lang"], j["seed"]): j for j in read_jsonl(run / "judge.jsonl")})
    describe = read_cache(STEP4_TEST_NLI)[0]
    if split == "test":
        nli, second = CachedOnly(describe), read_cache(SECOND_NLI / "step4_cache.jsonl")[1]
    else:  # the same model and device as the test scores
        nli, second = NLI(device=describe.split(", ")[1]), None
    rows = outputs(items, "espeak")
    if split == "dev":  # the JSON sensitivity row is post-hoc, defined and reported on test only
        rows = [r for r in rows if r["system"] != TOLERANT]
    run_of = {(it["id"], it["lang"], it["seed"]): it["run"] for it in items}
    score(rows, "espeak", nli, nli_cache)
    if judged:
        attach_judge(rows, judged)
    by_item = {(it["id"], it["lang"], it["seed"]): it for it in items}
    inputs: dict[str, dict] = {}
    responses = []
    for r in rows:
        it = by_item[r["id"], r["lang"], r["seed"]]
        refs = fleurs(split, r["lang"])
        case = f"step4/{split}/{r['lang']}/{r['id']}"
        inputs.setdefault(case, {
            "case_id": case, "split": split, "split_role": ROLE[split], "lang": r["lang"], "fleurs_id": r["id"],
            "source_en": r["source"], "reference": r["reference"],
            "budget_chars": it["budgets"]["isometric"]["target"], "budget_syllables": it["budgets"]["isosyllabic"]["target"],
            "source_chars": size(r["source"], "chars", "en"), "source_syllables": size(r["source"], "syllables", "en"),
            "license": refs[r["id"]]["license"]})
        entry, system, text = it["budgets"][r["budget"]], r["system"], r["text"]
        label, p, _ = language(text, r["lang"]) if text else (None, None, False)
        loop = entry["c"].get("loop") if system == "c" else None
        v = None
        if judged and system in SYSTEMS:
            j = judged[r["id"], r["lang"], r["seed"]]
            v = j["a"] if system == "a" else j["budgets"][r["budget"]][system]
        m2 = {}
        if second is not None and r["usable"]:
            m2 = {"ref": second[key(r["reference"], text)], "src": second[key(r["source"], text)]}
        responses.append({
            "row_id": f"{run_of[r['id'], r['lang'], r['seed']]}/{r['lang']}/{r['id']}/s{r['seed']}/{r['budget']}/{system}",
            "case_id": case, "split": split, "split_role": ROLE[split], "run": run_of[r["id"], r["lang"], r["seed"]],
            "lang": r["lang"], "fleurs_id": r["id"], "seed": r["seed"], "budget": r["budget"], "unit": r["unit"],
            "target": r["target"], "system": system,
            "system_name": SYSTEMS.get(system, "(b) with \\' read as ' (JSON sensitivity, post-hoc)"),
            "post_hoc": system == TOLERANT, "output_text": text, "no_output": not text,
            "language_label": label, "language_p": p, "wrong_language": r["wrong_language"], "usable": r["usable"],
            "output_chars": r["len"]["chars"] if r["len"] else None,
            "output_words": r["len"]["words"] if r["len"] else None,
            "output_syllables": r["len"]["syllables"] if r["len"] else None,
            "output_length": r["len"][r["unit"]] if r["len"] else None,
            "ratio": r["ratio"], "compression_vs_a": r["compression"], "fit": bool(r["fit"]),
            "nli_ref_kept": r["ref"]["kept"] if r["ref"] else None, "nli_ref_added": r["ref"]["added"] if r["ref"] else None,
            "nli_ref_dropped": r["ref"]["dropped"] if r["ref"] else None, "nli_src_kept": r["src"]["kept"] if r["src"] else None,
            "nli2_ref_kept": m2["ref"]["kept"] if m2 else None, "nli2_ref_added": m2["ref"]["added"] if m2 else None,
            "nli2_ref_dropped": m2["ref"]["dropped"] if m2 else None, "nli2_src_kept": m2["src"]["kept"] if m2 else None,
            **(judge_fields(v, r["wrong_language"], 4) if v is not None else judge_fields(None, False, 4) | {"judge_valid": None}),
            "fit_and_complete": r.get("complete"),
            "kept_plain": r["kept_plain"], "loop_revisions": r["rounds"] if system == "c" else None,
            "loop_rounds": len(loop["rounds"]) if loop else None,
            "loop_retries": sum(x["retry"] for x in loop["rounds"]) if loop else None,
            "loop_rounds_without_candidate": sum(not x["candidates"] for x in loop["rounds"]) if loop else None,
            "a_tries": len(it["a"]["tries"]) if system == "a" else None,
            "b_parse_error": entry["b"].get("parse_error") if system in ("b", TOLERANT) else None,
            "b_candidates": len(entry["b"].get("candidates") or []) if system in ("b", TOLERANT) else None})
    return list(inputs.values()), responses, runs


def control_verdicts() -> tuple[list[dict], list[dict]]:
    """judge_controls rows and their metadata: every planted pair, both NLI models' verdicts and the judge's
    outcome (correct or not, from the committed validation reports' lists of pairs judged wrong or invalid)."""
    from isochron.judge import SUITES
    from isochron.metrics.meaning import Meaning

    nli = defaultdict(dict)
    for c in read_jsonl(SECOND_NLI / "controls.jsonl"):
        nli[c["suite"], c["id"]][c["model"]] = c
    rows, meta = [], []
    for suite in ("nli", "hard", "nli_xl", "hard_xl"):
        report = Path(VALIDATION.format(suite=suite)).read_text(encoding="utf-8").splitlines()
        start = next(i for i, line in enumerate(report) if line.startswith("## Pairs judged wrong"))
        wrong = {line.split("|")[1].strip(): line.split("|")[2].strip()
                 for line in first_table(report[start:])[2:]}
        for p in read_jsonl(SUITES[suite]["file"]):
            verdicts = {}
            for model in ("evaluation", "second"):
                c = nli[suite, p["id"]][model]
                verdicts[model] = (c["forward"], c["backward"],
                                   bool(SUITES[suite]["nli"][p["control"]](Meaning(c["forward"], c["backward"]))))
            rows.append({"pair_id": f"{suite}/{p['id']}", "suite": suite, "lang": p["lang"],
                         "source_lang": p.get("source_lang") or p["lang"], "fleurs_id": p["fleurs_id"],
                         "control": p["control"], "source": p["source"], "output": p["output"], "edit": p.get("note"),
                         "nli_forward": verdicts["evaluation"][0], "nli_backward": verdicts["evaluation"][1],
                         "nli_correct": verdicts["evaluation"][2],
                         "nli2_forward": verdicts["second"][0], "nli2_backward": verdicts["second"][1],
                         "nli2_correct": verdicts["second"][2],
                         "judge_correct": p["id"] not in wrong,
                         "judge_invalid": wrong.get(p["id"]) == "invalid",
                         "split": "controls"})
            meta.append({"instance_id": f"controls/{suite}/{p['id']}", "split": "controls", "lang": p["lang"],
                         "fleurs_id": p["fleurs_id"], "license": p["license"],
                         "source": f"FLEURS train sentence {p['fleurs_id']} (text from FLoRes-101)"
                                   + ("; source replaced by its English original" if suite.endswith("_xl") else ""),
                         "note": None if p["control"] == "identity" else
                         "edited copy written by Claude (AI assistant); not reviewed by a native speaker",
                         "used_in": ["judge_controls"]})
    return rows, meta


def instance_meta(inputs: list[dict], experiment: str) -> list[dict]:
    rows = {}
    for x in inputs:
        rec = fleurs(x["split"], x["lang"])[x["fleurs_id"]]
        iid = f"fleurs/{x['split']}/{x['lang']}/{x['fleurs_id']}"
        rows[iid] = {"instance_id": iid, "split": x["split"], "lang": x["lang"], "fleurs_id": x["fleurs_id"],
                     "license": rec["license"], "source": rec["source"] + " (text from FLoRes-101)", "note": None,
                     "used_in": [experiment]}
    return list(rows.values())


def truth(value: str) -> bool | None:
    return {"True": True, "False": False, "1": True, "0": False}.get((value or "").strip())


def native_rows() -> list[dict]:
    """The native-speaker check: every line of the sheet as rated, its system from the key, and the marks the
    scoring uses (isochron.native_check: the rated copy's marks also apply to an identical pair, v2.34)."""
    from isochron.native_check import MEANING, read_marks, with_identical_pairs, yes_no

    raw = read_marks(NATIVE_MARKS)
    with open(NATIVE_AS_RATED, encoding="utf-8-sig") as f:
        sheet = {r["line"]: r for r in csv.DictReader(f)}
    with open(NATIVE_KEY, encoding="utf-8") as f:
        key = list(csv.DictReader(line for line in f if not line.startswith("#")))
    marks, origin = with_identical_pairs(raw, key, NATIVE_AS_RATED)
    rows = []
    for k in sorted(key, key=lambda r: int(r["line"])):
        line, m = k["line"], marks.get(k["line"])
        rows.append({
            "line": int(line), "case_id": f"step4/test/de/{k['id']}", "split": "test", "split_role": "descriptive",
            "run": k["run"], "lang": "de", "fleurs_id": k["id"], "seed": int(k["seed"]), "budget": k["budget"],
            "system": k["system"], "english_source": sheet[line]["english_source"],
            "german_output": sheet[line]["german_output"], "kept_plain": truth(k["kept_plain"]),
            "same_text_as_its_pair": truth(k["same_text_as_its_pair"]), "fits_budget": truth(k["fits_budget"]),
            "rating": origin.get(line, "not rated"),
            "meaning": MEANING.get((m.get("meaning") or "").strip().lower()) if m else None,
            "added_info": yes_no(m.get("added_info", "")) if m else None,
            "natural_german": yes_no(m.get("natural_german", "")) if m else None,
            "rater_comment": (raw[line].get("comment") or "").strip() or None,
            **{c: truth(k[c]) for c in ("nli_kept_ref", "nli_added_ref", "nli_dropped_ref", "nli_kept_src",
                                        "nli2_kept_ref", "nli2_added_ref", "nli2_dropped_ref", "nli2_kept_src")},
            "judge_recall": float(k["judge_recall"]) if k["judge_recall"] else None,
            **{c: truth(k[c]) for c in ("judge_dropped_or_changed", "judge_added", "judge_complete")}})
    return rows


def timing_rows() -> list[dict]:
    """Every timing test's durations, one row per text and system (no audio)."""
    def seconds(value: str | None) -> list[float] | None:
        return [float(x) for x in value.split()] if value else None

    def number(value: str | None) -> float | None:
        return float(value) if value not in (None, "") else None

    rows = []
    for test, (path, results, tts, ok) in TIMING_TESTS.items():
        with open(path, encoding="utf-8") as f:
            records = list(csv.DictReader(f))
        base = {"split": "test", "split_role": "exploratory", "timing_test": test, "results_file": results,
                "tts": tts, "seconds_valid": ok}
        if test == "qwen3_tts_calibrated":  # one row per source in the file: a row per system here
            for r in records:
                for system in ("a", "c"):
                    median, slot = float(r[f"{system}_s"]), float(r["english_slot_s"])
                    rows.append({**base, "fleurs_id": r["id"], "system": system, "purpose": "time_check", "voice": "Aiden",
                                 "text_id": None, "syllables": int(r["c_syllables"]) if system == "c" else None,
                                 "take_s": None, "median_s": median, "english_slot_s": slot,
                                 "ratio": round(median / slot, 3), "fits_slot": r[f"{system}_fits"] == "1",
                                 "calibrated_target": int(r["calibrated_target"]) if system == "c" else None,
                                 "hits_calibrated_target": r["c_hits_target"] == "1" if system == "c" else None,
                                 "kept_plain": r["c_kept_plain"] == "1" if system == "c" else None})
            continue
        for r in records:
            rows.append({**base, "fleurs_id": r["id"], "system": r["system"], "purpose": r.get("purpose", "demo"),
                         "voice": r.get("voice") or ("Aiden" if test == "qwen3_tts" else "default"),
                         "text_id": r["text_id"], "syllables": int(r["syllables"]) if r.get("syllables") else None,
                         "take_s": seconds(r.get("clean_take_s") or r.get("take_s")),
                         "median_s": number(r["median_s"]), "english_slot_s": number(r["english_slot_s"]),
                         "ratio": number(r.get("ratio")), "fits_slot": truth(r.get("fits_slot")),
                         "calibrated_target": None, "hits_calibrated_target": None, "kept_plain": None})
    return rows


def write(out: Path, config: str, split: str, rows: list[dict]) -> None:
    (out / config).mkdir(parents=True, exist_ok=True)
    with open(out / config / f"{split}.jsonl", "w", encoding="utf-8") as f:
        f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
    print(f"{config}/{split}.jsonl: {len(rows)} rows")


def build(out: Path, nli_cache: Path) -> None:
    if not nli_cache.exists():
        nli_cache.write_bytes(STEP4_TEST_NLI.read_bytes())
    meta = defaultdict(dict)
    for split in ("dev", "test"):
        inputs2, responses2, runs2 = step2(split)
        inputs4, responses4, runs4 = step4(split, nli_cache)
        write(out, "step2_inputs", split, inputs2)
        write(out, "step2_responses", split, responses2)
        write(out, "step4_inputs", split, inputs4)
        write(out, "step4_responses", split, responses4)
        write(out, "runs", split, runs2 + runs4)
        for m in instance_meta(inputs2, "step2") + instance_meta(inputs4, "step4"):
            if m["instance_id"] in meta[split]:
                meta[split][m["instance_id"]]["used_in"] += m["used_in"]
            else:
                meta[split][m["instance_id"]] = m
    controls, control_meta = control_verdicts()
    write(out, "judge_controls", "controls", controls)
    native, timing = native_rows(), timing_rows()
    write(out, "native_check", "test", native)
    write(out, "timing", "test", timing)
    for config, rows in (("native_check", native), ("timing", timing)):
        for iid in dict.fromkeys(f"fleurs/test/de/{r['fleurs_id']}" for r in rows):
            meta["test"][iid]["used_in"].append(config)  # every one is a step 4 test sentence
    for split in ("dev", "test"):
        write(out, "metadata", split, sorted(meta[split].values(), key=lambda m: m["instance_id"]))
    write(out, "metadata", "controls", control_meta)
    (out / "export.json").write_text(json.dumps({"git_commit": git_commit(), "tool": "isochron.hf_export",
                                                 "step2_runs": STEP2, "step4_runs": STEP4}, indent=1) + "\n",
                                     encoding="utf-8")


# ---------------------------------------------------------------- check: the results files from the export alone


def md_rows(path: Path, title: str) -> dict[str, list[str]]:
    """The table under the heading `### title` in a results file, as {first cell: cells}."""
    lines = path.read_text(encoding="utf-8").splitlines()
    start = lines.index(f"### {title}")
    table = first_table(lines[start + 1:])
    return {cells[0]: cells for cells in ([c.strip() for c in line.strip().strip("|").split("|")] for line in table[2:])}


def by_id(rs: list[dict], f, sel=lambda r: True) -> dict[str, list]:
    ids = sorted({r["fleurs_id"] for r in rs})
    return {i: [f(r) for r in rs if r["fleurs_id"] == i and sel(r)] for i in ids}


def mean(values, fmt="{:.2f}") -> str:
    values = [v for v in values if v is not None]
    return fmt.format(np.mean(values)) if values else "–"


STEP4_NAMES = {"a": "(a) plain translation", "b": "(b) one step to the budget",
               "b_tolerant": "(b), `\\'` read as `'`: sensitivity (post-hoc, added after test outputs existed)",
               "c": "(c) translate, then shorten"}


def step4_cells(rs: list[dict]) -> dict[str, dict[str, str]]:
    """The main, judge and second-NLI table cells of one (language, budget), per system."""
    out = {}
    for system, name in STEP4_NAMES.items():
        s = [r for r in rs if r["system"] == system]
        if not s:
            continue
        usable = [r for r in s if r["usable"]]
        lens = " / ".join(mean([r[f"output_{u}"] for r in usable], "{:.1f}") for u in ("chars", "words", "syllables"))
        cells = {
            "Outputs": str(len(s)), "Fit ±10 %": ci(by_id(s, lambda r: r["fit"])),
            "Kept vs reference": ci(by_id(s, lambda r: bool(r["nli_ref_kept"]))),
            "Added vs ref.": f"{100 * np.mean([bool(r['nli_ref_added']) for r in usable]) if usable else 0:.0f} %",
            "Dropped vs ref.": f"{100 * np.mean([bool(r['nli_ref_dropped']) for r in usable]) if usable else 0:.0f} %",
            "Kept vs source": ci(by_id(s, lambda r: bool(r["nli_src_kept"]))),
            "Achieved ÷ budget": mean([r["ratio"] for r in usable]),
            "Compression vs (a)": mean([r["compression_vs_a"] for r in usable]),
            "Chars / words / syllables": lens,
            "(a) kept": f"{100 * np.mean([r['kept_plain'] for r in s]):.0f} %" if system == "c" else "–",
            "Avg. rounds": mean([r["loop_revisions"] for r in s]) if system == "c" else "–",
            "Wrong language": str(sum(r["wrong_language"] for r in s)), "No output": str(sum(r["no_output"] for r in s))}
        if s[0]["judge_valid"] is not None and system != "b_tolerant":
            answered4 = [r for r in s if r["judge_valid"] and r["usable"]]
            cells |= {"judge:Fit & complete": ci(by_id(s, lambda r: r["fit_and_complete"])),
                      "judge:Fact recall": ci(by_id(s, lambda r: r["judge_recall"], lambda r: r["judge_valid"])),
                      "judge:Added-fact rate": f"{100 * np.mean([bool(r['judge_added_any']) for r in answered4]):.1f} %"
                      if answered4 else "–",
                      "judge:Judge invalid": str(sum(not r["judge_valid"] for r in s))}
        if s[0]["split"] == "test":
            for n, label in (("", "evaluation NLI"), ("2", "second NLI")):
                for side, col in (("ref", "reference"), ("src", "source")):
                    field = f"nli{n}_{side}_kept"
                    cells[f"nli2:Kept vs {col}: {label}"] = ci(by_id(s, lambda r, f=field: bool(r["usable"] and r[f])))
        out[name] = cells
    return out


def step4_diffs(rs: list[dict]) -> dict[str, dict[str, str]]:
    metrics = [("Fit ±10 %", lambda r: r["fit"]), ("Kept vs reference", lambda r: bool(r["nli_ref_kept"]))]
    if rs[0]["judge_valid"] is not None:
        metrics.insert(1, ("Fit & complete", lambda r: r["fit_and_complete"]))
    out = {}
    for x, y in (("c", "b"), ("c", "a"), ("b", "a"), ("c", "b_tolerant")):
        if not any(r["system"] == y for r in rs):
            continue
        pair = [{**r, "id": r["fleurs_id"], "cond": "with" if r["system"] == x else "without"}
                for r in rs if r["system"] in (x, y)]
        label = "(c) − (b) with `\\'` read as `'` (sensitivity)" if y == "b_tolerant" else f"({x}) − ({y})"
        out[label] = {name: "–" if y == "b_tolerant" and name == "Fit & complete" else
                      paired_diff(pair, value, lambda r: True) for name, value in metrics}
    return out


def step2_cells(rs: list[dict]) -> dict[str, str]:
    r2 = [{**r, "id": r["fleurs_id"], "valid": r["judge_valid"], "recall": r["judge_recall"],
           "added": r["judge_added_any"]} for r in rs]
    ratios = [r["ratio"] for r in rs if r["ratio"] is not None]
    return {"Outputs": str(len(rs)), "Fit ±10 %": ci(by_id(rs, lambda r: r["fit"])),
            "Fact recall": ci(by_id(r2, lambda r: r["recall"], valid)),
            "Added-fact rate": ci(by_id(r2, lambda r: r["added"], answered)),
            "Fit & complete": ci(by_id(r2, complete)),
            "NLI kept": f"{100 * np.mean([r['nli_kept'] for r in rs]):.0f} %",
            "Achieved ÷ target": f"{np.mean(ratios):.2f}" if ratios else "–",
            "Avg. rounds": f"{np.mean([r['rounds'] for r in rs]):.2f}", "Retries": str(sum(r["retries"] for r in rs)),
            "Time / output (s)": f"{np.mean([r['time_s'] for r in rs]):.1f}",
            "No output": str(sum(r["no_output"] for r in rs)), "Wrong language": str(sum(r["wrong_language"] for r in rs)),
            "Judge invalid": str(sum(not valid(r) for r in r2))}


def compare(got: dict[str, str], table: dict[str, list[str]], header: list[str], row: str, where: str,
            report: list[str], counts: Counter) -> None:
    cells = table.get(row)
    if cells is None:
        report.append(f"{where}: row {row!r} missing from the results file")
        return
    for col, value in got.items():
        if col in header:
            counts[where.split(" ")[0]] += 1
            have = cells[header.index(col)]
            if have != value:
                report.append(f"{where} | {row} | {col}: results {have!r}, export {value!r}")


def unmatched(table: dict[str, list[str]], rows, where: str, report: list[str]) -> None:
    """Rows of a results table that the export did not reproduce."""
    report += [f"{where}: row {row!r} is not in the export" for row in sorted(set(table) - set(rows))]


def header_of(path: Path, title: str) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    table = first_table(lines[lines.index(f"### {title}") + 1:])
    return [c.strip() for c in table[0].strip().strip("|").split("|")]


def check(d: Path, results: Path = Path("results")) -> tuple[Counter, list[str]]:
    """Every cell of the results tables that the export can reproduce, recomputed from the exported files;
    returns the cells compared per results file and the cells that differ."""
    mismatches: list[str] = []
    counts: Counter = Counter()
    s4 = {split: read_jsonl(d / "step4_responses" / f"{split}.jsonl") for split in ("dev", "test")}
    files4 = {"test": results / "step4_test.md", "dev": results / "hpc_8b_step4_dev.md"}
    for split, rows in s4.items():
        groups = defaultdict(list)
        for r in rows:
            groups[r["lang"], r["budget"]].append(r)
        for (lang, kind), rs in sorted(groups.items()):
            title = f"EN → {lang.upper()}, {kind} budget ({rs[0]['unit']})"
            cells = step4_cells(rs)
            for sub, path, t in (("", files4[split], title), ("judge:", files4[split], f"{title}: final judge"),
                                 ("nli2:", results / "step4_test_nli2.md", title)):
                if sub and split == "dev":  # no judge and no second NLI on dev
                    continue
                table, header = md_rows(path, t), header_of(path, t)
                for name, c in cells.items():
                    if name == STEP4_NAMES["b_tolerant"] and sub == "judge:":
                        continue
                    picked = {k[len(sub):]: v for k, v in c.items() if (k.startswith(sub) if sub else ":" not in k)}
                    compare(picked, table, header, name, f"{path.name} {t}", mismatches, counts)
                unmatched(table, cells, f"{path.name} {t}", mismatches)
            if split == "test":
                t = f"{title}: paired differences (post-hoc, added after test outputs existed; percentage points)"
                table, header = md_rows(files4[split], t), header_of(files4[split], t)
                diffs = step4_diffs(rs)
                for row, c in diffs.items():
                    compare(c, table, header, row, f"{files4[split].name} {t}", mismatches, counts)
                unmatched(table, diffs, f"{files4[split].name} {t}", mismatches)
    s2 = {split: read_jsonl(d / "step2_responses" / f"{split}.jsonl") for split in ("dev", "test")}
    for split, rows in s2.items():
        path = results / ("step2_test.md" if split == "test" else "phase2_pilot.md")
        for lang in sorted({r["lang"] for r in rows}):
            rl = [r for r in rows if r["lang"] == lang]
            levels = sorted({r["level"] for r in rl}, reverse=True)
            if split == "test":
                L = lang.upper()
                titles = [(f"{L}: all levels ({', '.join(f'{lv} %' for lv in levels)})", rl)]
                titles += [(f"{L}: level {lv} %", [r for r in rl if r["level"] == lv]) for lv in levels]
            else:
                titles = [(f"{'Both' if len(levels) == 2 else 'All'} levels ({' and '.join(f'{lv} %' for lv in levels)})", rl)]
                titles += [(f"Level {lv} %", [r for r in rl if r["level"] == lv]) for lv in levels]
            for t, rs in titles:
                lines = path.read_text(encoding="utf-8").splitlines()
                table_lines = first_table(lines[lines.index(f"### {t}") + 1:])
                header = [c.strip() for c in table_lines[0].strip().strip("|").split("|")]
                table = {}
                for line in table_lines[2:]:
                    cells = [c.strip() for c in line.strip().strip("|").split("|")]
                    table[f"{cells[0]} {cells[1]}"] = cells
                pairs = sorted({(r["variant"], r["condition"]) for r in rs})
                for (variant, cond) in pairs:
                    sel = [r for r in rs if r["variant"] == variant and r["condition"] == cond]
                    compare(step2_cells(sel), table, header, f"{variant} {cond}", f"{path.name} {t}", mismatches, counts)
                unmatched(table, [f"{v} {c}" for v, c in pairs], f"{path.name} {t}", mismatches)
    from isochron.judge import TITLES

    controls = read_jsonl(d / "judge_controls" / "controls.jsonl")
    for suite in ("nli", "hard", "nli_xl", "hard_xl"):
        rs = [r for r in controls if r["suite"] == suite]
        lines = Path(VALIDATION.format(suite=suite)).read_text(encoding="utf-8").splitlines()
        table_lines = first_table(lines)
        header = [c.strip() for c in table_lines[0].strip().strip("|").split("|")]
        table = {cells[0]: cells for cells in ([c.strip() for c in ln.strip().strip("|").split("|")] for ln in table_lines[2:])}
        nli2_t = TITLES[suite]
        nli2_table, nli2_header = md_rows(results / "step4_test_nli2.md", nli2_t), header_of(results / "step4_test_nli2.md", nli2_t)
        unmatched(table, {r["control"] for r in rs}, Path(VALIDATION.format(suite=suite)).name, mismatches)
        unmatched(nli2_table, {r["control"] for r in rs}, f"step4_test_nli2.md {nli2_t}", mismatches)
        for control in dict.fromkeys(r["control"] for r in rs):
            c = [r for r in rs if r["control"] == control]

            def rate(field, c=c):
                ok = sum(r[field] for r in c)
                return f"{100 * ok / len(c):.0f} % ({ok}/{len(c)})"

            compare({"All": rate("judge_correct"), "NLI, all": rate("nli_correct")}, table, header, control,
                    Path(VALIDATION.format(suite=suite)).name, mismatches, counts)
            compare({"Pairs": str(len(c)), "Evaluation NLI (the loop's)": rate("nli_correct"),
                     "Second NLI": rate("nli2_correct")}, nli2_table, nli2_header, control,
                    f"step4_test_nli2.md {nli2_t}", mismatches, counts)
    check_native(d, results, mismatches, counts)
    check_timing(d, results, mismatches, counts)
    return counts, mismatches


def check_native(d: Path, results: Path, mismatches: list[str], counts: Counter) -> None:
    """The native-speaker rates per system and the agreement with each automatic check."""
    from isochron.native_check import STEP4_CHECKS, kappa, rate

    rows = [r for r in read_jsonl(d / "native_check" / "test.jsonl") if r["meaning"] and r["added_info"] is not None]
    path = results / "native_check_step4_agreement.md"
    lines = path.read_text(encoding="utf-8").splitlines()
    tables = []
    for i, line in enumerate(lines):
        if line.startswith("|") and (i == 0 or not lines[i - 1].startswith("|")):
            tables.append(first_table(lines[i:]))
    rates, agree = tables[0], tables[1]
    names = {"a": "(a) plain translation", "c": "(c) ours: translate, then shorten"}
    got = {}
    for system, name in names.items():
        ls = [r for r in rows if r["system"] == system]
        nat = [r for r in ls if r["natural_german"] is not None]
        got[name] = ([name, str(len(ls))] + [rate(sum(r["meaning"] == v for r in ls), len(ls))
                                             for v in ("kept", "minor loss", "wrong")]
                     + [rate(sum(r["added_info"] for r in ls), len(ls)), rate(sum(r["natural_german"] for r in nat), len(nat))])
    for check_name, ok, lost, added in STEP4_CHECKS:
        for on, column, human in (("kept, nothing added", ok, lambda r: r["meaning"] == "kept" and not r["added_info"]),
                                  ("information lost (minor or wrong)", lost, lambda r: r["meaning"] != "kept"),
                                  ("information added", added, lambda r: r["added_info"])):
            if column is None:
                continue
            pairs = [(human(r), r[column]) for r in rows if r[column] is not None]
            k = kappa([p[0] for p in pairs], [p[1] for p in pairs])
            got[f"{check_name} | {on}"] = [check_name, on, str(len(pairs)),
                                           f"{100 * sum(a == b for a, b in pairs) / len(pairs):.0f} %",
                                           "–" if k is None else f"{k:.2f}"]
    have = {}
    for table, width in ((rates, 1), (agree, 2)):
        for line in table[2:]:
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            have[" | ".join(cells[:width])] = cells
    for row, cells in got.items():
        counts[path.name] += len(cells)
        if have.get(row) != cells:
            mismatches.append(f"{path.name} | {row}: results {have.get(row)}, export {cells}")
    unmatched(have, got, path.name, mismatches)


def check_timing(d: Path, results: Path, mismatches: list[str], counts: Counter) -> None:
    """Fit in seconds per system, and the paired counts, of each timing test that reports them."""
    rows = read_jsonl(d / "timing" / "test.jsonl")
    for test, title_c in (("chatterbox", "(c) ours"), ("qwen3_tts", "(c) ours"),
                          ("qwen3_tts_calibrated", "(c) ours, calibrated budget")):
        path = results / Path(TIMING_TESTS[test][1]).name
        text = path.read_text(encoding="utf-8")
        timed = [r for r in rows if r["timing_test"] == test and r["purpose"] == "time_check" and r["median_s"] is not None]
        paired = {r["fleurs_id"] for r in timed if r["system"] == "a"} & {r["fleurs_id"] for r in timed if r["system"] == "c"}
        by = {s: {r["fleurs_id"]: r for r in timed if r["system"] == s and r["fleurs_id"] in paired} for s in ("a", "c")}
        lines = text.splitlines()
        table = first_table(lines[lines.index("## Fit in seconds") + 1:])
        header = [c.strip() for c in table[0].strip().strip("|").split("|")]
        have = {cells[0]: cells for cells in ([c.strip() for c in ln.strip().strip("|").split("|")] for ln in table[2:])}
        got_rows = {}
        for system, name in (("a", "(a) plain translation"), ("c", title_c)):
            rs = list(by[system].values())
            ratios = sorted(r["median_s"] / r["english_slot_s"] for r in rs)
            fits = sum(r["fits_slot"] for r in rs)
            got = {"Fits the English slot": f"{fits}/{len(rs)} ({100 * fits / len(rs):.0f} %)",
                   "Median speech ÷ slot": f"{float(np.median(ratios)):.2f}",
                   "Range": f"{ratios[0]:.2f}–{ratios[-1]:.2f}",
                   "Too short": str(sum(x < 0.9 for x in ratios)), "Too long": str(sum(x > 1.1 for x in ratios))}
            got_rows[name] = got
            compare(got, have, header, name, f"{path.name} Fit in seconds", mismatches, counts)
        unmatched(have, got_rows, f"{path.name} Fit in seconds", mismatches)
        only_c = sum(by["c"][i]["fits_slot"] and not by["a"][i]["fits_slot"] for i in paired)
        only_a = sum(by["a"][i]["fits_slot"] and not by["c"][i]["fits_slot"] for i in paired)
        sentence = f"(c) fits and (a) does not in {only_c}, the reverse in {only_a}"
        counts[path.name] += 2
        if sentence not in text:
            mismatches.append(f"{path.name}: no sentence {sentence!r}")
        if test == "qwen3_tts_calibrated":
            c = list(by["c"].values())
            hits = [r for r in c if r["hits_calibrated_target"]]
            sentences = [(f"(c) hits its calibrated syllable budget (±10 %) in {len(hits)}/{len(c)}; of those, "
                          f"{sum(r['fits_slot'] for r in hits)} also fit the English slot"),
                         f"(c) kept (a) in {sum(r['kept_plain'] for r in c)} sources"]
            for sentence in sentences:
                counts[path.name] += 1
                if sentence not in text:
                    mismatches.append(f"{path.name}: no sentence {sentence!r}")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="write the dataset from results/raw/")
    b.add_argument("--out", type=Path, default=Path("data/hf_dataset"))
    b.add_argument("--nli-cache", type=Path, required=True,
                   help="working copy of the step 4 NLI cache (made from results/raw/ if missing; dev is scored into it)")
    c = sub.add_parser("check", help="recompute the results tables from the exported files")
    c.add_argument("--dir", type=Path, default=Path("data/hf_dataset"))
    args = ap.parse_args(argv)
    if args.cmd == "build":
        build(args.out, args.nli_cache)
    else:
        counts, mismatches = check(args.dir)
        print("\n".join(f"{name}: {n} cells" for name, n in sorted(counts.items())))
        print(f"{sum(counts.values())} cells compared, {len(mismatches)} differ")
        print("\n".join(mismatches))
        raise SystemExit(1 if mismatches else 0)


if __name__ == "__main__":
    main()
