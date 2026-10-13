"""Too long and not too long (protocol v2.36; post-hoc, added after test outputs existed).

Running long can overlap the next speech segment; running short is tolerable. Per output: too long = a usable
output (an answer in the target language) over 1.10 × the budget; not too long = a usable output at most
1.10 × the budget; a missing or wrong-language output is neither. The pre-registered fit stays the main
metric.

- Step 4 (results/step4_test_lengths.csv): (a), (b) and (c) in all four settings, as shares of all outputs
  with 95 % bootstrap intervals over sentences, and paired differences (c) − (a) and (c) − (b).
- Timing tests (seconds against the English slot): (a) and (c), with exact McNemar on too long.

    uv run python -m isochron.too_long        # writes results/step4_too_long.md
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from isochron.provenance import git_commit
from isochron.time_check import mcnemar_exact

LENGTHS = Path("results/step4_test_lengths.csv")
TIMING = (("Qwen3-TTS, syllable budget (21 sheet sources)", Path("results/time_check/durations_qwen.csv")),
          ("Qwen3-TTS, voice-calibrated budget (99 test sources)", Path("results/time_check/calibrated/durations.csv")))
OUT = Path("results/step4_too_long.md")
N_BOOT, SEED, LIMIT = 10_000, 0, 1.10
SETTINGS = (("de", "isometric", "DE, characters"), ("de", "isosyllabic", "DE, syllables"),
            ("fr", "isometric", "FR, characters"), ("fr", "isosyllabic", "FR, syllables"))
NAMES = {"a": "(a) plain", "b": "(b) one step", "c": "(c) ours"}


def classify(ratio: str, usable: bool) -> tuple[int, int]:
    """(too long, not too long) of one output."""
    if not usable or ratio == "":
        return 0, 0
    r = float(ratio)
    return int(r > LIMIT + 1e-9), int(r <= LIMIT + 1e-9)


def boot(per_id: dict[str, dict[str, np.ndarray]], ids: list[str], f, n: int = N_BOOT, seed: int = SEED):
    """f(sums by system) over sentence resamples: the point value and a 95 % percentile interval."""
    idx = np.random.default_rng(seed).integers(0, len(ids), size=(n, len(ids)))
    stacked = {s: np.array([per_id[s][i] for i in ids]) for s in per_id}  # ids × (k, n)
    point = f({s: v.sum(axis=0) for s, v in stacked.items()})
    values = [f({s: v[row].sum(axis=0) for s, v in stacked.items()}) for row in idx]
    lo, hi = np.percentile(values, [2.5, 97.5])
    return point, lo, hi


def fmt(v, signed: bool = False) -> str:
    f = (lambda x: f"{100 * x:+.1f}") if signed else (lambda x: f"{100 * x:.1f}")
    return f"{f(v[0])} [{f(v[1])}, {f(v[2])}]".replace("-", "−")


def step4_tables() -> list[str]:
    rows = list(csv.DictReader(line for line in LENGTHS.read_text(encoding="utf-8").splitlines() if not line.startswith("#")))
    out = []
    for lang, budget, label in SETTINGS:
        per_id: dict[str, dict[str, np.ndarray]] = {}
        for r in rows:
            if r["lang"] == lang and r["budget"] == budget and r["system"] in NAMES:
                usable = r["no_output"] == "0" and r["wrong_language"] == "0"
                long, ok = classify(r["ratio"], usable)
                cell = per_id.setdefault(r["system"], {}).setdefault(r["id"], np.zeros(3))
                cell += (long, ok, 1)
        ids = sorted(set.intersection(*(set(v) for v in per_id.values())), key=int)
        share = lambda k: (lambda s, sys: s[sys][k] / s[sys][2])  # noqa: E731
        out += [f"### EN → {label}: {len(ids)} sentences × seeds", "",
                "| System | Too long | Not too long | Neither (missing or wrong language) |", "|---|---|---|---:|"]
        for s in NAMES:
            sums = sum(per_id[s][i] for i in ids)
            out.append(f"| {NAMES[s]} | {fmt(boot(per_id, ids, lambda t, s=s: share(0)(t, s)))} | "
                       f"{fmt(boot(per_id, ids, lambda t, s=s: share(1)(t, s)))} | "
                       f"{int(sums[2] - sums[0] - sums[1])} of {int(sums[2])} |")
        out += ["", "| Paired (post-hoc) | Too long | Not too long |", "|---|---|---|"]
        for other in ("a", "b"):
            out.append(f"| (c) − {NAMES[other].split()[0]} | "
                       + " | ".join(fmt(boot(per_id, ids, lambda t, k=k, o=other: share(k)(t, "c") - share(k)(t, o)),
                                        signed=True) for k in (0, 1)) + " |")
        out.append("")
    return out


def timing_tables() -> list[str]:
    out = ["| Timing test | n | (a) too long | (c) too long | (a) not too long | (c) not too long | McNemar p, too long |",
           "|---|---:|---:|---:|---:|---:|---:|"]
    for label, path in TIMING:
        rows = list(csv.DictReader(line for line in path.read_text(encoding="utf-8").splitlines()))
        if "a_s" in rows[0]:  # the calibrated run: one row per source
            pairs = [(float(r["a_s"]), float(r["c_s"]), float(r["english_slot_s"])) for r in rows]
        else:  # the 21-source run: one row per source and system
            by = {(r["id"], r["system"]): r for r in rows if r["purpose"] == "time_check"}
            pairs = [(float(by[(i, "a")]["median_s"]), float(by[(i, "c")]["median_s"]), float(by[(i, "a")]["english_slot_s"]))
                     for i in sorted({i for i, _ in by}, key=int) if (i, "a") in by and (i, "c") in by]
        long_a = [a > LIMIT * s + 1e-9 for a, _, s in pairs]
        long_c = [c > LIMIT * s + 1e-9 for _, c, s in pairs]
        n = len(pairs)
        p = mcnemar_exact(sum(lc and not la for la, lc in zip(long_a, long_c)), sum(la and not lc for la, lc in zip(long_a, long_c)))
        out.append(f"| {label} | {n} | {sum(long_a)} | {sum(long_c)} | {n - sum(long_a)} | {n - sum(long_c)} | {p:.2g} |")
    return out


def main() -> None:
    md = ["# Too long and not too long (post-hoc)", "",
          "Post-hoc, added after test outputs existed (protocol v2.36). Running long can overlap the next speech segment; "
          "running short is tolerable. The pre-registered fit (within ±10 %) stays the main metric.", "",
          f"- Date: {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC; git commit {git_commit()}",
          "- Step 4: `results/step4_test_lengths.csv` (FLEURS test; Apertus 1.5 8B, BF16, vLLM on the cluster, endpoints "
          "in `results/step4_test.md`; seeds 0, 1, 2; 347 German and 332 French sentences). TTS: none for step 4.",
          f"- Too long: a usable output over {LIMIT:.2f} × the budget; not too long: a usable output at most {LIMIT:.2f} × "
          "the budget; a missing or wrong-language output is neither. Shares of all outputs, in %, with 95 % bootstrap "
          f"intervals over sentences ({N_BOOT:,} resamples, seed {SEED}); paired differences in points.",
          "- Timing tests: Qwen3-TTS (voice Aiden), seconds against the English slot (`results/time_check_qwen.md`, "
          "`results/time_check_calibrated.md`).", "", "## Step 4", "", *step4_tables(), "## Timing tests", "",
          *timing_tables(), ""]
    OUT.write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
