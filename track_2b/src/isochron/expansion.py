"""How much longer are German and French than English? (protocol v2.35; post-hoc, descriptive)

FLEURS test, per language: target ÷ English for characters without spaces, words and syllables, for the
human reference and for Apertus's plain translation (a) at generation seed 0; the share longer than the
English and longer by more than 10 %; and the human readings' duration ratio where neither recording is
flagged noisy. Medians with 95 % bootstrap intervals over sentences, shares with Wilson intervals.

    uv run python -m isochron.expansion        # writes results/expansion_en_de_fr.md
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from isochron.language import check as check_language
from isochron.metrics.length import counter_description, length
from isochron.native_check import wilson
from isochron.provenance import git_commit

RUNS = {"de": Path("results/raw/hpc_8b_step4_test"), "fr": Path("results/raw/hpc_8b_step4_test_fr")}
UNITS = (("characters", "chars"), ("words", "words"), ("syllables", "syllables"))
N_BOOT, SEED, GEN_SEED, LONG = 10_000, 0, 0, 70
OUT = Path("results/expansion_en_de_fr.md")


def median_ci(values: np.ndarray, n: int = N_BOOT, seed: int = SEED) -> tuple[float, float, float]:
    rng = np.random.default_rng(seed)
    meds = np.median(values[rng.integers(0, len(values), (n, len(values)))], axis=1)
    lo, hi = np.percentile(meds, [2.5, 97.5])
    return float(np.median(values)), float(lo), float(hi)


def share(k: int, n: int) -> str:
    lo, hi = wilson(k, n)
    return f"{100 * k / n:.0f} % [{100 * lo:.0f}, {100 * hi:.0f}]"


def row(label: str, ratios: np.ndarray) -> str:
    m, lo, hi = median_ci(ratios)
    return (f"| {label} | {len(ratios)} | {m:.2f} [{lo:.2f}, {hi:.2f}] | {share(int((ratios > 1).sum()), len(ratios))} | "
            f"{share(int((ratios > 1.10).sum()), len(ratios))} |")


def main() -> None:
    commit = git_commit()
    md = ["# How much longer are German and French than English? (post-hoc, descriptive)", "",
          "Post-hoc, added after test outputs existed (protocol v2.35).", "",
          f"- Date: {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC; git commit {commit}",
          "- Data: FLEURS test (google/fleurs @ 70bb2e8, CC BY 4.0): the English source, the human reference "
          "translation and its reading; Apertus's plain translation (a) at generation seed 0 from the step 4 test "
          "runs (Apertus 1.5 8B, BF16, vLLM on the cluster; endpoints in `results/step4_test.md`). TTS: none.",
          f"- Lengths: characters without spaces, words, and syllables ({counter_description('espeak')}). Duration: "
          "the human readings, trimmed as `slot_s` (16 kHz, librosa trim at 30 dB), where neither recording is "
          "flagged noisy.",
          f"- Ratio = target ÷ English per sentence. Median with a 95 % bootstrap interval ({N_BOOT:,} resamples "
          f"over sentences, seed {SEED}); shares with 95 % Wilson intervals.",
          "- Context: W3C, \"Text size in translation\" (https://www.w3.org/International/articles/article-text-size), "
          "citing IBM's guidance that European-language translations of English text over 70 characters run to "
          "about 130 % of its length. The last rows of each table keep English sources over 70 characters "
          "(with spaces, as that guidance counts them).", ""]
    for lang in ("de", "fr"):
        data = [json.loads(line) for line in Path(f"data/fleurs_{lang}_test.jsonl").read_text(encoding="utf-8").splitlines()]
        plain = {}
        for it in map(json.loads, (RUNS[lang] / "items.jsonl").read_text(encoding="utf-8").splitlines()):
            if it and it["seed"] == GEN_SEED and it["a"]["text"] and not check_language(it["a"]["text"], lang).wrong:
                plain[it["id"]] = it["a"]["text"]
        md += [f"## EN → {lang.upper()}: {len(data)} sentences", "",
               "| Text | n | Median ratio | Longer than the English | Longer by > 10 % |", "|---|---:|---|---|---|"]
        for name, unit in UNITS:
            en = {r["id"]: length(r["src_text"], unit, "en") for r in data}
            ref = np.array([length(r["ref_text"], unit, lang) / en[r["id"]] for r in data])
            pl = np.array([length(plain[r["id"]], unit, lang) / en[r["id"]] for r in data if r["id"] in plain])
            md += [row(f"{name}: human reference", ref), row(f"{name}: plain translation (a)", pl)]
        clean = [r for r in data if not r["noisy_src"] and not r["noisy_tgt"]]
        md.append(row("seconds: human readings (recordings not noisy)",
                      np.array([r["ref_tgt_s"] / r["slot_s"] for r in clean])))
        long = [r for r in data if len(r["src_text"]) > LONG]
        en_c = {r["id"]: length(r["src_text"], "chars", "en") for r in long}
        md += [row(f"characters, English > {LONG} characters: human reference",
                   np.array([length(r["ref_text"], "chars", lang) / en_c[r["id"]] for r in long])),
               row(f"characters, English > {LONG} characters: plain translation (a)",
                   np.array([length(plain[r["id"]], "chars", lang) / en_c[r["id"]] for r in long if r["id"] in plain])),
               ""]
    OUT.write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
