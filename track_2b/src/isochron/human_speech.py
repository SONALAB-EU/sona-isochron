"""The human-speech check: do syllables or characters predict how long people take to read a line?

Exploratory, post-hoc, added after test outputs existed (docs/eval_protocol.md, v2.27). CPU only.

The FLEURS test recordings that data/fleurs_{de,fr}_test.jsonl name (English, German, French) are measured
again from the audio, trimmed as slot_s was (isochron.time_check.measure, the same as build_fleurs), and
must match the stored durations. Recordings flagged noisy are skipped.

(a) Per language: Pearson r of syllables with seconds; seconds per syllable (Σ s ÷ Σ syllables) against
    Pellegrino et al.'s rates, which step 4's syllable budget uses.
(b) Per sentence (both recordings clean): the human reading fits when its seconds are within ±10 % of the
    English slot; a ruler fits when the reference's length is within ±10 % of step 4's budget. Agreement
    (share, Cohen's kappa) and Pearson / Spearman r of length ÷ budget with seconds ÷ slot, with 95 %
    bootstrap intervals over sentences and paired differences syllables − characters.

    uv run python -m isochron.human_speech        # writes results/human_speech.md and .csv
"""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from isochron.metrics.length import counter_description, hit, length
from isochron.provenance import git_commit
from isochron.step4 import RATES

LANGS = ("de", "fr")
CONFIGS = {"en": "en_us", "de": "de_de", "fr": "fr_fr"}
N_BOOT, SEED = 10_000, 0
TOLERANCE = 0.10
OUT = Path("results/human_speech.md")


def kappa(a: np.ndarray, b: np.ndarray) -> float:
    """Cohen's kappa of two boolean arrays (nan when chance agreement is 1)."""
    a, b = a.astype(bool), b.astype(bool)
    po = float(np.mean(a == b))
    pe = float(np.mean(a) * np.mean(b) + (1 - np.mean(a)) * (1 - np.mean(b)))
    return float("nan") if pe == 1 else (po - pe) / (1 - pe)


def spearman(x: np.ndarray, y: np.ndarray) -> float:
    rank = lambda v: np.argsort(np.argsort(v, kind="stable"), kind="stable").astype(float)  # noqa: E731
    return float(np.corrcoef(rank(x), rank(y))[0, 1])


def pearson(x: np.ndarray, y: np.ndarray) -> float:
    return float(np.corrcoef(x, y)[0, 1])


def boot(stat, *arrays: np.ndarray, n: int = N_BOOT, seed: int = SEED) -> tuple[float, float, float]:
    """The statistic and its 95 % percentile bootstrap interval, resampling the rows of all arrays together."""
    rng = np.random.default_rng(seed)
    k = len(arrays[0])
    values = [stat(*(a[idx] for a in arrays)) for idx in (rng.integers(0, k, k) for _ in range(n))]
    lo, hi = np.nanpercentile(values, [2.5, 97.5])
    return stat(*arrays), float(lo), float(hi)


def fmt(v: tuple[float, float, float], digits: int = 2, pct: bool = False, signed: bool = False) -> str:
    scale, places = (100, 1) if pct else (1, digits)
    f = lambda x: f"{scale * x:{'+' if signed else ''}.{places}f}".replace("-", "−")  # noqa: E731
    return f"{f(v[0])} [{f(v[1])}, {f(v[2])}]"


def durations(config: str, wanted: set[str]) -> dict[str, float]:
    """Trimmed seconds of the wanted recordings (by recording id) of one FLEURS test config."""
    import pyarrow.parquet as pq
    import soundfile as sf

    from isochron.data.build_fleurs import SPLITS, recording_id
    from isochron.data.fleurs import fetch
    from isochron.time_check import measure

    pf = pq.ParquetFile(fetch(f"parquet-data/{config}/{SPLITS['test']}-00000-of-00001.parquet"))
    out: dict[str, float] = {}
    for batch in pf.iter_batches(batch_size=64, columns=["audio"]):
        audio = batch.column(0)
        for k, path in enumerate(audio.field("path").to_pylist()):
            if (rid := recording_id(path)) in wanted:
                y, sr = sf.read(io.BytesIO(audio.field("bytes")[k].as_py()), dtype="float32")
                out[rid] = round(measure(y, sr).trimmed_s, 3)
    if missing := wanted - out.keys():
        raise SystemExit(f"{config}: no audio for {sorted(missing)[:5]}")
    return out


def main() -> None:
    commit = git_commit()
    data = {lang: [json.loads(line) for line in Path(f"data/fleurs_{lang}_test.jsonl").read_text(encoding="utf-8").splitlines()]
            for lang in LANGS}
    measured = {"en": durations("en_us", {r["src_recording_id"] for lang in LANGS for r in data[lang]})}
    for lang in LANGS:
        measured[lang] = durations(CONFIGS[lang], {r["tgt_recording_id"] for r in data[lang]})
    mismatch = [(lang, r["id"]) for lang in LANGS for r in data[lang]
                if abs(measured["en"][r["src_recording_id"]] - r["slot_s"]) > 0.0015
                or abs(measured[lang][r["tgt_recording_id"]] - r["ref_tgt_s"]) > 0.0015]
    if mismatch:
        raise SystemExit(f"re-measured durations differ from the stored ones: {mismatch[:5]}")

    lines = ["# Human speech: syllables, characters and seconds (exploratory, post-hoc)", "",
             "Post-hoc, added after test outputs existed (protocol v2.27, planned before computing). FLEURS test, read by "
             "people; no TTS.", "",
             f"- Date: {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC; git commit {commit}",
             "- Data: google/fleurs @ 70bb2e8 (CC BY 4.0), `en_us`, `de_de`, `fr_fr` test, the recording "
             "`data/fleurs_{de,fr}_test.jsonl` names per sentence; trimmed as `slot_s` (16 kHz, librosa.effects.trim "
             "top_db 30, frame 2048, hop 512). Re-measured from the audio: every duration equals the stored one.",
             f"- Syllables: {counter_description('espeak')}; characters without spaces. Model, quantisation, endpoint, "
             "TTS: none (human recordings). Bootstrap: 10,000 resamples over sentences, seed 0.", ""]
    rows = []
    # (a) per language
    per_lang = {}
    en_seen: dict[str, tuple[str, float]] = {}
    for lang in LANGS:
        for r in data[lang]:
            if not r["noisy_src"]:
                en_seen[r["id"]] = (r["src_text"], r["slot_s"])
    per_lang["en"] = [(text, s) for text, s in en_seen.values()]
    for lang in LANGS:
        per_lang[lang] = [(r["ref_text"], r["ref_tgt_s"]) for r in data[lang] if not r["noisy_tgt"]]
    table_a = ["| Language | Recordings | r (syllables, seconds) | s per syllable | Syllables per s | Pellegrino | "
               "Rate ÷ EN, measured | Rate ÷ EN, budget |", "|---|---:|---|---:|---:|---:|---:|---:|"]
    rate = {}
    for lang in ("en", *LANGS):
        syl = np.array([length(t, "syllables", lang) for t, _ in per_lang[lang]], float)
        sec = np.array([s for _, s in per_lang[lang]], float)
        rate[lang] = (syl, sec)
    en_rate = rate["en"][0].sum() / rate["en"][1].sum()
    for lang in ("en", *LANGS):
        syl, sec = rate[lang]
        r_ = boot(pearson, syl, sec)
        sps = syl.sum() / sec.sum()
        ratio_b = RATES[lang] / RATES["en"]
        table_a.append(f"| {lang.upper()} | {len(sec)} | {fmt(r_)} | {sec.sum() / syl.sum():.3f} | {sps:.2f} | "
                       f"{RATES[lang]:.2f} | {sps / en_rate:.3f} | {ratio_b:.3f} |")
    lines += ["## (a) Syllables and seconds, per language", "",
              "Seconds are trimmed only at the ends, so pauses inside a sentence count: the rates are lower than "
              "Pellegrino et al.'s.", "", *table_a, ""]
    # (b) per sentence
    lines += ["## (b) Does a ruler predict whether the human reading fits the English slot?", ""]
    for lang in LANGS:
        clean = [r for r in data[lang] if not r["noisy_src"] and not r["noisy_tgt"]]
        human = np.array([abs(r["ref_tgt_s"] - r["slot_s"]) <= TOLERANCE * r["slot_s"] + 1e-9 for r in clean])
        dur_ratio = np.array([r["ref_tgt_s"] / r["slot_s"] for r in clean])
        ruler = {}
        for name, unit in (("syllables", "syllables"), ("characters", "chars")):
            budget = np.array([int(length(r["src_text"], "syllables", "en") * RATES[lang] / RATES["en"] + 0.5)
                               if unit == "syllables" else length(r["src_text"], "chars", "en") for r in clean])
            got = np.array([length(r["ref_text"], unit, lang) for r in clean])
            ruler[name] = (np.array([hit(int(g), int(b)) for g, b in zip(got, budget)]), got / budget)
            for r, b, g in zip(clean, budget, got):
                rows.append({"lang": lang, "id": r["id"], "ruler": name, "budget": int(b), "length": int(g),
                             "length_ratio": round(float(g / b), 4), "slot_s": r["slot_s"], "ref_s": r["ref_tgt_s"],
                             "duration_ratio": round(r["ref_tgt_s"] / r["slot_s"], 4),
                             "ruler_fits": int(hit(int(g), int(b))), "human_fits": int(abs(r["ref_tgt_s"] - r["slot_s"]) <= TOLERANCE * r["slot_s"] + 1e-9)})
        agree = lambda f, h: float(np.mean(f == h))  # noqa: E731
        t = ["| Ruler | Ruler fits | Agreement with the human fit (%) | Cohen's kappa | Pearson r, ratios | Spearman r, ratios |",
             "|---|---:|---|---|---|---|"]
        for name, (fit, ratio) in ruler.items():
            t.append(f"| {name} | {int(fit.sum())}/{len(fit)} | {fmt(boot(agree, fit, human), pct=True)} | "
                     f"{fmt(boot(kappa, fit, human))} | {fmt(boot(pearson, ratio, dur_ratio))} | {fmt(boot(spearman, ratio, dur_ratio))} |")
        (fs, rs), (fc, rc) = ruler["syllables"], ruler["characters"]
        d_agree = boot(lambda a, b, h: agree(a, h) - agree(b, h), fs, fc, human)
        d_kappa = boot(lambda a, b, h: kappa(a, h) - kappa(b, h), fs, fc, human)
        d_r = boot(lambda a, b, d: pearson(a, d) - pearson(b, d), rs, rc, dur_ratio)
        lines += [f"### EN → {lang.upper()}: {len(clean)} sentences with both recordings clean; the human reading fits the "
                  f"English slot in {int(human.sum())} ({100 * human.mean():.1f} %)", "", *t, "",
                  f"Syllables − characters (paired): agreement {fmt(d_agree, pct=True, signed=True)} points; kappa "
                  f"{fmt(d_kappa, signed=True)}; Pearson r {fmt(d_r, signed=True)}.", ""]
    OUT.write_text("\n".join(lines), encoding="utf-8")
    with open(OUT.with_suffix(".csv"), "w", encoding="utf-8", newline="") as f:
        f.write(f"# written by isochron.human_speech, git commit {commit}; one row per sentence and ruler; FLEURS test, "
                "recordings flagged noisy left out\n")
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
