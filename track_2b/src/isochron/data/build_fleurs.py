"""Build the FLEURS EN→DE/FR/IT line files that the experiments read.

Source: google/fleurs on Hugging Face, pinned to REVISION. The repo has no
loading script any more: its configs are served from the parquet files under
parquet-data/. We download exactly the files we need (en_us, de_de, fr_fr,
it_it × validation, test) and read them with pyarrow. FLEURS "validation" is
called "dev" in our files. Downloads go to the Hugging Face cache
(~/.cache/huggingface); no audio is written to the repo.

Licence: FLEURS is CC BY 4.0, but its sentences come from FLoRes-101, which
is CC BY-SA 4.0 upstream, so every record carries license="CC-BY-SA-4.0".

For every target language and split:

- EN and target recordings are joined by FLEURS sentence id.
- If a sentence has several recordings in a language, we use the one with the
  smallest numeric recording id (its WAV file name). The rule never looks at
  the audio, so it cannot favour fast or slow speakers.
- Durations are measured after trimming leading and trailing silence with
  librosa.effects.trim (TRIM below) at the native 16 kHz, then rounded to
  1 ms. slot_s is the EN duration, ref_tgt_s the target duration.
- noisy_src / noisy_tgt: the recording's noise floor (5th percentile of frame
  RMS in dB relative to the loudest frame, on the frames trim uses) is above
  -top_db. Trim cannot remove noise that loud, so the duration is too long.
- A line is over-long when ref_tgt_s > 1.10 × slot_s, on the rounded values.

The audio-based fields are not valid until trimming is fixed (VAD, planned for
the isochrony step); the main experiments do not use them.

Writes data/fleurs_{lang}_{split}.jsonl, data/overlong_{lang}_{split}.jsonl
and results/fleurs_stats.md. Run from track_2b/:

    uv run python -m isochron.data.build_fleurs
"""

from __future__ import annotations

import argparse
import io
import random
import re
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from typing import Any

import librosa
import numpy as np
import pyarrow.parquet as pq
import soundfile as sf

from isochron.data.fleurs import REPO_ID, REVISION, fetch
from isochron.provenance import git_commit
from isochron.schema import OverlongRecord, SentenceRecord, write_jsonl

LICENSE = "CC-BY-SA-4.0"
SRC_LANG, SRC_CONFIG = "en", "en_us"
TGT_CONFIGS = {"de": "de_de", "fr": "fr_fr", "it": "it_it"}
SPLITS = {"dev": "validation", "test": "test"}  # our name -> FLEURS parquet split
RAW_SPLITS = ("train", "dev", "test")  # split names in the raw release's TSVs
SAMPLE_RATE = 16_000
TRIM: dict[str, Any] = {"top_db": 30, "ref": np.max, "frame_length": 2048, "hop_length": 512}
TRIM_DESC = "librosa.effects.trim(top_db=30, ref=np.max, frame_length=2048, hop_length=512)"
NOISY_FLOOR_DB = -TRIM["top_db"]
OVERLONG = 1.10
SAMPLE_SEED = 0
N_SAMPLES = 5  # joined pairs printed per target language


@dataclass(frozen=True)
class Sentence:
    id: int
    text: str
    """raw_transcription: the cased, punctuated sentence."""
    recording_id: str
    raw_s: float
    """Duration of the chosen recording before trimming."""
    trimmed_s: float
    floor_db: float
    """Noise floor: 5th percentile of frame RMS in dB re the loudest frame."""

    @property
    def noisy(self) -> bool:
        """The noise is louder than trim's threshold, so trim left it in place."""
        return self.floor_db > NOISY_FLOOR_DB


@dataclass
class Split:
    sentences: dict[int, Sentence]
    recordings: set[tuple[int, str]]
    """Every (sentence id, recording id) in the parquet split."""


def recording_id(path: str) -> str:
    return Path(path).stem


def measure(wav: bytes) -> tuple[float, float, float]:
    """(raw s, trimmed s, noise floor dB) of one WAV recording.

    The noise floor uses the same frames and dB scale as trim, so a floor
    above -top_db means trim cannot remove the leading and trailing noise.
    """
    y, sr = sf.read(io.BytesIO(wav), dtype="float32")
    if sr != SAMPLE_RATE or y.ndim != 1:
        raise ValueError(f"expected mono {SAMPLE_RATE} Hz audio, got {sr} Hz, shape {y.shape}")
    _, (start, end) = librosa.effects.trim(y, **TRIM)
    if end <= start:
        raise ValueError("recording is silent after trimming")
    rms = librosa.feature.rms(y=y, frame_length=TRIM["frame_length"], hop_length=TRIM["hop_length"])[0]
    floor_db = float(np.percentile(librosa.amplitude_to_db(rms, ref=np.max, top_db=None), 5))
    return len(y) / sr, (end - start) / sr, floor_db


def load_split(config: str, split: str) -> Split:
    """Choose one recording per sentence and measure it."""
    pf = pq.ParquetFile(fetch(f"parquet-data/{config}/{SPLITS[split]}-00000-of-00001.parquet"))
    rows = pf.read(columns=["id", "path", "raw_transcription"]).to_pylist()
    recordings = {(r["id"], recording_id(r["path"])) for r in rows}
    if len({rid for _, rid in recordings}) != len(rows):
        raise ValueError(f"{config}/{split}: duplicate recording ids")

    by_id: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        by_id[r["id"]].append(r)
    chosen: dict[str, dict[str, Any]] = {}
    for sid, recs in by_id.items():
        if len({r["raw_transcription"] for r in recs}) != 1:
            raise ValueError(f"{config}/{split}: sentence {sid} has different texts across recordings")
        best = min(recs, key=lambda r: int(recording_id(r["path"])))
        chosen[recording_id(best["path"])] = best

    durations: dict[str, tuple[float, float, float]] = {}
    for batch in pf.iter_batches(batch_size=64, columns=["audio"]):
        audio = batch.column(0)
        for k, path in enumerate(audio.field("path").to_pylist()):
            rid = recording_id(path)
            if rid in chosen:
                durations[rid] = measure(audio.field("bytes")[k].as_py())
    if missing := chosen.keys() - durations.keys():
        raise ValueError(f"{config}/{split}: no audio for recordings {sorted(missing)[:5]}")

    sentences = {
        r["id"]: Sentence(r["id"], r["raw_transcription"], rid, *durations[rid])
        for rid, r in chosen.items()
    }
    print(f"{config} {split}: {len(rows)} recordings, {len(sentences)} sentences")
    return Split(sentences, recordings)


def join(lang: str, split: str, en: Split, tgt: Split) -> list[SentenceRecord]:
    source = f"{REPO_ID}@{REVISION} {SRC_CONFIG}+{TGT_CONFIGS[lang]} {SPLITS[split]}"
    lines = []
    for sid in sorted(en.sentences.keys() & tgt.sentences.keys()):
        s, t = en.sentences[sid], tgt.sentences[sid]
        lines.append(
            SentenceRecord(
                id=str(sid),
                src_lang=SRC_LANG,
                tgt_lang=lang,
                src_text=s.text,
                ref_text=t.text,
                slot_s=round(s.trimmed_s, 3),
                ref_tgt_s=round(t.trimmed_s, 3),
                noisy_src=s.noisy,
                noisy_tgt=t.noisy,
                src_recording_id=s.recording_id,
                tgt_recording_id=t.recording_id,
                license=LICENSE,
                source=source,
            )
        )
    return lines


def overlong(lines: list[SentenceRecord]) -> list[OverlongRecord]:
    return [
        OverlongRecord(**asdict(r), overrun=round(r.ref_tgt_s / r.slot_s, 4))
        for r in lines
        if r.ref_tgt_s > OVERLONG * r.slot_s
    ]


def read_tsv(config: str, raw_split: str) -> set[tuple[int, str]]:
    """(sentence id, recording id) pairs listed in the raw release's TSV."""
    with open(fetch(f"data/{config}/{raw_split}.tsv"), encoding="utf-8") as f:
        cols = (line.rstrip("\n").split("\t") for line in f if line.strip())
        return {(int(c[0]), recording_id(c[1])) for c in cols}


def digit_runs(text: str) -> list[str]:
    return sorted(re.findall(r"\d+", text))


def pct(k: int, n: int) -> str:
    return f"{100 * k / n:.1f} %" if n else "–"


def stats_report(
    started: datetime,
    commit: str,
    src: dict[str, Split],
    tgt: dict[tuple[str, str], Split],
    lines: dict[tuple[str, str], list[SentenceRecord]],
    tsv_mismatches: list[str],
    split_overlaps: list[str],
) -> str:
    top_db = TRIM["top_db"]
    n_total = sum(len(v) for v in lines.values())
    n_split = {s: sum(len(v) for (_, sp), v in lines.items() if sp == s) for s in SPLITS}
    libs = ", ".join(f"{p} {version(p)}" for p in ("librosa", "numpy", "soundfile", "pyarrow", "huggingface_hub"))
    out = [
        "# FLEURS line statistics",
        "",
        "> **Warning.** The audio-based numbers in this file (`slot_s`, `ref_tgt_s`, their ratios and",
        "> the over-long counts) are not valid until trimming is fixed. With `top_db=30`, trimming leaves",
        f"> noise in place on recordings whose noise floor is above −{top_db} dB (flagged `noisy_src` /",
        "> `noisy_tgt`; see the end of this file). The fix, VAD trimming, is planned for the isochrony",
        "> step. The `ref_tgt_s / slot_s` ratios also mix two different speakers' tempos. The main",
        "> experiments (steps 1–4 in `docs/eval_protocol.md`) use none of these numbers.",
        "",
        f"- Date: {started:%Y-%m-%d %H:%M} UTC",
        f"- Git commit: {commit}",
        "- Built by: `uv run python -m isochron.data.build_fleurs` (in `track_2b/`)",
        f"- Data: [{REPO_ID}](https://huggingface.co/datasets/{REPO_ID}) at revision `{REVISION}`; "
        f"configs {SRC_CONFIG}, {', '.join(TGT_CONFIGS.values())}; "
        "FLEURS splits `validation` (our `dev`) and `test`",
        "- Licence: FLEURS is CC BY 4.0; its text comes from FLoRes-101 (CC BY-SA 4.0), "
        "so our data files are CC BY-SA 4.0",
        f"- Trimming: `{TRIM_DESC}` at the native {SAMPLE_RATE} Hz, no resampling; durations rounded to 1 ms",
        f"- Noisy flag: noise floor above −{top_db} dB, where noise floor = 5th percentile of frame RMS "
        f"(frame {TRIM['frame_length']}, hop {TRIM['hop_length']}, the frames trim uses) in dB relative to the loudest frame",
        "- Recording choice: per sentence and language, the recording with the smallest numeric recording id",
        f"- Over-long: `ref_tgt_s > {OVERLONG:.2f} × slot_s`, on the rounded durations",
        "- Model + quantisation, endpoint, TTS engine + voice: none. No model or TTS is involved; "
        "every duration here is measured on a human FLEURS recording",
        f"- Seeds: {SAMPLE_SEED} (only used to pick the sample pairs printed to the console)",
        f"- n: {n_total} joined lines (dev {n_split['dev']}, test {n_split['test']})",
        f"- Libraries: {libs}",
        "",
        "## Lines per split and language",
        "",
        "| Pair | Split | EN sentences (recordings) | Target sentences (recordings) | Joined lines | EN only | Target only |",
        "|------|-------|--------------------------:|------------------------------:|-------------:|--------:|------------:|",
    ]
    for (lang, split), t in tgt.items():
        en_ids, t_ids = src[split].sentences.keys(), t.sentences.keys()
        out.append(
            f"| en→{lang} | {split} | {len(en_ids)} ({len(src[split].recordings)}) "
            f"| {len(t_ids)} ({len(t.recordings)}) | {len(lines[lang, split])} "
            f"| {len(en_ids - t_ids)} | {len(t_ids - en_ids)} |"
        )

    out += ["", "## Checks", ""]
    out.append(
        "- Parquet vs raw release: "
        + ("every parquet split lists the same (sentence id, recording id) pairs as the matching raw TSV."
           if not tsv_mismatches else "MISMATCH: " + "; ".join(tsv_mismatches))
    )
    out.append(
        "- Split separation: "
        + ("no sentence id occurs in two different splits (train, dev, test), within or across "
           f"{SRC_CONFIG}, {', '.join(TGT_CONFIGS.values())}."
           if not split_overlaps else "OVERLAP: " + "; ".join(split_overlaps))
    )
    out.append("- Texts: every recording of a sentence has the same `raw_transcription` (the build stops otherwise).")
    out += [
        "- Alignment: lines where EN or target text contains digits, and how many have identical digit runs.",
        "  Numbers spelled out in one language and not the other cause some mismatches even when the alignment is right.",
        "",
        "| Pair | Lines with digits | Identical digit runs | Share |",
        "|------|------------------:|---------------------:|------:|",
    ]
    for lang in TGT_CONFIGS:
        both = [r for s in SPLITS for r in lines[lang, s]]
        with_digits = [r for r in both if digit_runs(r.src_text) or digit_runs(r.ref_text)]
        same = sum(digit_runs(r.src_text) == digit_runs(r.ref_text) for r in with_digits)
        out.append(f"| en→{lang} | {len(with_digits)} | {same} | {pct(same, len(with_digits))} |")

    out += [
        "",
        "## Slot duration `slot_s` (s)",
        "",
        "| Pair | Split | n | mean | min | p10 | p25 | median | p75 | p90 | max |",
        "|------|-------|--:|-----:|----:|----:|----:|-------:|----:|----:|----:|",
    ]
    for (lang, split), rows in lines.items():
        v = np.array([r.slot_s for r in rows])
        q = np.percentile(v, [10, 25, 50, 75, 90])
        out.append(
            f"| en→{lang} | {split} | {len(v)} | {v.mean():.2f} | {v.min():.2f} | "
            + " | ".join(f"{x:.2f}" for x in q)
            + f" | {v.max():.2f} |"
        )

    out += [
        "",
        "## Reference length relative to the slot, `ref_tgt_s / slot_s`",
        "",
        "| Pair | Split | n | p25 | median | p75 |",
        "|------|-------|--:|----:|-------:|----:|",
    ]
    for lang in TGT_CONFIGS:
        for split in (*SPLITS, "dev+test"):
            rows = lines[lang, split] if split in SPLITS else [r for s in SPLITS for r in lines[lang, s]]
            q = np.percentile([r.ref_tgt_s / r.slot_s for r in rows], [25, 50, 75])
            out.append(f"| en→{lang} | {split} | {len(rows)} | {q[0]:.3f} | **{q[1]:.3f}** | {q[2]:.3f} |")

    out += [
        "",
        f"## Over-long lines, `ref_tgt_s > {OVERLONG:.2f} × slot_s`",
        "",
        "The last column counts over-long lines flagged `noisy_src` or `noisy_tgt`.",
        "",
        "| Pair | Split | Lines | Over-long | Share | Over-long with a noisy recording |",
        "|------|-------|------:|----------:|------:|---------------------------------:|",
    ]
    for (lang, split), rows in lines.items():
        ol = overlong(rows)
        noisy = sum(r.noisy_src or r.noisy_tgt for r in ol)
        out.append(
            f"| en→{lang} | {split} | {len(rows)} | {len(ol)} | {pct(len(ol), len(rows))} | {noisy} |"
        )

    out += [
        "",
        "## Trimming, chosen recordings",
        "",
        f"| Language | Split | Recordings | Median raw (s) | Median trimmed (s) | Median removed (s) | Noise floor above −{top_db} dB |",
        "|----------|-------|-----------:|---------------:|-------------------:|-------------------:|-------------------------:|",
    ]
    by_lang = {(SRC_LANG, s): src[s] for s in SPLITS} | tgt
    for (lang, split), sp in by_lang.items():
        raw = np.array([s.raw_s for s in sp.sentences.values()])
        trimmed = np.array([s.trimmed_s for s in sp.sentences.values()])
        noisy = sum(s.noisy for s in sp.sentences.values())
        out.append(
            f"| {lang} | {split} | {len(raw)} | {np.median(raw):.2f} | {np.median(trimmed):.2f} "
            f"| {np.median(raw - trimmed):.2f} | {noisy} ({pct(noisy, len(raw))}) |"
        )

    out += [
        "",
        f"### Known issue: noise floors above −{top_db} dB",
        "",
        f"`top_db={top_db}` only removes frames more than {top_db} dB below the loudest frame. When a",
        "recording's background noise is louder than that, trim leaves the leading and trailing",
        "non-speech in place, and its duration comes out too long. Characters per second (text",
        "length incl. spaces ÷ trimmed duration) is a rough tempo check; it also varies by speaker",
        "and language. VAD trimming is planned for the isochrony step in `docs/eval_protocol.md`.",
        "",
        "| Language | Noise floor | Recordings | Median removed (s) | Nothing removed | Median chars/s |",
        "|----------|-------------|-----------:|-------------------:|----------------:|---------------:|",
    ]
    for lang in (SRC_LANG, *TGT_CONFIGS):
        recs = [s for (code, _), sp in by_lang.items() if code == lang for s in sp.sentences.values()]
        for name, group in (
            (f"≤ −{top_db} dB", [s for s in recs if not s.noisy]),
            (f"> −{top_db} dB (noisy)", [s for s in recs if s.noisy]),
        ):
            if not group:
                continue
            removed = np.array([s.raw_s - s.trimmed_s for s in group])
            cps = np.median([len(s.text) / s.trimmed_s for s in group])
            none = int(np.sum(removed < 0.001))
            out.append(
                f"| {lang} | {name} | {len(group)} | {np.median(removed):.2f} "
                f"| {none} ({pct(none, len(group))}) | {cps:.1f} |"
            )

    out += [
        "",
        "Noisy flags per data file:",
        "",
        "| Pair | Split | Lines | `noisy_src` | `noisy_tgt` | Either |",
        "|------|-------|------:|------------:|------------:|-------:|",
    ]
    for (lang, split), rows in lines.items():
        n_src = sum(r.noisy_src for r in rows)
        n_tgt = sum(r.noisy_tgt for r in rows)
        either = sum(r.noisy_src or r.noisy_tgt for r in rows)
        out.append(f"| en→{lang} | {split} | {len(rows)} | {n_src} | {n_tgt} | {either} |")
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Build FLEURS EN→DE/FR/IT line files.")
    ap.add_argument("--data-dir", type=Path, default=Path("data"))
    ap.add_argument("--results-dir", type=Path, default=Path("results"))
    args = ap.parse_args(argv)

    started = datetime.now(timezone.utc)
    commit = git_commit()

    src = {split: load_split(SRC_CONFIG, split) for split in SPLITS}
    tgt = {(lang, split): load_split(cfg, split) for lang, cfg in TGT_CONFIGS.items() for split in SPLITS}

    configs = {SRC_CONFIG: src} | {cfg: {s: tgt[lang, s] for s in SPLITS} for lang, cfg in TGT_CONFIGS.items()}
    tsv = {(cfg, s): read_tsv(cfg, s) for cfg in configs for s in RAW_SPLITS}
    tsv_mismatches = [
        f"{cfg} {split}: {len(sp.recordings ^ tsv[cfg, split])} pairs differ"
        for cfg, splits in configs.items()
        for split, sp in splits.items()
        if sp.recordings != tsv[cfg, split]
    ]
    ids = {key: {sid for sid, _ in pairs} for key, pairs in tsv.items()}
    split_overlaps = [
        f"{c1} {s1} ∩ {c2} {s2}: {n} ids"
        for (c1, s1), a in ids.items()
        for (c2, s2), b in ids.items()
        if s1 < s2 and (n := len(a & b))
    ]

    args.data_dir.mkdir(parents=True, exist_ok=True)
    args.results_dir.mkdir(parents=True, exist_ok=True)
    lines: dict[tuple[str, str], list[SentenceRecord]] = {}
    for (lang, split), t in tgt.items():
        lines[lang, split] = join(lang, split, src[split], t)
        write_jsonl(args.data_dir / f"fleurs_{lang}_{split}.jsonl", lines[lang, split])
        write_jsonl(args.data_dir / f"overlong_{lang}_{split}.jsonl", overlong(lines[lang, split]))

    stats = args.results_dir / "fleurs_stats.md"
    stats.write_text(
        stats_report(started, commit, src, tgt, lines, tsv_mismatches, split_overlaps), encoding="utf-8"
    )

    rng = random.Random(SAMPLE_SEED)
    for lang in TGT_CONFIGS:
        pool = [(s, r) for s in SPLITS for r in lines[lang, s]]
        print(f"\n=== {N_SAMPLES} random joined pairs, en→{lang} (seed {SAMPLE_SEED})")
        for split, r in rng.sample(pool, N_SAMPLES):
            print(f"\n[{split} id {r.id}] slot_s {r.slot_s}  ref_tgt_s {r.ref_tgt_s}")
            print(f"  EN: {r.src_text}")
            print(f"  {lang.upper()}: {r.ref_text}")

    print()
    for (lang, split), rows in lines.items():
        print(
            f"en→{lang} {split}: {len(rows)} lines, {len(overlong(rows))} over-long, "
            f"noisy_src {sum(r.noisy_src for r in rows)}, noisy_tgt {sum(r.noisy_tgt for r in rows)}"
        )
    if tsv_mismatches or split_overlaps:
        print("CHECKS FAILED:", *tsv_mismatches, *split_overlaps, sep="\n  ")
    print(f"\nwrote {args.data_dir.resolve()}/fleurs_*.jsonl, overlong_*.jsonl and {stats.resolve()}")


if __name__ == "__main__":
    main()
