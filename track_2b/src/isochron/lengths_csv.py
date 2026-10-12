"""results/step2_test_lengths.csv: the length of every step 2 output, for the figures.

Raw runs stay out of git (results/raw/), so `make figures` reads this committed file instead. One row
per output: each (sentence, level, seed) of each run, without the loop (the closest round-0
candidate) and with it, scored as isochron.pilot_report scores them. It holds numbers only, no text.
The lines starting with # record how it was made.

    uv run python -m isochron.lengths_csv RUN_DIR [RUN_DIR ...] --out results/step2_test_lengths.csv
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path

from isochron.pilot_report import rows_for, short
from isochron.provenance import git_commit

FIELDS = ("lang", "id", "level", "seed", "loop", "target_syllables", "output_syllables", "ratio", "fit",
          "wrong_language", "no_output")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("runs", type=Path, nargs="+")
    ap.add_argument("--out", type=Path, default=Path("results/step2_test_lengths.csv"))
    args = ap.parse_args(argv)
    header, body = [], []
    for run in args.runs:
        cfg, rows = rows_for(run)
        header.append(f"# run {run.name} ({short(cfg['git_commit'])}): {cfg['lang']} {cfg['split']}, model {cfg['model']}, "
                      f"quantisation {cfg['quantisation']}, endpoint {cfg['endpoint']}, levels {cfg['levels']}, "
                      f"seeds {cfg['seeds']}, {cfg['items']['n']} sentences")
        for r in sorted(rows, key=lambda r: (int(r["id"]), -r["level"], r["seed"], r["cond"] != "without")):
            body.append({"lang": cfg["lang"], "id": r["id"], "level": r["level"], "seed": r["seed"], "loop": r["cond"],
                         "target_syllables": r["target"],
                         "output_syllables": "" if r["syllables"] is None else r["syllables"],
                         "ratio": "" if r["ratio"] is None else f"{r['ratio']:.4f}",
                         "fit": int(r["fit"]), "wrong_language": int(r["wrong_language"]),
                         "no_output": int(r["no_output"])})
    with open(args.out, "w", encoding="utf-8", newline="") as f:
        f.write(f"# Step 2 output lengths, written by isochron.lengths_csv on "
                f"{datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC, git commit {git_commit()}\n")
        f.write("# ratio = output syllables / target syllables, only for an answer in the right language; fit = within "
                "±10 % of the target; TTS: none\n")
        for line in header:
            f.write(line + "\n")
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(body)
    print(f"wrote {len(body)} rows to {args.out}")


if __name__ == "__main__":
    main()
