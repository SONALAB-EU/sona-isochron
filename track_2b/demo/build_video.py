"""The demo video: demo/out/isochron_demo.mp4 and its subtitles, from the narration and committed results.

    uv run --no-project --with faster-whisper==1.2.1 --with imageio-ffmpeg==0.6.0 --with pillow==12.3.0 \
        --with matplotlib==3.11.2 --with numpy==2.4.6 --with soundfile==0.14.0 --with num2words==0.5.14 \
        --with pyloudnorm==0.2.0 python demo/build_video.py

Not a project dependency: --with keeps pyproject.toml and uv.lock as they are.

Inputs (git-ignored, so on this machine only):
- demo/narration/scene1..7 (any audio format; the speaker's recordings, read only, never changed): copied
  to demo/out/narration/ and processed there
- audio/demo_voices/{1679,1903}/*.wav: the demo clips (isochron.time_check demo-voices, docs/demo_video.md)
- results/raw/hpc_8b_step4_test/items.jsonl: the raw loop record of the line shown as not fitting
Committed inputs: technical_report.md (key results, cost), results/time_check/demo_voices/durations.csv,
data/hf_dataset/native_check/test.jsonl. Every number on screen is read from these files at build time.

Narration: transcribed with Whisper small.en (faster-whisper, int8 on the CPU; base.en dropped the last
sentence of scene 2), aligned to SCRIPT word by word; cut only in the pause between two sentences; each
piece trimmed to TRIM_PAD s of silence at both ends; high-pass at 80 Hz. No other processing, no speed
change. Clips play alone, each normalised to the narration's loudness. The whole mix then gets one gain to
−16 LUFS and a 4× oversampled peak limiter for −1.5 dBTP (the narration's peaks are ~23 dB above its
loudness, so the ceiling cannot be met by gain alone); the MP4 is measured afterwards.

Output (demo/out/, git-ignored): isochron_demo.mp4 (1920×1080, 30 fps, H.264 yuv420p, AAC 48 kHz,
faststart), isochron_demo.srt (script text, transcript timing), timeline.md, slides/, frames/ (one per
scene), transcripts.json, word_diffs.md.
"""

from __future__ import annotations

import difflib
import json
import re
import shutil
import subprocess
import sys
import textwrap
from dataclasses import dataclass, field
from pathlib import Path

import imageio_ffmpeg
import numpy as np
import pyloudnorm
import soundfile as sf
from matplotlib import font_manager
from num2words import num2words
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
NARRATION = ROOT / "demo/narration"
OUT = ROOT / "demo/out"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
SR = 48000
W, H, FPS = 1920, 1080, 30
MAX_LEN = 120.0
TRIM_PAD = 0.15
LEAD_IN = 0.3

SCRIPT = {
    1: ["In dubbing, a translated line must fit the time the actor speaks.",
        "This English line takes three seconds.",
        "A plain German translation takes five and a half: over seventy percent too long.",
        "Today, someone fixes that by hand."],
    2: ["Isochron uses Apertus 1.5, the open Swiss model, with no fine-tuning.",
        "Apertus translates, then shortens to a length budget.",
        "Our code checks every candidate for length, meaning and language, and sends specific feedback.",
        "Apertus revises at most twice."],
    3: ["After the loop, the same line takes three point three seconds: it fits.",
        "This one lands just inside the band.",
        "And when the loop can't make a line fit, the output records it, so an editor knows which lines "
        "need work."],
    4: ["On the held-out test set, English to German and French, plain translation fits the budget in 20 to "
        "56 percent of lines; with our loop, 70 to 80.",
        "Lines that run too long, the costly error in dubbing, drop from up to 79 percent to at most 20.",
        "The cost: by an independent check, up to about five points fewer lines keep their full meaning."],
    5: ["In a separate test, we calibrated the budget to one synthetic voice.",
        "Then our lines fit the English timing in 47 of 99 cases, against 25 for plain translation."],
    6: ["It all runs sovereign: one command starts Apertus and our app in containers with no network, even "
        "on a laptop.",
        "On a GPU it costs about ten H100-minutes per thousand lines."],
    7: ["Machine meaning checks miss subtle changes, so a native speaker reviewed our German and found slips "
        "they missed, like a dropped 'some'.",
        "We report them.",
        "Isochron, by SONALAB, for Hack Apertus."],
}

ENGLISH = "English: FLEURS recording"
SYNTHETIC = "Synthetic voice (Qwen3-TTS), matched to the reader's gender, no cloning"
PICKED = "Examples picked by a fixed rule"


def run(*args: str) -> str:
    p = subprocess.run(args, capture_output=True, text=True)
    if p.returncode:
        sys.exit(f"failed: {' '.join(args)}\n{p.stderr[-3000:]}")
    return p.stderr


def load(path: Path, filters: str | None = None) -> np.ndarray:
    """Any audio file as mono float32 at SR, through ffmpeg."""
    args = [FFMPEG, "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR)]
    args += ["-af", filters] if filters else []
    out = subprocess.run(args + ["-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(out, dtype=np.float32).copy()


# ---------------------------------------------------------------- narration: files, transcripts, alignment

def norm_tokens(text: str) -> list[str]:
    text = text.lower().replace("%", " percent ").replace("–", " ")
    out = []
    text = re.sub(r"(^|\s)\.(\d)", r"\1point \2", text)  # Whisper writes 3.3 as the words "3" ".3"
    text = re.sub(r"(\d)?(^|\s)?-(\d)", r"\1\2 to \3", text)  # and "20 to 56" as "20-56" or "20" "-56"
    for tok in text.replace("-", " ").split():
        tok = tok.strip(".,:;!?'\"()“”‘’")
        if not tok:
            continue
        if re.fullmatch(r"\d+(\.\d+)?", tok):
            out += num2words(float(tok) if "." in tok else int(tok)).replace("-", " ").replace(",", "").split()
        else:
            out.append(tok)
    return out


def recordings() -> dict[int, Path]:
    files = sorted(p for p in NARRATION.iterdir() if p.is_file() and not p.name.startswith("."))
    if len(files) != 7:
        sys.exit(f"expected 7 recordings in {NARRATION}, found {len(files)}: {[p.name for p in files]}")
    named = {int(m.group(1)): p for p in files if (m := re.fullmatch(r"scene([1-7])\.\w+", p.name, re.I))}
    if len(named) != 7:
        sys.exit("the recordings are not named scene1..scene7: match them to scenes by transcript and rename "
                 "them (mv -n) first")
    return named


def transcribe(copies: dict[int, Path]) -> dict[int, list[dict]]:
    cache = OUT / "transcripts.json"
    if cache.exists():
        data = json.loads(cache.read_text())
        if data.get("files") == {str(k): p.name for k, p in copies.items()}:
            return {int(k): v for k, v in data["words"].items()}
    from faster_whisper import WhisperModel
    model = WhisperModel("small.en", device="cpu", compute_type="int8")
    words = {}
    for k, p in copies.items():
        segs, _ = model.transcribe(str(p), word_timestamps=True, beam_size=5, language="en")
        words[k] = [{"w": w.word.strip(), "s": round(w.start, 3), "e": round(w.end, 3)} for s in segs for w in s.words]
    cache.write_text(json.dumps({"model": "faster-whisper small.en int8", "files": {str(k): p.name for k, p in copies.items()},
                                 "words": words}, indent=1, ensure_ascii=False))
    return words


def check_scene_match(words: dict[int, list[dict]]) -> None:
    """Each recording must match its own scene's script best."""
    for k, ws in words.items():
        heard = norm_tokens(" ".join(w["w"] for w in ws))
        scores = {s: difflib.SequenceMatcher(None, norm_tokens(" ".join(t)), heard, autojunk=False).ratio()
                  for s, t in SCRIPT.items()}
        best = max(scores, key=scores.get)
        if best != k or scores[k] < 0.6:
            sys.exit(f"recording {k} matches scene {best} best (scores {scores}): rename or re-record")


@dataclass
class Sentence:
    scene: int
    index: int
    text: str
    start: float  # in the recording, s
    end: float


def align(scene: int, ws: list[dict], diffs: list[str]) -> list[Sentence]:
    """Script sentences located in the transcript: difflib over normalised tokens."""
    s_tok, s_sent = [], []
    for i, sent in enumerate(SCRIPT[scene]):
        t = norm_tokens(sent)
        s_tok += t
        s_sent += [i] * len(t)
    t_tok, t_word = [], []
    for j, w in enumerate(ws):
        t = norm_tokens(w["w"])
        t_tok += t
        t_word += [j] * len(t)
    to_tx: list[int | None] = [None] * len(s_tok)
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, s_tok, t_tok, autojunk=False).get_opcodes():
        if tag != "equal":
            diffs.append(f"| {scene} | {' '.join(s_tok[i1:i2]) or '–'} | {' '.join(t_tok[j1:j2]) or '–'} |")
        if tag in ("equal", "replace"):
            for i in range(i1, i2):
                to_tx[i] = j1 + min(j2 - j1 - 1, (i - i1) * (j2 - j1) // max(1, i2 - i1)) if j2 > j1 else None
    out = []
    for i in range(len(SCRIPT[scene])):
        idx = [to_tx[k] for k in range(len(s_tok)) if s_sent[k] == i and to_tx[k] is not None]
        if not idx:
            sys.exit(f"scene {scene}, sentence {i + 1} not found in the transcript")
        out.append(Sentence(scene, i, SCRIPT[scene][i], ws[t_word[min(idx)]]["s"], ws[t_word[max(idx)]]["e"]))
    return out


def rms_db(x: np.ndarray, hop: int = SR // 100) -> np.ndarray:
    n = len(x) // hop
    f = x[: n * hop].reshape(n, hop)
    return 20 * np.log10(np.sqrt((f ** 2).mean(axis=1)) + 1e-9)


def cut_point(x: np.ndarray, a: Sentence, b: Sentence) -> float:
    """The quietest 10 ms between two sentences; it must be a pause (40 dB below the recording's peak)."""
    env = rms_db(x)
    lo, hi = int((a.end - 0.1) * 100), int((b.start + 0.1) * 100)
    k = lo + int(np.argmin(env[lo:hi]))
    if env[k] > env.max() - 40:
        sys.exit(f"scene {a.scene}: no pause between sentences {a.index + 1} and {b.index + 1} ({env[k]:.0f} dB)")
    return (k + 0.5) / 100


def trim(x: np.ndarray) -> tuple[np.ndarray, float]:
    """Silence at both ends down to TRIM_PAD s; speech starts 40 dB below the piece's peak."""
    env = rms_db(x)
    on = np.flatnonzero(env > env.max() - 40)
    a = max(0, int((on[0] / 100 - TRIM_PAD) * SR))
    b = min(len(x), int(((on[-1] + 1) / 100 + TRIM_PAD) * SR))
    return x[a:b], a / SR


# ---------------------------------------------------------------- numbers from committed files

def report_row(prefix: str) -> list[str]:
    for line in (ROOT / "technical_report.md").read_text(encoding="utf-8").splitlines():
        if line.startswith(f"| {prefix}"):
            return [c.strip().strip("*") for c in line.strip("|").split("|")]
    sys.exit(f"technical_report.md: no table row starting {prefix!r}")


def pct_range(cell: str) -> str:
    """'19.6–55.6' -> '20–56 %' (whole percents, half up)."""
    return "–".join(str(int(float(v) + 0.5)) for v in cell.split("–")) + " %"


def numbers() -> dict:
    fit, long = report_row("Translation task: fit within"), report_row("Translation task: too long")
    nli2, timing = report_row("Translation task: meaning kept vs reference, second NLI"), report_row("Timing, budget calibrated")
    cost = report_row("(c) ours, (a) included")
    lo, hi = (float(v) for v in cost[5].split("–"))
    durations = {}
    for line in (ROOT / "results/time_check/demo_voices/durations.csv").read_text().splitlines()[1:]:
        c = line.split(",")
        durations[(c[0], c[1])] = (float(c[5]), float(c[6]))
    gap = re.search(r"finds ours ([\d.]+)–([\d.]+) points below plain", (ROOT / "technical_report.md").read_text())
    if not gap:
        sys.exit("technical_report.md: the second NLI's gap to plain translation is not where expected")
    return {"fit": [pct_range(c) for c in fit[1:4]], "long": [pct_range(c) for c in long[1:4]],
            "nli2": nli2[1:4], "nli2_gap": gap.groups(), "timing": (int(timing[1]), int(timing[3])),
            "cost_s": cost[5], "cost_min": (lo * 1000 / 60, hi * 1000 / 60), "dur": durations}


def unfit_record() -> dict:
    """The first German test line (by ID; seed 0, syllable budget) where ours ran the loop and its final
    candidate still misses the budget."""
    rows = [json.loads(l) for l in (ROOT / "results/raw/hpc_8b_step4_test/items.jsonl").open(encoding="utf-8")]
    for r in sorted((r for r in rows if r["seed"] == 0), key=lambda r: int(r["id"])):
        loop = r["budgets"]["isosyllabic"]["c"].get("loop")
        if loop and loop["final"] and not loop["final"]["hit"]:
            return {"id": r["id"], "source": r["source"], "loop": loop}
    sys.exit("no line found that the loop could not fit")


def dropped_some() -> dict:
    for line in (ROOT / "data/hf_dataset/native_check/test.jsonl").open(encoding="utf-8"):
        r = json.loads(line)
        if r["system"] == "c" and r["meaning"] == "wrong" and " some " in r["english_source"]:
            return r
    sys.exit("the dropped 'some' line is not in data/hf_dataset/native_check/test.jsonl")


# ---------------------------------------------------------------- slides

FONT_DIR = Path(font_manager.findfont("DejaVu Sans")).parent
INK, MUTED, BLUE, GREY, BAND, HILITE, BG = "#111111", "#4a4a4a", "#0072B2", "#8c8c8c", "#dcdcdc", "#ffe08a", "#ffffff"


def font(size: int, bold: bool = False, mono: bool = False) -> ImageFont.FreeTypeFont:
    name = "DejaVuSansMono" if mono else "DejaVuSans"
    return ImageFont.truetype(str(FONT_DIR / f"{name}{'-Bold' if bold else ''}.ttf"), size)


TITLE, BODY, SMALL = font(64, bold=True), font(46), font(40)


class Slide:
    """A 1920×1080 still. Every text goes through put(), which stops the build if it leaves the frame."""
    MARGIN = 100

    def __init__(self, title: str | None = None, sub: str | None = None):
        self.im = Image.new("RGB", (W, H), BG)
        self.d = ImageDraw.Draw(self.im)
        self.y = 90
        if title:
            self.text(title, TITLE, gap=24)
        if sub:
            self.text(sub, SMALL, fill=MUTED, gap=40)

    def put(self, xy: tuple[float, float], s: str, f, fill: str = INK) -> float:
        if re.search(r"step\s*\d", s, re.I):
            sys.exit(f"'step N' on screen: {s!r}")
        x0, y0, x1, y1 = self.d.textbbox(xy, s, font=f)
        if x0 < self.MARGIN - 40 or x1 > W - self.MARGIN or y1 > H - 40:
            sys.exit(f"slide text out of the frame: {s!r} at {(x0, y0, x1, y1)}")
        self.d.text(xy, s, font=f, fill=fill)
        return x1

    def text(self, s: str, f, x: int = 120, fill: str = INK, gap: int = 18, width: int = W - 240) -> None:
        for line in wrap(s, f, width):
            self.put((x, self.y), line, f, fill)
            self.y += f.size + 14
        self.y += gap

    def box(self, s: str, f, fill: str = "#fff4cc") -> None:
        """Text on a tinted panel as tall as the text."""
        lines = wrap(s, f, W - 300)
        h = len(lines) * (f.size + 14) + 36
        self.d.rounded_rectangle((100, self.y, W - 100, self.y + h), 16, fill=fill)
        for i, line in enumerate(lines):
            self.put((140, self.y + 18 + i * (f.size + 14)), line, f)
        self.y += h + 24

    def labels(self, *labels: str) -> None:
        """Source labels at the bottom."""
        lines = [l for s in labels for l in wrap(s, SMALL, W - 240)]
        y = H - 70 - len(lines) * (SMALL.size + 14)
        if y < self.y:
            sys.exit(f"labels overlap the slide's content: {labels}")
        for s in lines:
            self.put((120, y), s, SMALL, MUTED)
            y += SMALL.size + 14

    def chip(self, s: str, fill: str = INK, bg: str = HILITE) -> None:
        f = font(42, bold=True)
        w = int(self.d.textlength(s, font=f))
        self.d.rounded_rectangle((W - 120 - w - 40, 60, W - 120, 60 + f.size + 30), 12, fill=bg)
        self.put((W - 120 - w - 20, 75), s, f, fill)

    def save(self, path: Path) -> Path:
        self.im.save(path)
        return path


def wrap(s: str, f, width: int) -> list[str]:
    words, lines, cur = s.split(), [], ""
    for w in words:
        t = f"{cur} {w}".strip()
        if f.getlength(t) <= width or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    return lines + ([cur] if cur else [])


def bars(line: str, rows: list[tuple[str, float, str]], slot: float, labels: list[str], chip: str | None = None,
         note: str | None = None) -> Slide:
    """Seconds as horizontal bars, with the ±10 % band of the English slot."""
    s = Slide(f"FLEURS test line {line}", "Seconds as spoken; grey band: ±10 % of the English slot")
    if chip:
        s.chip(chip)
    x0, x1, top = 440, W - 560, s.y + 10
    scale = (x1 - x0) / max(r[1] for r in rows + [("", slot * 1.1, "")])
    rh, pitch = 74, 118
    band = (x0 + scale * slot * 0.9, x0 + scale * slot * 1.1)
    s.d.rectangle((band[0], top - 20, band[1], top + pitch * len(rows) - 20), fill=BAND)
    for i, (name, sec, color) in enumerate(rows):
        y = top + i * pitch
        s.put((x0 - 30 - s.d.textlength(name, font=BODY), y + 10), name, BODY)
        s.d.rectangle((x0, y, x0 + scale * sec, y + rh), fill=color)
        val = f"{sec:.2f} s" + ("" if name == "English" else f" · {100 * (sec / slot - 1):+.1f} %")
        s.put((max(x0 + scale * sec, band[1]) + 18, y + 12), val, BODY)
    s.d.line((x0, top - 20, x0, top + pitch * len(rows) - 20), fill=INK, width=3)
    s.y = top + pitch * len(rows) + 10
    if note:
        s.text(note, BODY)
    s.labels(*labels)
    return s


def slides(n: dict, rec: dict, some: dict) -> dict[str, Path]:
    d = OUT / "slides"
    d.mkdir(exist_ok=True)
    p: dict[str, Path] = {}

    s = Slide()
    s.y = 400
    s.text("Isochron: dubbing lines that fit their slot", font(70, bold=True), gap=40)
    s.text("SONALAB · Hack Apertus 2026 · Track 2B", font(52), fill=MUTED)
    p["title"] = s.save(d / "01_title.png")

    en, plain = n["dur"][("1679", "a")][1], n["dur"][("1679", "a")][0]
    ours = n["dur"][("1679", "c")][0]
    p["1679_en"] = bars("1679", [("English", en, INK)], en, [ENGLISH], chip="Playing: English").save(d / "02_1679_en.png")
    p["1679_plain"] = bars("1679", [("English", en, INK), ("Plain", plain, GREY)], en, [ENGLISH, SYNTHETIC],
                           note="Plain German overruns the English slot.").save(d / "03_1679_plain.png")

    s = Slide("The loop", "Apertus 1.5, no fine-tuning; our code checks every candidate")
    f = font(44)
    boxes = [("Apertus translates", False), ("Apertus shortens it to a length budget (syllables)", False),
             ("Our code checks every candidate: length, meaning, language", False),
             ("Fails? Specific feedback, and Apertus revises (at most twice)", True),
             ("Output: the best candidate, with its checks", False)]
    bx0, bx1, y, mids = 160, 1500, s.y - 10, []
    for i, (t, loop) in enumerate(boxes):
        lines = wrap(t, f, bx1 - bx0 - 80)
        h = len(lines) * 58 + 34
        s.d.rounded_rectangle((bx0, y, bx1, y + h), 18, outline=BLUE if loop else INK, width=4,
                              fill="#e8f1f8" if loop else BG)
        for j, line in enumerate(lines):
            s.put((bx0 + 40, y + 14 + j * 58), line, f)
        mids.append(y + h / 2)
        if i < len(boxes) - 1:
            cx = (bx0 + bx1) / 2
            s.d.line((cx, y + h, cx, y + h + 34), fill=INK, width=4)
            s.d.polygon([(cx - 14, y + h + 20), (cx + 14, y + h + 20), (cx, y + h + 36)], fill=INK)
        y += h + 38
    ax = bx1 + 110
    s.d.line([(bx1, mids[3]), (ax, mids[3]), (ax, mids[1]), (bx1 + 4, mids[1])], fill=BLUE, width=5)
    s.d.polygon([(bx1 + 2, mids[1]), (bx1 + 24, mids[1] - 14), (bx1 + 24, mids[1] + 14)], fill=BLUE)
    s.put((ax + 20, (mids[1] + mids[3]) / 2 - 24), "revise", SMALL, BLUE)
    p["loop"] = s.save(d / "04_loop.png")

    rows = [("English", en, INK), ("Plain", plain, GREY), ("Ours", ours, BLUE)]
    p["1679_ours"] = bars("1679", rows, en, [ENGLISH, SYNTHETIC, PICKED], chip="Fits").save(d / "05_1679_ours.png")
    en2, ours2 = n["dur"][("1903", "c")][1], n["dur"][("1903", "c")][0]
    p["1903"] = bars("1903", [("English", en2, INK), ("Ours", ours2, BLUE)], en2, [ENGLISH, SYNTHETIC, PICKED],
                     chip="Just inside").save(d / "06_1903.png")

    loop, fin = rec["loop"], rec["loop"]["final"]
    s = Slide("Lines that don't fit are marked",
              f"German test line {rec['id']}; budget {loop['target']} {loop['unit']}; excerpt of the raw loop record (test run)")
    mono = font(40, mono=True)
    lines = [("{", False)] + [(f'  "text": "{t}' if i == 0 else f"           {t}", False)
                              for i, t in enumerate(textwrap.wrap(fin["text"] + '",', 58))]
    lines += [(f'  "syllables": {fin["syllables"]},', False), (f'  "hit": {json.dumps(fin["hit"])},', True),
              (f'  "final_accepted": {json.dumps(loop["final_accepted"])},', True),
              (f'  "revisions": {loop["revisions"]}', False), ("}", False)]
    y = s.y
    for t, hi in lines:
        if hi:
            s.d.rectangle((150, y - 6, 150 + s.d.textlength(t, font=mono) + 20, y + 50), fill=HILITE)
        s.put((160, y), t, mono)
        y += 56
    s.y = y
    s.labels(PICKED + ": the first such line by ID")
    p["unfit"] = s.save(d / "07_unfit.png")

    def results(cost: bool) -> Slide:
        s = Slide("Held-out test: English → German, French",
                  "Translation task; Apertus 1.5 8B; 4 settings × 3 seeds; ranges over the settings")
        cols = [860, 1210, 1560]
        for c, h in zip(cols, ["Plain", "One step", "Ours"]):
            s.put((c, s.y), h, font(46, bold=True), BLUE if h == "Ours" else INK)
        y = s.y + 90
        for name, vals in [("Fits the budget (±10 %)", n["fit"]), ("Too long (over +10 %)", n["long"])]:
            s.d.line((120, y - 22, W - 120, y - 22), fill=BAND, width=3)
            s.put((120, y), name, BODY)
            for c, v in zip(cols, vals):
                s.put((c, y), v, font(46, bold=c == cols[2]), BLUE if c == cols[2] else INK)
            y += 110
        s.y = y + 10
        if cost:
            s.box(f"The cost: by an independent meaning check, ours keeps full meaning "
                  f"{n['nli2_gap'][0]}–{n['nli2_gap'][1]} points less often than plain.", BODY)
        s.labels("FLEURS test: 347 German, 332 French sentences. Fit pre-registered; too long post-hoc")
        return s

    p["results"] = results(False).save(d / "08_results.png")
    p["results_cost"] = results(True).save(d / "09_results_cost.png")

    plain_n, ours_n = n["timing"]
    s = Slide("Timed with one synthetic voice", "Budget calibrated to that voice (Qwen3-TTS, preset Aiden)")
    s.chip("Exploratory")
    x0, top = 520, s.y + 40
    for i, (name, v, c) in enumerate([("Plain", plain_n, GREY), ("Ours", ours_n, BLUE)]):
        y = top + i * 170
        s.put((x0 - 30 - s.d.textlength(name, font=BODY), y + 30), name, BODY)
        s.d.rectangle((x0, y, x0 + v * 13, y + 120), fill=c)
        s.put((x0 + v * 13 + 24, y + 26), f"{v} of 99", font(60, bold=True))
    s.y = top + 2 * 170 + 30
    s.text("German lines spoken within ±10 % of the English speaker's time", BODY)
    s.labels("Exploratory: added after the test outputs existed")
    p["timing"] = s.save(d / "10_timing.png")

    def terminal(cost: bool) -> Slide:
        s = Slide("One command, no network", "Apertus and our app in containers; this run on a laptop CPU")
        s.chip("No network", fill="#ffffff", bg=INK)
        mono = font(40, mono=True)
        lines = ["$ make run-offline GGUF=… LLM_QUANTISATION=Q4_K_M",
                 "  llama-server + app: network_mode: none",
                 "  Apertus 1.5 8B, Q4_K_M, llama.cpp, CPU (Apple M3)",
                 "  10 German lines: fit 6/10, meaning kept (NLI) 10/10",
                 "  exit 0"]
        s.d.rounded_rectangle((120, s.y, W - 120, s.y + 40 + 66 * len(lines)), 16, fill="#1e1e1e")
        for i, t in enumerate(lines):
            s.put((160, s.y + 30 + i * 66), t, mono, "#e6e6e6" if i else "#9ad19a")
        s.y += 40 + 66 * len(lines) + 30
        if cost:
            s.box("Cost is an estimate: " + n["cost_s"] + " H100-seconds per line, about "
                  f"{n['cost_min'][0]:.0f}–{n['cost_min'][1]:.0f} H100-minutes per 1,000 lines", BODY)
        s.labels("From results/docker_check.md (2026-10-12): a summary of the run, not a recording")
        return s

    p["terminal"] = terminal(False).save(d / "11_terminal.png")
    p["terminal_cost"] = terminal(True).save(d / "12_terminal_cost.png")

    s = Slide("A native speaker checked our German", f"FLEURS test line {some['fleurs_id']}, ours")
    s.text("English:", font(46, bold=True), gap=4)
    x, y = 120, s.y
    for wd in some["english_source"].split():
        f = font(46, bold=wd == "some")
        if x + s.d.textlength(wd, font=f) > W - 160:
            x, y = 120, y + 60
        if wd == "some":
            s.d.rectangle((x - 6, y - 4, x + s.d.textlength(wd, font=f) + 6, y + 56), fill=HILITE)
        s.put((x, y), wd, f)
        x += s.d.textlength(wd + " ", font=f)
    s.y = y + 90
    s.text("German (ours):", font(46, bold=True), gap=4)
    s.text(some["german_output"], BODY, gap=40)
    s.text("Native speaker: wrong, \"some\" is dropped", font(46, bold=True), fill="#b00020", gap=8)
    nli = "kept" if some["nli_kept_ref"] and some["nli2_kept_ref"] else "not kept"
    s.text(f"Both NLI meaning checks: meaning {nli}", BODY)
    p["some"] = s.save(d / "13_some.png")

    s = Slide("Isochron")
    s.text("SONALAB · Hack Apertus 2026 · Track 2B", font(52), fill=MUTED, gap=50)
    for t in ["FLEURS recordings (CC BY 4.0)", "Apertus 1.5 (Swiss AI Initiative)", "Qwen3-TTS (Apache-2.0)",
              "SONALAB", "github.com/SONALAB-EU/sona-isochron", "huggingface.co/datasets/sonalab/sona-isochron"]:
        s.text(t, BODY, gap=6)
    p["end"] = s.save(d / "14_end.png")
    return p


# ---------------------------------------------------------------- timeline

@dataclass
class Item:
    scene: int
    kind: str  # voice, clip, gap
    source: str
    audio: np.ndarray
    slide: str
    subs: list[tuple[float, float, str]] = field(default_factory=list)  # offsets within the item
    switches: list[tuple[float, str]] = field(default_factory=list)


def plan(gap_in: float, gap_scene: float, end_hold: float, drop_1903: bool, voice, clip) -> list[Item]:
    sil = lambda s, sc, sl: Item(sc, "gap", "silence", np.zeros(int(s * SR), np.float32), sl)
    items = [sil(LEAD_IN, 1, "title"), voice(1, [0], "title"), sil(gap_in, 1, "1679_en"),
             clip(1, "1679/english", ENGLISH, "1679_en"), sil(gap_in, 1, "1679_en"), voice(1, [1], "1679_en"),
             sil(gap_in, 1, "1679_plain"), clip(1, "1679/plain", SYNTHETIC, "1679_plain"), sil(gap_in, 1, "1679_plain"),
             voice(1, [2, 3], "1679_plain"),
             sil(gap_scene, 2, "loop"), voice(2, [0, 1, 2, 3], "loop"),
             sil(gap_scene, 3, "1679_ours"), clip(3, "1679/ours", SYNTHETIC, "1679_ours"), sil(gap_in, 3, "1679_ours"),
             voice(3, [0], "1679_ours")]
    if drop_1903:
        items += [sil(gap_in, 3, "unfit"), voice(3, [2], "unfit")]
    else:
        items += [sil(gap_in, 3, "1903"), clip(3, "1903/ours", SYNTHETIC, "1903"), sil(gap_in, 3, "1903"),
                  voice(3, [1, 2], "1903", {2: "unfit"})]
    items += [sil(gap_scene, 4, "results"), voice(4, [0, 1, 2], "results", {2: "results_cost"}),
              sil(gap_scene, 5, "timing"), voice(5, [0, 1], "timing"),
              sil(gap_scene, 6, "terminal"), voice(6, [0, 1], "terminal", {1: "terminal_cost"}),
              sil(gap_scene, 7, "some"), voice(7, [0, 1, 2], "some", {2: "end"}), sil(end_hold, 7, "end")]
    return items


def main() -> None:
    OUT.mkdir(exist_ok=True)
    (OUT / "narration").mkdir(exist_ok=True)
    rec = recordings()
    copies = {}
    for k, p in rec.items():
        c = OUT / "narration" / p.name
        if not c.exists():
            shutil.copy2(p, c)
        copies[k] = c
    words = transcribe(copies)
    check_scene_match(words)
    diffs: list[str] = []
    sentences = {k: align(k, words[k], diffs) for k in SCRIPT}
    (OUT / "word_diffs.md").write_text("| Scene | Script | Heard (small.en) |\n|---|---|---|\n" + "\n".join(diffs) + "\n")

    audio = {k: load(copies[k], "highpass=f=80") for k in SCRIPT}
    ref = pyloudnorm.Meter(SR)
    voice_lufs = ref.integrated_loudness(np.concatenate([audio[k] for k in SCRIPT]).astype(np.float64))

    def voice(scene: int, idx: list[int], slide: str, switch: dict[int, str] | None = None) -> Item:
        ss, x = sentences[scene], audio[scene]
        a = cut_point(x, ss[idx[0] - 1], ss[idx[0]]) if idx[0] > 0 else 0.0
        b = cut_point(x, ss[idx[-1]], ss[idx[-1] + 1]) if idx[-1] < len(ss) - 1 else len(x) / SR
        piece, off = trim(x[int(a * SR):int(b * SR)])
        t0 = a + off
        subs = [(max(0.0, ss[i].start - t0), min(len(piece) / SR, ss[i].end - t0), ss[i].text) for i in idx]
        sw = [(cut_point(x, ss[i - 1], ss[i]) - t0, sl) for i, sl in (switch or {}).items()]
        return Item(scene, "voice", f"scene{scene} sentence{'s' if len(idx) > 1 else ''} "
                    f"{', '.join(str(i + 1) for i in idx)}", piece, slide, subs, sw)

    def clip(scene: int, name: str, label: str, slide: str) -> Item:
        x = load(ROOT / "audio/demo_voices" / f"{name}.wav").astype(np.float64)
        x *= 10 ** ((voice_lufs - ref.integrated_loudness(x)) / 20)
        return Item(scene, "clip", f"{name}.wav ({label.split(':')[0].split(' (')[0]})", x.astype(np.float32), slide)

    n, unfit, some = numbers(), unfit_record(), dropped_some()
    ladder = [(0.4, 0.8, 3.0, False, "planned gaps"), (0.3, 0.3, 2.0, False, "gaps 0.3 s, end hold 2 s"),
              (0.3, 0.3, 2.0, True, "and without \"This one lands just inside the band\"")]
    for gap_in, gap_scene, hold, drop, what in ladder:
        items = plan(gap_in, gap_scene, hold, drop, voice, clip)
        total = sum(len(i.audio) for i in items) / SR
        print(f"{what}: {total:.2f} s")
        if total <= MAX_LEN:
            break
    draft = total > MAX_LEN

    rows, t = [], 0.0
    for it in items:
        rows.append(f"| {it.scene} | {it.kind} | {it.source} | {t:.2f} | {len(it.audio) / SR:.2f} |")
        it.t = t  # type: ignore[attr-defined]
        t += len(it.audio) / SR
    savings = []
    if draft:
        for it in items:
            if it.kind == "voice":
                for s0, s1, txt in it.subs:
                    savings.append(f"- scene {it.scene}: \"{txt}\" ({s1 - s0 + 0.3:.1f} s with its pause)")
    timeline = ("| Scene | Kind | Source | Start (s) | Length (s) |\n|---|---|---|--:|--:|\n" + "\n".join(rows)
                + f"\n\nTotal: {t:.2f} s ({what}){'; DRAFT: over 2:00' if draft else ''}\n")
    if draft:
        timeline += "\nSentences that could go (seconds each saves):\n" + "\n".join(savings) + "\n"
    (OUT / "timeline.md").write_text(timeline)
    print(timeline)

    paths = slides(n, unfit, some)
    # Video: one still per change of slide, frame-aligned
    changes = []
    for it in items:
        changes.append((it.t, it.slide))
        changes += [(it.t + o, sl) for o, sl in it.switches]
    changes.sort()
    merged = [c for i, c in enumerate(changes) if i == 0 or c[1] != changes[i - 1][1]]
    frames = [round(c[0] * FPS) for c in merged] + [round(t * FPS)]
    lst = OUT / "slides.ffconcat"
    body = ["ffconcat version 1.0"]
    for (_, sl), f0, f1 in zip(merged, frames, frames[1:]):
        body += [f"file '{paths[sl]}'", f"duration {(f1 - f0) / FPS:.6f}"]
    body.append(f"file '{paths[merged[-1][1]]}'")
    lst.write_text("\n".join(body) + "\n")

    # Loudness: one gain for the whole mix, then a 4× oversampled peak limiter for the true-peak ceiling. At
    # −16 LUFS the narration's peaks would reach about +7 dBFS, so −1.5 dBTP needs limiting; loudnorm's dynamic
    # mode would compress all of it instead. The gain is corrected for what the limiter takes off.
    mix = np.concatenate([it.audio for it in items]).astype(np.float64)
    limiter = "aresample=192000,alimiter=limit=0.79:attack=1:release=50:asc=1:level=disabled,aresample=48000"
    gain = -16 - ref.integrated_loudness(mix)
    for _ in range(4):
        sf.write(OUT / "mix_gain.wav", mix * 10 ** (gain / 20), SR, subtype="FLOAT")
        run(FFMPEG, "-v", "error", "-y", "-i", str(OUT / "mix_gain.wav"), "-af", limiter, "-c:a", "pcm_f32le",
            str(OUT / "mix.wav"))
        got = ref.integrated_loudness(sf.read(OUT / "mix.wav")[0])
        if abs(got + 16) < 0.05:
            break
        gain += -16 - got
    mp4 = OUT / "isochron_demo.mp4"
    run(FFMPEG, "-hide_banner", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-i", str(OUT / "mix.wav"),
        "-r", str(FPS), "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-tune", "stillimage",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart",
        "-t", f"{t:.3f}", str(mp4))
    log = run(FFMPEG, "-hide_banner", "-nostats", "-i", str(mp4), "-af", "ebur128=peak=true", "-f", "null", "-")
    summary = log[log.rindex("Summary:"):]
    lufs = float(re.search(r"I:\s+(-?[\d.]+) LUFS", summary).group(1))
    tp = float(re.search(r"Peak:\s+(-?[\d.]+) dBFS", summary).group(1))
    print(f"gain {gain:+.1f} dB, then the limiter; the MP4 measures {lufs} LUFS, true peak {tp} dBFS")
    if abs(lufs + 16) > 0.5 or tp > -1.5:
        sys.exit("the MP4 misses −16 LUFS / −1.5 dBTP")
    with (OUT / "timeline.md").open("a") as f:
        f.write(f"\nLoudness: gain {gain:+.1f} dB and a peak limiter; MP4 {lufs} LUFS, true peak {tp} dBTP\n")

    def ts(x: float) -> str:
        ms = round(x * 1000)
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
    cues = [(it.t + a, it.t + b, txt) for it in items for a, b, txt in it.subs]
    (OUT / "isochron_demo.srt").write_text("".join(f"{i}\n{ts(a)} --> {ts(b)}\n{txt}\n\n"
                                                  for i, (a, b, txt) in enumerate(cues, 1)), encoding="utf-8")

    fr = OUT / "frames"
    fr.mkdir(exist_ok=True)
    for (t0, sl), f0, f1 in zip(merged, frames, frames[1:]):
        mid = (f0 + f1) / 2 / FPS
        run(FFMPEG, "-v", "error", "-y", "-ss", f"{mid:.3f}", "-i", str(mp4), "-frames:v", "1",
            str(fr / f"{t0:06.2f}_{sl}.png"))
    print(f"wrote {mp4} ({t:.2f} s){' as a DRAFT' if draft else ''}")


if __name__ == "__main__":
    main()
