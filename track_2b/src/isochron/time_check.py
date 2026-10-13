"""The time check and the demo lines: German speech against the English speaker's slot, in seconds.

Exploratory, post-hoc, added after test outputs existed (docs/eval_protocol.md, v2.24). Step 4 measured
fit in syllables or characters; here the outputs are spoken by a TTS voice and timed.

- Lines. The time check uses the 25 English sources of the native-speaker sheet (step 4 test, German,
  syllable budget, generation seed 0), each with its plain translation (a) and ours (c), skipping a source
  whose English recording is flagged noisy (noisy_src in data/fleurs_de_test.jsonl). The demo uses
  DEMO_FIT lines where (a) misses the syllable budget and (c) fits with its meaning kept against the
  reference by both NLI models, and DEMO_MISS lines where the repair loop ran but could not fit, drawn
  with random.Random(SEED).sample from the eligible ids in numeric order, among the test sources that are
  not on the sheet (the sheet must stay blind) and whose English recording is not noisy.
- Speech. hpc/tts.sbatch reads every distinct text 3 times (seeds 0, 1, 2) with Chatterbox multilingual
  and its default voice. A text's duration is the median of its takes.
- Timing. The English recording (FLEURS, the one data/fleurs_de_test.jsonl names) and the speech are
  trimmed the same way: resampled to 16 kHz, then build_fleurs.TRIM (librosa.effects.trim, top_db 30). A
  line fits when its speech is within ±10 % of the English slot.

    uv run python -m isochron.time_check plan              # results/time_check/plan.jsonl, selection.json
    uv run python -m isochron.time_check english           # the English recordings into audio/ (git-ignored)
    uv run --group figures python -m isochron.time_check report   # after the TTS job: results/time_check.md
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import random
import statistics
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from isochron.provenance import git_commit

SEED = 0
DEMO_FIT, DEMO_MISS = 3, 1
TOLERANCE = 0.10
GEN_SEED = 0  # the step 4 generation seed of every line here
TAKES = 3
SR = 16_000
OUT = Path("results/time_check")
AUDIO = Path("audio")  # git-ignored
RAW = Path("results/raw/time_check")
FLEURS = Path("data/fleurs_de_test.jsonl")
KEY = Path("results/native_check/step4_key_de.csv")
SHEET = Path("results/native_check/step4_sheet_de.csv")
LENGTHS = Path("results/step4_test_lengths.csv")
RUN = Path("results/raw/hpc_8b_step4_test")
NLI = Path("results/raw/step4_test_nli_cache.jsonl")
NLI2 = Path("results/raw/meaning_check/step4_cache.jsonl")
TTS_ENGINE = "Chatterbox multilingual (chatterbox-tts 0.1.7, MIT; weights ResembleAI/chatterbox @ 5bb1f6e, MIT)"
TTS_VOICE = "the model's built-in default voice (conds.pt); no reference audio, no cloning"
FLEURS_LICENCE = "CC BY 4.0"
TTS_LICENCE = "synthetic speech (Chatterbox, MIT); text CC BY-SA 4.0 (Apertus output from FLoRes-101)"


def text_id(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def demo_choice(rows: list[dict[str, Any]], exclude: set[str], seed: int = SEED,
                n_fit: int = DEMO_FIT, n_miss: int = DEMO_MISS) -> tuple[list[str], list[str], dict[str, int]]:
    """The demo ids: (a) misses and (c) fits with meaning kept by both NLIs; and the loop ran but missed.

    rows: one per source, with id, noisy, a_usable, a_fit, c_usable, c_fit, c_kept_plain, c_kept_main,
    c_kept_second. Sources in `exclude` (the sheet's) and with a noisy English recording never count."""
    pool = sorted((r for r in rows if r["id"] not in exclude and not r["noisy"]), key=lambda r: int(r["id"]))
    fits = [r["id"] for r in pool if r["a_usable"] and not r["a_fit"] and r["c_usable"] and r["c_fit"]
            and r["c_kept_main"] and r["c_kept_second"]]
    misses = [r["id"] for r in pool if r["a_usable"] and r["c_usable"] and not r["c_kept_plain"] and not r["c_fit"]]
    if len(fits) < n_fit or len(misses) < n_miss:
        raise SystemExit(f"too few eligible demo lines: {len(fits)} fit, {len(misses)} missed")
    return (random.Random(seed).sample(fits, n_fit), random.Random(seed).sample(misses, n_miss),
            {"pool": len(pool), "eligible_fit": len(fits), "eligible_miss": len(misses)})


@dataclass(frozen=True)
class Timing:
    raw_s: float
    trimmed_s: float
    floor_db: float
    peak: float
    clipped: float
    """share of samples at full scale (|x| ≥ 0.999)"""


def measure(y: np.ndarray, sr: int) -> Timing:
    """Trim leading and trailing silence exactly as build_fleurs does for the English slots: at 16 kHz,
    with build_fleurs.TRIM; the noise floor as there."""
    import librosa

    from isochron.data.build_fleurs import TRIM

    y = np.asarray(y, dtype=np.float32)
    if y.ndim > 1:
        y = y.mean(axis=1)
    if not len(y):
        raise ValueError("empty audio")
    peak = float(np.max(np.abs(y)))
    clipped = float(np.mean(np.abs(y) >= 0.999))
    y16 = y if sr == SR else librosa.resample(y, orig_sr=sr, target_sr=SR).astype(np.float32)
    _, (start, end) = librosa.effects.trim(y16, **TRIM)
    if end <= start or peak == 0:
        raise ValueError("silent audio")
    rms = librosa.feature.rms(y=y16, frame_length=TRIM["frame_length"], hop_length=TRIM["hop_length"])[0]
    floor = float(np.percentile(librosa.amplitude_to_db(rms, ref=np.max, top_db=None), 5))
    return Timing(len(y) / sr, (end - start) / SR, floor, peak, clipped)


def fits(seconds: float, slot: float, tolerance: float = TOLERANCE) -> bool:
    """Within ±10 % of the slot (the same rule as length.hit, in seconds)."""
    return abs(seconds - slot) <= tolerance * slot + 1e-9


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar p for b and c discordant pairs."""
    n = b + c
    if not n:
        return 1.0
    tail = sum(math.comb(n, k) for k in range(min(b, c) + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def fit_line(x: list[float], y: list[float]) -> dict[str, float]:
    """Pearson r, least-squares slope and intercept of y on x, and y per x overall (sum y / sum x)."""
    a, b = np.asarray(x, float), np.asarray(y, float)
    slope, intercept = np.polyfit(a, b, 1)
    return {"r": float(np.corrcoef(a, b)[0, 1]), "slope": float(slope), "intercept": float(intercept),
            "per_unit": float(b.sum() / a.sum()), "n": len(a)}


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(line for line in f if not line.startswith("#")))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def plan() -> None:
    from isochron.meaning_check import key, read_cache

    commit = git_commit()
    fleurs = {r["id"]: r for r in map(json.loads, FLEURS.read_text(encoding="utf-8").splitlines())}
    lines = {r["line"]: r for r in read_csv_rows(SHEET)}
    sheet = [{**k, "text": lines[k["line"]]["german_output"]} for k in read_csv_rows(KEY)]
    sheet_ids = {k["id"] for k in sheet}
    items = {it["id"]: it for it in map(json.loads, (RUN / "items.jsonl").read_text(encoding="utf-8").splitlines())
             if it and it["seed"] == GEN_SEED}
    lengths = {(r["id"], r["system"]): r for r in read_csv_rows(LENGTHS)
               if r["lang"] == "de" and r["budget"] == "isosyllabic" and r["seed"] == str(GEN_SEED)}
    nli, nli2 = read_cache(NLI)[1], read_cache(NLI2)[1]
    rows = []
    for sid, it in items.items():
        a, c = lengths[(sid, "a")], lengths[(sid, "c")]
        ctext = it["budgets"]["isosyllabic"]["c"]["text"]
        usable = {s: r["no_output"] == "0" and r["wrong_language"] == "0" for s, r in (("a", a), ("c", c))}
        kept = (nli.get(key(it["reference"], ctext), {}).get("kept", False) if usable["c"] else False,
                nli2.get(key(it["reference"], ctext), {}).get("kept", False) if usable["c"] else False)
        rows.append({"id": sid, "noisy": fleurs[sid]["noisy_src"], "a_usable": usable["a"], "a_fit": a["fit"] == "1",
                     "c_usable": usable["c"], "c_fit": c["fit"] == "1",
                     "c_kept_plain": it["budgets"]["isosyllabic"]["c"]["kept_plain"], "c_kept_main": kept[0],
                     "c_kept_second": kept[1]})
    fit_ids, miss_ids, counts = demo_choice(rows, sheet_ids)
    uses: dict[str, dict[str, Any]] = {}

    def use(text: str, sid: str, system: str, purpose: str) -> None:
        entry = uses.setdefault(text_id(text), {"text_id": text_id(text), "text": text, "uses": []})
        entry["uses"].append({"id": sid, "system": system, "purpose": purpose})

    timed = [k for k in sheet if not fleurs[k["id"]]["noisy_src"]]
    for k in sorted(timed, key=lambda k: (int(k["id"]), k["system"])):
        use(k["text"], k["id"], k["system"], "time_check")
    for sid in fit_ids + miss_ids:
        use(items[sid]["a"]["text"], sid, "a", "demo")
        use(items[sid]["budgets"]["isosyllabic"]["c"]["text"], sid, "c", "demo")
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "plan.jsonl", "w", encoding="utf-8") as f:
        for entry in uses.values():
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    selection = {
        "written": f"{datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC", "commit": commit, "seed": SEED,
        "run": RUN.name, "generation_seed": GEN_SEED, "budget": "isosyllabic",
        "sheet_sources": len(sheet_ids),
        "sheet_noisy": sorted({k["id"] for k in sheet if fleurs[k["id"]]["noisy_src"]}, key=int),
        "timed_sources": sorted({k["id"] for k in timed}, key=int),
        "demo_fit": fit_ids, "demo_miss": miss_ids, **counts,
        "rule": (f"pool: step 4 test sources (German, syllable budget, seed {GEN_SEED}) not on the native-speaker "
                 "sheet, English recording not noisy, both outputs usable; fit: (a) misses, (c) fits, (c) kept vs "
                 "the reference by both NLI models; miss: (c) not kept plain (the loop ran) and misses; each drawn "
                 f"with random.Random({SEED}).sample from the eligible ids in numeric order"),
        "texts": len(uses)}
    (OUT / "selection.json").write_text(json.dumps(selection, indent=1) + "\n", encoding="utf-8")
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / "plan.jsonl").write_bytes((OUT / "plan.jsonl").read_bytes())
    print(f"{len(timed) // 2} of {len(sheet_ids)} sheet sources timed ({len(selection['sheet_noisy'])} noisy); demo "
          f"fit {fit_ids} of {counts['eligible_fit']}, miss {miss_ids} of {counts['eligible_miss']}; {len(uses)} texts")


def english() -> None:
    """The English recordings of the timed and demo sources, as FLEURS has them, into audio/english/."""
    import pyarrow.parquet as pq

    from isochron.data.build_fleurs import SPLITS, recording_id
    from isochron.data.fleurs import fetch

    selection = json.loads((OUT / "selection.json").read_text(encoding="utf-8"))
    fleurs = {r["id"]: r for r in map(json.loads, FLEURS.read_text(encoding="utf-8").splitlines())}
    wanted = {fleurs[sid]["src_recording_id"]: sid
              for sid in selection["timed_sources"] + selection["demo_fit"] + selection["demo_miss"]}
    pf = pq.ParquetFile(fetch(f"parquet-data/en_us/{SPLITS['test']}-00000-of-00001.parquet"))
    (AUDIO / "english").mkdir(parents=True, exist_ok=True)
    found = 0
    for batch in pf.iter_batches(batch_size=64, columns=["audio"]):
        audio = batch.column(0)
        for k, path in enumerate(audio.field("path").to_pylist()):
            if (rid := recording_id(path)) in wanted:
                (AUDIO / "english" / f"{wanted[rid]}.wav").write_bytes(audio.field("bytes")[k].as_py())
                found += 1
    if found != len(wanted):
        raise SystemExit(f"found {found} of {len(wanted)} English recordings")
    print(f"wrote {found} English recordings to {AUDIO / 'english'}")


def load(path: Path) -> tuple[np.ndarray, int]:
    import soundfile as sf

    y, sr = sf.read(io.BytesIO(path.read_bytes()), dtype="float32")
    return y, sr


def report() -> None:
    from isochron.metrics.length import counter_description, length

    commit = git_commit()
    selection = json.loads((OUT / "selection.json").read_text(encoding="utf-8"))
    texts = [json.loads(line) for line in (OUT / "plan.jsonl").read_text(encoding="utf-8").splitlines()]
    fleurs = {r["id"]: r for r in map(json.loads, FLEURS.read_text(encoding="utf-8").splitlines())}
    settings = json.loads((AUDIO / "tts" / "settings.json").read_text(encoding="utf-8"))
    log = {(e["text_id"], e["take"]): e for e in map(json.loads, (AUDIO / "tts" / "log.jsonl").read_text().splitlines())}
    manifest, problems = [], []

    def record(path: Path, kind: str, timing: Timing, **extra: Any) -> None:
        manifest.append({"file": path.as_posix(), "kind": kind, **extra, "raw_s": f"{timing.raw_s:.3f}",
                         "trimmed_s": f"{timing.trimmed_s:.3f}", "peak": f"{timing.peak:.4f}",
                         "clipped_share": f"{timing.clipped:.5f}", "sha256": sha256(path),
                         "licence": FLEURS_LICENCE if kind == "english" else TTS_LICENCE})

    slots: dict[str, float] = {}
    for sid in selection["timed_sources"] + selection["demo_fit"] + selection["demo_miss"]:
        path = AUDIO / "english" / f"{sid}.wav"
        t = measure(*load(path))
        slots[sid] = t.trimmed_s
        if abs(t.trimmed_s - fleurs[sid]["slot_s"]) > 0.0015:
            problems.append(f"English {sid}: trimmed {t.trimmed_s:.3f} s, but data says slot_s {fleurs[sid]['slot_s']}")
        record(path, "english", t, id=sid, system="", text_id="", take="", seed="",
               recording=fleurs[sid]["src_recording_id"])
    seconds: dict[str, float] = {}
    takes: dict[str, list[float]] = {}
    for entry in texts:
        tid = entry["text_id"]
        for k in range(TAKES):
            path = AUDIO / "tts" / f"{tid}_take{k}.wav"
            if not path.is_file():
                raise SystemExit(f"missing {path}: did the TTS job finish? ({settings.get('stopped')})")
            t = measure(*load(path))
            takes.setdefault(tid, []).append(t.trimmed_s)
            if t.clipped > 0.001 or log[(tid, k)]["peak"] >= 1.0:
                problems.append(f"{path.name}: clipped (peak {log[(tid, k)]['peak']}, {t.clipped:.2%} at full scale)")
            record(path, "tts", t, id=" ".join(sorted({u["id"] for u in entry["uses"]})),
                   system=" ".join(sorted({u["system"] for u in entry["uses"]})), text_id=tid, take=k,
                   seed=log[(tid, k)]["seed"], recording="")
        seconds[tid] = statistics.median(takes[tid])
    syll = {e["text_id"]: length(e["text"], "syllables", "de") for e in texts}
    per_syll = {tid: seconds[tid] / syll[tid] for tid in seconds}
    for tid, v in per_syll.items():
        if not 0.10 <= v <= 0.40:
            problems.append(f"{tid}: {v:.3f} s per syllable, outside 0.10–0.40")

    by = {(u["id"], u["system"]): e["text_id"] for e in texts for u in e["uses"]}
    timed = selection["timed_sources"]
    table = []
    for sid in timed:
        a, c = seconds[by[(sid, "a")]], seconds[by[(sid, "c")]]
        table.append({"id": sid, "slot": slots[sid], "a": a, "c": c, "a_fit": fits(a, slots[sid]), "c_fit": fits(c, slots[sid]),
                      "same_text": by[(sid, "a")] == by[(sid, "c")]})
    n = len(table)
    a_fit, c_fit = sum(r["a_fit"] for r in table), sum(r["c_fit"] for r in table)
    only_c = sum(r["c_fit"] and not r["a_fit"] for r in table)
    only_a = sum(r["a_fit"] and not r["c_fit"] for r in table)
    ratio = {s: [r[s] / r["slot"] for r in table] for s in "ac"}
    timed_tids = sorted({by[(sid, s)] for sid in timed for s in "ac"})
    line = fit_line([syll[t] for t in timed_tids], [seconds[t] for t in timed_tids])
    english_line = fit_line([length(fleurs[sid]["src_text"], "syllables", "en") for sid in timed], [slots[sid] for sid in timed])
    spread = [(max(takes[t]) - min(takes[t])) / seconds[t] for t in timed_tids]
    manifest_path = OUT / "manifest.csv"
    with open(manifest_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(manifest[0]))
        w.writeheader()
        w.writerows(manifest)
    durations = OUT / "durations.csv"
    with open(durations, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "system", "purpose", "text_id", "syllables", "take_s", "median_s", "english_slot_s", "ratio",
                    "fits_slot"])
        for e in texts:
            for u in e["uses"]:
                tid, sid = e["text_id"], u["id"]
                w.writerow([sid, u["system"], u["purpose"], tid, syll[tid], " ".join(f"{x:.3f}" for x in takes[tid]),
                            f"{seconds[tid]:.3f}", f"{slots[sid]:.3f}", f"{seconds[tid] / slots[sid]:.3f}",
                            int(fits(seconds[tid], slots[sid]))])
    figures = demo(selection, texts, by, seconds, takes, slots, fleurs)
    pct = lambda k: f"{k}/{n} ({100 * k / n:.0f} %)"  # noqa: E731
    md = [
        "# Time check: German speech against the English slot (exploratory, post-hoc)", "",
        "Post-hoc, added after test outputs existed (protocol v2.24). Exploratory: no threshold was fixed in advance.", "",
        f"- Date: {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC; git commit {commit}",
        f"- Texts: step 4 test, run `{selection['run']}` (Apertus 1.5 8B, BF16; vLLM on the cluster, its endpoint in "
        f"`results/step4_test.md`), German, syllable budget, generation seed {GEN_SEED}",
        f"- TTS engine: {TTS_ENGINE}; voice: {TTS_VOICE}",
        f"- TTS settings: {', '.join(f'{k}={v}' for k, v in settings_view(settings).items())}; "
        f"{settings['gpu']}, one job, {settings['wall_s']:.0f} s wall time; endpoint: none (local inference)",
        f"- TTS seeds: {settings['seeds']} (take k uses seed k); {TAKES} takes per text, duration = the median take",
        f"- English slot: the FLEURS recording named in `data/fleurs_de_test.jsonl` (google/fleurs, CC BY 4.0), "
        "trimmed like the speech: 16 kHz, `librosa.effects.trim(top_db=30, frame 2048, hop 512)`; sources whose "
        "English recording is flagged noisy are skipped",
        f"- Fit: speech within ±{TOLERANCE:.0%} of the English slot. Syllables: {counter_description('espeak')}",
        f"- n: {n} of the sheet's {selection['sheet_sources']} sources ({len(selection['sheet_noisy'])} skipped as noisy: "
        f"{', '.join(selection['sheet_noisy'])}); {len(texts)} distinct texts × {TAKES} takes", "",
        "## Fit in seconds", "",
        "| System | Fits the English slot | Median speech ÷ slot | Range |", "|---|---|---:|---|",
        f"| (a) plain translation | {pct(a_fit)} | {statistics.median(ratio['a']):.2f} | {min(ratio['a']):.2f}–{max(ratio['a']):.2f} |",
        f"| (c) ours | {pct(c_fit)} | {statistics.median(ratio['c']):.2f} | {min(ratio['c']):.2f}–{max(ratio['c']):.2f} |", "",
        f"Paired, per source: (c) fits and (a) does not in {only_c}, the reverse in {only_a}; exact McNemar "
        f"p = {mcnemar_exact(only_c, only_a):.3f}. In {sum(r['same_text'] for r in table)} sources (c) kept (a)'s text, "
        "so both read the same audio. Absolute shares depend on the voice's speaking rate; the comparison of (a) "
        "with (c) is what counts.", "",
        "## Do syllables predict seconds?", "",
        f"- German speech, {line['n']} distinct texts: r = {line['r']:.2f}; {line['per_unit']:.3f} s per syllable overall; "
        f"least squares: {line['slope']:.3f} s per syllable + {line['intercept']:.2f} s.",
        f"- English FLEURS speakers, {english_line['n']} recordings: r = {english_line['r']:.2f}; "
        f"{english_line['per_unit']:.3f} s per syllable.",
        f"- Takes of the same text differ by a median of {100 * statistics.median(spread):.0f} % of its duration "
        f"(max − min over {TAKES} takes; largest {100 * max(spread):.0f} %).", "",
        "## Per source", "",
        "| Source | English slot (s) | (a) s | (c) s | (a) fits | (c) fits |", "|---|---:|---:|---:|---|---|",
        *(f"| {r['id']} | {r['slot']:.2f} | {r['a']:.2f} | {r['c']:.2f} | {'yes' if r['a_fit'] else 'no'} | "
          f"{'yes' if r['c_fit'] else 'no'} |" for r in table), "",
        "## Demo lines", "",
        f"Drawn by the rule in `results/time_check/selection.json`: {selection['rule']}. Eligible: "
        f"{selection['eligible_fit']} fit, {selection['eligible_miss']} miss, of {selection['pool']} sources.", "",
        "| Source | Kind | English slot (s) | (a) s | (c) s | Figure |", "|---|---|---:|---:|---:|---|",
        *(f"| {sid} | {kind} | {slots[sid]:.2f} | {seconds[by[(sid, 'a')]]:.2f} | {seconds[by[(sid, 'c')]]:.2f} | "
          f"`{figures[sid]}` |" for kind, ids in (("fit", selection["demo_fit"]), ("loop missed", selection["demo_miss"]))
          for sid in ids), "",
        "## Checks", "",
        f"- Files: {len(manifest)} (`{manifest_path}`, with SHA-256 and licence; the audio stays in `audio/`, "
        "git-ignored). None empty or silent (the trim would fail).",
        f"- Peak of the speech before 16-bit writing: max {max(e['peak'] for e in log.values()):.3f}; "
        f"seconds per syllable per text: {min(per_syll.values()):.3f}–{max(per_syll.values()):.3f}.",
        f"- Problems: {'; '.join(problems) if problems else 'none'}", ""]
    (Path("results") / "time_check.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))


def settings_view(settings: dict[str, Any]) -> dict[str, Any]:
    keys = ("language_id", "exaggeration", "cfg_weight", "temperature", "repetition_penalty", "min_p", "top_p",
            "sample_rate")
    return {k: settings[k] for k in keys} | {"versions": ", ".join(f"{p} {v}" for p, v in settings["versions"].items())}


def demo(selection: dict[str, Any], texts: list[dict[str, Any]], by: dict[tuple[str, str], str],
         seconds: dict[str, float], takes: dict[str, list[float]], slots: dict[str, float],
         fleurs: dict[str, dict[str, Any]]) -> dict[str, str]:
    """For each demo line: the English recording and the median take of (a) and (c), trimmed, in
    audio/demo/<id>/, and a timeline figure in docs/figures/demo/."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import soundfile as sf

    from isochron.figures import PLAIN, WIDTH, WITH as LOOP

    out = Path("docs/figures/demo")
    out.mkdir(parents=True, exist_ok=True)
    text_of = {e["text_id"]: e["text"] for e in texts}
    made = {}
    for sid in selection["demo_fit"] + selection["demo_miss"]:
        folder = AUDIO / "demo" / sid
        folder.mkdir(parents=True, exist_ok=True)
        for name, path in (("english", AUDIO / "english" / f"{sid}.wav"),
                           *((name, AUDIO / "tts" / f"{by[(sid, s)]}_take{median_take(takes[by[(sid, s)]])}.wav")
                             for name, s in (("plain", "a"), ("ours", "c")))):
            y, sr = load(path)
            import librosa

            from isochron.data.build_fleurs import TRIM

            y16 = y if sr == SR else librosa.resample(y, orig_sr=sr, target_sr=SR)
            _, (start, end) = librosa.effects.trim(y16, **TRIM)
            sf.write(folder / f"{name}.wav", y[int(start * sr / SR):int(end * sr / SR)], sr)
        slot = slots[sid]
        bars = [("English\n(FLEURS speaker)", slot, "#000000"), ("plain\ntranslation", seconds[by[(sid, "a")]], PLAIN),
                ("ours", seconds[by[(sid, "c")]], LOOP)]
        fig, ax = plt.subplots(figsize=(WIDTH, 1.6))
        ax.axvspan(0.9 * slot, 1.1 * slot, color="#E5E5E5", zorder=0, label="±10 % of the English slot")
        for y_, (label, s, colour) in enumerate(reversed(bars)):
            ax.barh(y_, s, color=colour, height=0.55, zorder=2)
            ax.text(s + 0.05, y_, f"{s:.2f} s", va="center", fontsize=7)
        ax.set_yticks(range(3), [b[0] for b in reversed(bars)], fontsize=7)
        ax.set_xlabel("Seconds (speech, trimmed)", fontsize=7)
        ax.set_xlim(0, 1.25 * max(b[1] for b in bars))
        ax.tick_params(axis="x", labelsize=7)
        ax.set_title(f"FLEURS test {sid}: {fleurs[sid]['src_text'][:60]}…", fontsize=7, loc="left")
        ax.legend(fontsize=6, loc="lower right", frameon=False)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        fig.tight_layout()
        stem = out / f"demo_{sid}"
        fig.savefig(f"{stem}.png", dpi=300, metadata={"Software": None})
        fig.savefig(f"{stem}.pdf", metadata={"CreationDate": None, "ModDate": None, "Producer": None, "Creator": None})
        plt.close(fig)
        with open(f"{stem}.csv", "w", encoding="utf-8", newline="") as f:
            f.write(f"# drawn by isochron.time_check from {OUT / 'durations.csv'}; seconds are trimmed, the median of "
                    f"{TAKES} takes for the speech\n")
            w = csv.writer(f)
            w.writerow(["track", "seconds", "text"])
            w.writerow(["english", f"{slot:.3f}", fleurs[sid]["src_text"]])
            w.writerow(["plain", f"{seconds[by[(sid, 'a')]]:.3f}", text_of[by[(sid, "a")]]])
            w.writerow(["ours", f"{seconds[by[(sid, 'c')]]:.3f}", text_of[by[(sid, "c")]]])
        made[sid] = f"{stem}.png"
    return made


def median_take(values: list[float]) -> int:
    """The take whose duration is the median (the middle of three)."""
    return sorted(range(len(values)), key=lambda k: values[k])[len(values) // 2]


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=("plan", "english", "report"))
    args = ap.parse_args(argv)
    {"plan": plan, "english": english, "report": report}[args.cmd]()


if __name__ == "__main__":
    main()
