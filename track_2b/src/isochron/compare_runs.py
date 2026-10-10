"""Compare two repair-loop runs on the same items (for example HPC BF16 against local Q4).

For every (sentence, level, seed) in both runs, side by side: the output without the loop (closest
round-0 candidate) and with it, its syllables against T, fit, NLI kept, language and revision rounds.
Writes a markdown file with both runs' provenance.

    uv run python -m isochron.compare_runs RUN_A RUN_B --out results/FILE.md
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from isochron.language import check as check_language
from isochron.provenance import git_commit


def load(run: Path) -> tuple[dict, dict]:
    cfg = json.loads((run / "config.json").read_text(encoding="utf-8"))
    items = {(it["id"], it["level"], it["seed"]): it
             for it in map(json.loads, (run / "items.jsonl").read_text(encoding="utf-8").splitlines()) if it}
    return cfg, items


def cell(c: dict | None, target: int, lang: str) -> tuple[str, bool, bool]:
    if not c:
        return "(no output)", False, False
    wrong = check_language(c["text"], lang).wrong
    fit, kept = c["hit"] and not wrong, c["kept"] and not wrong
    flags = f"{c['syllables']}/{target} syll, {'fit' if fit else 'no fit'}, {'kept' if kept else 'not kept'}"
    return f"{c['text']} *({flags}{', wrong language' if wrong else ''})*", fit, kept


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("run_a", type=Path)
    ap.add_argument("run_b", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    (cfg_a, items_a), (cfg_b, items_b) = load(args.run_a), load(args.run_b)
    keys = sorted(items_a.keys() & items_b.keys(), key=lambda k: (int(k[0]), -k[1], k[2]))
    if not keys:
        raise SystemExit("the runs share no items")
    lang = cfg_a["lang"]
    names = [f"A = `{args.run_a.name}`", f"B = `{args.run_b.name}`"]
    lines = [f"# Same items, two runs: {args.run_a.name} vs {args.run_b.name}", "",
             f"- Date: {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC; git commit (report): {git_commit()}"]
    for name, cfg in zip(names, (cfg_a, cfg_b)):
        lines.append(f"- {name}: model {cfg['model']}, quantisation {cfg['quantisation']}, endpoint {cfg['endpoint']}, "
                     f"backend {cfg['backend'].get('build_info')}, commit {cfg['git_commit'][:7]}, prompt "
                     f"`{cfg['prompt']['name']}` ({cfg['prompt']['sha256'][:12]}), generation {json.dumps(cfg['generation'])}")
    lines += [f"- Items: {len(keys)} (sentence, level, seed) in both runs; language {lang}; TTS: none", ""]
    totals = {"A": [0, 0, 0, 0, 0], "B": [0, 0, 0, 0, 0]}  # fit without, kept without, fit with, kept with, rounds
    rows = []
    for key in keys:
        sid, level, seed = key
        for tag, items in (("A", items_a), ("B", items_b)):
            it = items[key]
            without, fit0, kept0 = cell(it.get("closest_round0"), it["target"], lang)
            with_, fit1, kept1 = cell(it.get("final"), it["target"], lang)
            t = totals[tag]
            t[0] += fit0
            t[1] += kept0
            t[2] += fit1
            t[3] += kept1
            t[4] += it["revisions"]
            rows.append(f"| {sid} | {level} | {seed} | {tag} | {without} | {with_} | {it['revisions']} |")
    n = len(keys)
    lines += ["| Run | Fit without the loop | Kept without | Fit with the loop | Kept with | Avg. rounds |",
              "|-----|---------------------:|-------------:|------------------:|----------:|------------:|"]
    for tag, t in totals.items():
        lines.append(f"| {tag} | {t[0]}/{n} | {t[1]}/{n} | {t[2]}/{n} | {t[3]}/{n} | {t[4] / n:.2f} |")
    lines += ["", "Fit: within ±10 % of T in syllables; kept: the loop's NLI, both ways. A wrong-language output",
              "counts as neither. These are a handful of items: a smoke test, not a measurement of a difference.", "",
              "| Id | Level | Seed | Run | Without the loop | With the loop | Rounds |",
              "|----|------:|-----:|-----|------------------|---------------|-------:|", *rows]
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[: 12 + len(totals)]))
    print(f"wrote {args.out.resolve()}")


if __name__ == "__main__":
    main()
