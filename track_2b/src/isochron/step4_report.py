"""Step 4 tables: translation to a length budget, per target language, budget and system.

Reads a step 4 run (isochron.step4) and writes a markdown report.

- Fit: the output is within ±10 % of the budget, in the budget's unit (characters without spaces for
  the isometric budget, syllables for the isosyllabic one). A missing or wrong-language output is a miss.
- Kept vs reference (the main meaning check): the NLI finds entailment both ways between the output and
  the human reference translation, in the target language. Added and dropped are its two directions.
- Kept vs source (secondary): the same against the English source (cross-lingual NLI).
- Achieved ÷ budget, and compression = output ÷ plain translation (a), both in the budget's unit, over
  outputs with an answer.
- Lengths: mean characters, words and syllables of the outputs with an answer.
- (c) keeps (a) unchanged when (a) is at most 1.10 × the budget; "(a) kept" is how often.
- A wrong-language output (isochron.language) counts as a failure, like a missing one.
- 95 % intervals: bootstrap over sentences (each carries its seeds), 10,000 resamples, seed 0.

    uv run python -m isochron.step4_report RUN_DIR [--out FILE]
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from isochron.language import check as check_language
from isochron.language import describe as describe_language
from isochron.metrics.length import hit, length
from isochron.pilot_report import BOOT_SEED, N_BOOT, ci
from isochron.provenance import git_commit

SYSTEMS = {"a": "(a) plain translation", "b": "(b) one step to the budget", "c": "(c) translate, then shorten"}


def outputs(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One row per (item, budget, system), before scoring."""
    rows = []
    for it in items:
        plain = it["a"]["text"]
        for kind, entry in it["budgets"].items():
            texts = {"a": plain, "b": entry["b"]["text"], "c": entry["c"]["text"]}
            for system, text in texts.items():
                loop = entry["c"].get("loop") if system == "c" else None
                rows.append({"id": it["id"], "lang": it["lang"], "seed": it["seed"], "budget": kind,
                             "unit": entry["unit"], "target": entry["target"], "system": system, "text": text,
                             "plain": plain, "source": it["source"], "reference": it["reference"],
                             "kept_plain": entry["c"]["kept_plain"] if system == "c" else None,
                             "rounds": loop["revisions"] if loop else 0})
    return rows


def score(rows: list[dict[str, Any]], counter: str, nli) -> None:
    """Adds lengths, fit, the language check and both NLI checks to every row, in place."""
    for r in rows:
        t, lang = r["text"], r["lang"]
        r["wrong_language"] = bool(t) and check_language(t, lang).wrong
        r["usable"] = bool(t) and not r["wrong_language"]
        if t:
            r["len"] = {u: length(t, u, lang, counter) for u in ("chars", "words", "syllables")}
            r["fit"] = r["usable"] and hit(r["len"][r["unit"]], r["target"])
            r["ratio"] = r["len"][r["unit"]] / r["target"]
            r["compression"] = (r["len"][r["unit"]] / length(r["plain"], r["unit"], lang, counter)) if r["plain"] else None
        else:
            r["len"], r["fit"], r["ratio"], r["compression"] = None, False, None, None
    scored = [r for r in rows if r["usable"]]
    vs_ref = nli.meaning([r["reference"] for r in scored], [r["text"] for r in scored])
    vs_src = nli.meaning([r["source"] for r in scored], [r["text"] for r in scored])
    for r in rows:
        r["ref"] = r["src"] = None
    for r, m_ref, m_src in zip(scored, vs_ref, vs_src):
        r["ref"] = {"kept": m_ref.kept, "added": m_ref.added, "dropped": m_ref.dropped}
        r["src"] = {"kept": m_src.kept}


def table(rows: list[dict[str, Any]], title: str) -> list[str]:
    out = [f"### {title}", "",
           "| System | Outputs | Fit ±10 % | Kept vs reference | Added vs ref. | Dropped vs ref. | Kept vs source "
           "| Achieved ÷ budget | Compression vs (a) | Chars / words / syllables | (a) kept | Avg. rounds "
           "| Wrong language | No output |",
           "|--------|--------:|-----------|-------------------|--------------:|----------------:|----------------"
           "|------------------:|-------------------:|--------------------------|---------:|------------:"
           "|---------------:|----------:|"]
    for system, name in SYSTEMS.items():
        rs = [r for r in rows if r["system"] == system]
        if not rs:
            continue
        ids = sorted({r["id"] for r in rs})

        def by(f):
            return {i: [f(r) for r in rs if r["id"] == i] for i in ids}

        usable = [r for r in rs if r["usable"]]

        def mean(values, fmt="{:.2f}"):
            values = [v for v in values if v is not None]
            return fmt.format(np.mean(values)) if values else "–"

        lens = " / ".join(mean([r["len"][u] for r in usable], "{:.1f}") for u in ("chars", "words", "syllables"))
        kept_plain = f"{100 * np.mean([r['kept_plain'] for r in rs]):.0f} %" if system == "c" else "–"
        out.append(
            f"| {name} | {len(rs)} | {ci(by(lambda r: r['fit']))} | {ci(by(lambda r: bool(r['ref'] and r['ref']['kept'])))} "
            f"| {100 * np.mean([bool(r['ref'] and r['ref']['added']) for r in usable]) if usable else 0:.0f} % "
            f"| {100 * np.mean([bool(r['ref'] and r['ref']['dropped']) for r in usable]) if usable else 0:.0f} % "
            f"| {ci(by(lambda r: bool(r['src'] and r['src']['kept'])))} "
            f"| {mean([r['ratio'] for r in usable])} | {mean([r['compression'] for r in usable])} | {lens} "
            f"| {kept_plain} | {mean([r['rounds'] for r in rs]) if system == 'c' else '–'} "
            f"| {sum(r['wrong_language'] for r in rs)} | {sum(not r['text'] for r in rs)} |")
    return out


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Step 4 tables.")
    ap.add_argument("run", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--device", default=None, help="NLI device (default: cuda, then mps, then cpu)")
    args = ap.parse_args(argv)
    cfg = json.loads((args.run / "config.json").read_text(encoding="utf-8"))
    items = [json.loads(line) for line in (args.run / "items.jsonl").read_text(encoding="utf-8").splitlines() if line]
    from isochron.metrics.meaning import NLI

    nli = NLI(device=args.device)
    rows = outputs(items)
    score(rows, cfg["length_counter"]["counter"], nli)
    out = args.out or Path("results") / f"{args.run.name}.md"
    lines = [
        f"# Step 4 ({args.run.name}): translation to a length budget",
        "",
        f"- Date: {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC",
        f"- Git commit (report): {git_commit()}; run: `{args.run.name}` ({cfg['git_commit'][:7]})",
        f"- Model: {cfg['model']}, quantisation {cfg['quantisation']}, endpoint {cfg['endpoint']}, "
        f"backend {cfg['backend'].get('build_info', cfg['backend'].get('type'))}",
        f"- Generation: {json.dumps(cfg['generation'])}; seeds {cfg['seeds']} ({cfg['round_seed']})",
        "- Prompts: " + ", ".join(f"`{p['name']}` ({p['sha256'][:12]})" for p in cfg["prompts"].values()),
        f"- Systems: (b) {cfg['selection_b']}; (c) {cfg['shorten_c']}",
        f"- Budgets: {json.dumps(cfg['budgets'])}; syllable rates {json.dumps(cfg['rates'])}; length counter "
        f"{cfg['length_counter']['syllables']}",
        f"- Meaning: NLI {nli.describe()}; language check {describe_language()}",
        f"- Items: {cfg['items']['selection']}; sentences {json.dumps(cfg['items']['n'])}; split {cfg['split']}; TTS: none",
        f"- 95 % intervals: bootstrap over sentences, {N_BOOT} resamples, seed {BOOT_SEED}."
        + (" Dev split: exploratory." if cfg["split"] == "dev" else ""),
        "",
        "Fit, kept, added and dropped are in %. (a) is the same translation under both budgets; its fit says how",
        "often plain translation already meets the budget.",
        "",
    ]
    groups = defaultdict(list)
    for r in rows:
        groups[r["lang"], r["budget"]].append(r)
    for (lang, kind), rs in sorted(groups.items()):
        lines += table(rs, f"EN → {lang.upper()}, {kind} budget ({rs[0]['unit']})") + [""]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"wrote {out.resolve()}")


if __name__ == "__main__":
    main()
