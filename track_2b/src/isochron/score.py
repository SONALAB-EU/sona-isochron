"""Score a run offline: selection, length and meaning. Re-runnable.

For every (sentence, level, seed) in results/raw/<run>/candidates.jsonl:
- the raw answer is parsed again, so parser fixes apply to old runs;
- selection "closest": the candidate whose length in the run's unit is
  closest to the target, ties to the earlier one; "first": candidate 1;
- length in characters, words and syllables. In each unit the target is
  level % of the input's length (rounded half up); a hit is within ±10 %;
- compression ratio per unit: output length ÷ input length;
- meaning: bidirectional NLI between input and output (same language), plus a
  check whether the NLI accepts each unchanged input as entailing itself.

An answer without usable candidates counts as a miss and as not kept.
Writes scores.jsonl and summary.md into the run directory and prints the
summary; for a go/no-go run it also prints the decision. Run from track_2b/:

    uv run python -m isochron.score results/raw/<run> [--show]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from isochron import gonogo
from isochron.candidates import SELECTIONS, parse_candidates, select
from isochron.metrics.length import UNITS, counter_description, espeak_available, hit, length, target
from isochron.provenance import git_commit

N_BOOT = 10_000
BOOT_SEED = 0


def bootstrap(per_item: list[float]) -> tuple[float, float, float]:
    """Mean and 95 % percentile interval, resampling items with replacement."""
    x = np.asarray(per_item, dtype=float)
    idx = np.random.default_rng(BOOT_SEED).integers(0, len(x), size=(N_BOOT, len(x)))
    means = x[idx].mean(axis=1)
    return float(x.mean()), float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def item_means(recs: list[dict[str, Any]], value) -> list[float]:
    """Per sentence, the value averaged over seeds (records with value None are skipped)."""
    by_id: dict[str, list[float]] = defaultdict(list)
    for r in recs:
        v = value(r)
        if v is not None:
            by_id[r["id"]].append(float(v))
    return [float(np.mean(v)) for v in by_id.values()]


def fmt_ci(per_item: list[float]) -> str:
    if not per_item:
        return "–"
    m, lo, hi = bootstrap(per_item)
    return f"{100 * m:.0f} % [{100 * lo:.0f}, {100 * hi:.0f}]"


def score_rows(rows: list[dict[str, Any]], lang: str, unit: str, counter: str) -> list[dict[str, Any]]:
    def n(text: str, u: str) -> int:
        return length(text, u, lang, counter)

    scored = []
    for row in rows:
        cands, error = parse_candidates(row["raw"])
        inp = row["input"]
        in_len = {u: n(inp, u) for u in UNITS}
        goals = {u: target(row["level"], in_len[u]) for u in UNITS}
        if goals[unit] != row["target"]:
            print(f"warning: {row['id']} level {row['level']}: target {row['target']} at run time, "
                  f"{goals[unit]} now (has the counter changed?)", file=sys.stderr)
        for how in SELECTIONS:
            idx = select(cands, how, lambda c: n(c, unit), row["target"])
            out = cands[idx] if idx is not None else None
            out_len = {u: n(out, u) for u in UNITS} if out else None
            scored.append({
                "id": row["id"], "level": row["level"], "seed": row["seed"], "selection": how,
                "candidate": idx, "n_candidates": len(cands), "parse_error": error,
                "input": inp, "output": out, "input_len": in_len, "target": goals, "output_len": out_len,
                "hit": {u: bool(out_len) and hit(out_len[u], goals[u]) for u in UNITS},
                "ratio": {u: round(out_len[u] / in_len[u], 4) for u in UNITS} if out_len else None,
            })
    return scored


def add_meaning(scored: list[dict[str, Any]], device: str | None) -> tuple[str, dict[str, bool]]:
    from isochron.metrics.meaning import NLI

    nli = NLI(device=device)
    pairs = sorted({(r["input"], r["output"]) for r in scored if r["output"]})
    inputs = sorted({r["input"] for r in scored})
    results = nli.meaning([p[0] for p in pairs] + inputs, [p[1] for p in pairs] + inputs)
    meaning = dict(zip(pairs, results[: len(pairs)]))
    self_kept = {text: m.kept for text, m in zip(inputs, results[len(pairs):])}
    for r in scored:
        m = meaning.get((r["input"], r["output"])) if r["output"] else None
        r["nli"] = (
            {"forward": m.forward, "backward": m.backward, "kept": m.kept, "added": m.added, "dropped": m.dropped}
            if m else {"forward": None, "backward": None, "kept": False, "added": None, "dropped": None}
        )
        r["input_self_kept"] = self_kept[r["input"]]
    return nli.describe(), self_kept


def summarise(cfg: dict[str, Any], scored: list[dict[str, Any]], nli_desc: str | None,
              self_kept: dict[str, bool] | None, counter: str) -> tuple[list[str], list[str]]:
    unit = cfg["unit"]
    started = datetime.now(timezone.utc)
    out = [
        f"# Scores: step {cfg['step']}, {cfg['lang']} {cfg['split']}, {unit} targets"
        + (" (MOCK RUN, no LLM)" if cfg["mock"] else ""),
        "",
        f"- Scored: {started:%Y-%m-%d %H:%M} UTC, git commit {git_commit()}",
        f"- Run: {cfg['date']}, git commit {cfg['git_commit']}",
        f"- Model: {cfg['model']}, quantisation {cfg['quantisation']}, endpoint {cfg['endpoint']}",
        f"- Generation: {json.dumps(cfg['generation'])}; {cfg['candidates_per_request']} candidates per request",
        f"- Prompt: {cfg['prompt']['name']} (sha256 {cfg['prompt']['sha256'][:12]})",
        f"- Seeds: {cfg['seeds']}; levels: {cfg['levels']}; TTS: none",
        f"- n: {cfg['items']['n']} sentences ({cfg['items']['selection']}), {len(scored) // len(SELECTIONS)} requests",
        f"- Syllables: {counter_description(counter)}",
        f"- NLI: {nli_desc or 'not run (--no-nli)'}",
        f"- 95 % CIs: bootstrap over sentences (seed-averaged), {N_BOOT} resamples, seed {BOOT_SEED}",
    ]
    if self_kept is not None:
        bad = sum(not k for k in self_kept.values())
        out.append(f"- Inputs the NLI does not accept as entailing themselves: {bad} of {len(self_kept)}")
    out += [
        "",
        f"| Level | Selection | Outputs | No usable answer | Hit {unit} (95 % CI) | Hit words | Hit chars "
        "| Ratio syll / words / chars | Kept (95 % CI) | Added | Dropped |",
        "|------:|-----------|--------:|-----------------:|------------------|----------:|----------:"
        "|----------------------------|----------------|------:|--------:|",
    ]
    groups: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)
    for r in scored:
        groups[r["level"], r["selection"]].append(r)
    for (level, how), recs in sorted(groups.items(), key=lambda kv: (-kv[0][0], kv[0][1])):
        none = sum(r["output"] is None for r in recs)
        ratios = [r["ratio"] for r in recs if r["ratio"]]
        ratio = " / ".join(f"{np.mean([x[u] for x in ratios]):.2f}" for u in UNITS[::-1]) if ratios else "–"
        hit_unit = fmt_ci(item_means(recs, lambda r: r["hit"][unit]))
        hit_other = [f"{100 * np.mean(item_means(recs, lambda r, u=u: r['hit'][u])):.0f} %" for u in ("words", "chars")]
        if "nli" in recs[0]:
            kept = fmt_ci(item_means(recs, lambda r: r["nli"]["kept"]))
            added, dropped = (
                f"{100 * np.mean(item_means(recs, lambda r, k=k: r['nli'][k])):.0f} %" for k in ("added", "dropped")
            )
        else:
            kept = added = dropped = "–"
        out.append(f"| {level} | {how} | {len(recs)} | {none} | {hit_unit} | {hit_other[0]} | {hit_other[1]} "
                   f"| {ratio} | {kept} | {added} | {dropped} |")

    decision = gonogo_lines(cfg, scored)
    return out + ([""] + decision if decision else []), decision


def gonogo_lines(cfg: dict[str, Any], scored: list[dict[str, Any]]) -> list[str]:
    ids = set(gonogo.gonogo_ids())
    if not (cfg["lang"], cfg["split"], cfg["unit"]) == (gonogo.LANG, gonogo.SPLIT, gonogo.UNIT):
        return []
    if gonogo.LEVEL not in cfg["levels"] or not set(gonogo.SEEDS) <= set(cfg["seeds"]) or not ids <= set(cfg["items"]["ids"]):
        return []
    if cfg["mock"]:
        return ["Go/no-go: mock run, no decision."]
    lines = [f"## Go/no-go (50 sentences × seeds {list(gonogo.SEEDS)}, level {gonogo.LEVEL})", ""]
    for how in SELECTIONS:
        recs = [r for r in scored if r["selection"] == how and r["id"] in ids
                and r["level"] == gonogo.LEVEL and r["seed"] in gonogo.SEEDS]
        if not recs:
            return []
        if "nli" not in recs[0]:
            return lines + ["NLI not run: no decision."]
        go, hit_share, kept_share = gonogo.decide([r["hit"]["syllables"] for r in recs], [r["nli"]["kept"] for r in recs])
        role = "decides" if how == gonogo.SELECTION else "reported only"
        lines.append(f"- {how} ({role}): {len(recs)} outputs, hit {100 * hit_share:.1f} % (need ≥ "
                     f"{100 * gonogo.MIN_HIT:.0f} %), kept among hits {100 * kept_share:.1f} % (need ≥ "
                     f"{100 * gonogo.MIN_KEPT_AMONG_HITS:.0f} %) → **{'GO' if go else 'NO-GO'}**")
    return lines


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Score a run: selection, length and meaning.")
    ap.add_argument("run", type=Path)
    ap.add_argument("--no-nli", action="store_true", help="skip the meaning metrics")
    ap.add_argument("--device", default=None, help="NLI device: cpu or mps (default: mps if available)")
    ap.add_argument("--show", action="store_true", help="print every scored output (closest selection)")
    args = ap.parse_args(argv)

    cfg = json.loads((args.run / "config.json").read_text(encoding="utf-8"))
    rows = [json.loads(line) for line in open(args.run / "candidates.jsonl", encoding="utf-8") if line.strip()]
    counter = cfg["length_counter"]["counter"]
    if counter == "espeak" and not espeak_available():
        sys.exit("this run counted syllables with espeak-ng, which is not installed here")

    scored = score_rows(rows, cfg["lang"], cfg["unit"], counter)
    nli_desc, self_kept = add_meaning(scored, args.device) if not args.no_nli else (None, None)

    with open(args.run / "scores.jsonl", "w", encoding="utf-8") as f:
        for r in scored:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    summary, _ = summarise(cfg, scored, nli_desc, self_kept, counter)
    (args.run / "summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")

    if args.show:
        for r in scored:
            if r["selection"] != "closest":
                continue
            u = cfg["unit"]
            nli = r.get("nli") or {}
            print(f"\n[{r['id']} level {r['level']} seed {r['seed']}] input {r['input_len'][u]} {u}, "
                  f"target {r['target'][u]}, candidate {r['candidate']}")
            print(f"  IN : {r['input']}")
            print(f"  OUT: {r['output']}")
            if r["output_len"]:
                print(f"  {u} {r['output_len'][u]} hit={r['hit'][u]} | words {r['output_len']['words']} "
                      f"chars {r['output_len']['chars']} | NLI {nli.get('forward')}/{nli.get('backward')} "
                      f"kept={nli.get('kept')} added={nli.get('added')} dropped={nli.get('dropped')}")
            else:
                print(f"  no usable answer: {r['parse_error']}")
    print("\n" + "\n".join(summary))
    print(f"\nwrote {args.run / 'scores.jsonl'} and {args.run / 'summary.md'}")


if __name__ == "__main__":
    main()
