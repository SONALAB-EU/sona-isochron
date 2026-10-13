"""Synthesise the time check's and the demo's German lines with Qwen3-TTS, keeping only clean takes
(protocol v2.28; run by hpc/tts_qwen.sbatch in its own venv, so it imports nothing from isochron).

Round r (r = 0 … ROUNDS - 1) seeds torch with r and reads, in one batch, every text with fewer than 3 clean
takes, with the preset voice VOICE and no instruction. Whisper small transcribes every take; a take is
rejected when its transcript has more than MAX_EXTRA words after the last word it shares with the text
(extra_words, the same as isochron.time_check.extra_words). Every take is kept as a 32-bit float WAV,
<text_id>_r<round>.wav, and log.jsonl says which are clean. It stops starting rounds after --budget-min.

    python hpc/tts_qwen_synth.py PLAN.jsonl --model DIR --whisper DIR --out DIR [--budget-min 13]
"""

from __future__ import annotations

import argparse
import difflib
import json
import platform
import random
import re
import time
from importlib.metadata import version
from pathlib import Path

VOICE = "Aiden"
LANGUAGE = "German"
TAKES, ROUNDS, MAX_EXTRA = 3, 10, 1
SETTINGS = {"do_sample": True, "temperature": 0.9, "top_k": 50, "top_p": 1.0, "repetition_penalty": 1.05,
            "subtalker_dosample": True, "subtalker_temperature": 0.9, "subtalker_top_k": 50, "subtalker_top_p": 1.0,
            "max_new_tokens": 2048}
WHISPER = {"model": "small", "language": "de", "temperature": 0.0}


def full_stop(text: str) -> str:
    """isochron.native_check.full_stop: a line not ending in . ! ? … gets a full stop."""
    stripped = text.rstrip()
    return stripped if stripped.rstrip("\"'”“’»)]").endswith((".", "!", "?", "…")) else stripped + "."


def extra_words(text: str, transcript: str) -> int:
    """Words the speech has after the last word it shares with its text (isochron.time_check.extra_words)."""
    words = lambda s: re.findall(r"\w+", s.lower())  # noqa: E731
    said, asr = words(text), words(transcript)
    blocks = [b for b in difflib.SequenceMatcher(None, said, asr, autojunk=False).get_matching_blocks() if b.size]
    return len(asr) - (blocks[-1].b + blocks[-1].size if blocks else 0)


def longer_chars(text: str, transcript: str) -> float:
    """Transcript length ÷ text length, in characters without spaces, punctuation or case (protocol v2.30)."""
    norm = lambda s: re.sub(r"[\W_]+", "", s.lower())  # noqa: E731
    return len(norm(transcript)) / max(1, len(norm(text)))


MAX_LONGER = 1.10  # the chars10 rule: a transcript more than 10 % longer is rejected


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("plan", type=Path)
    ap.add_argument("--model", type=Path, required=True)
    ap.add_argument("--whisper", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--budget-min", type=float, default=13.0)
    ap.add_argument("--device", default="cuda", help="cpu only for a smoke test")
    ap.add_argument("--limit", type=int, help="only the first N texts and 1 round (a smoke test)")
    ap.add_argument("--rule", choices=("extra-words", "chars10"), default="extra-words",
                    help="extra-words: at most 1 word after the text (v2.28); chars10: transcript at most 10 %% longer (v2.30)")
    args = ap.parse_args()
    started = time.time()
    import librosa
    import numpy as np
    import soundfile as sf
    import torch
    import whisper
    from qwen_tts import Qwen3TTSModel

    texts = [json.loads(line) for line in args.plan.read_text(encoding="utf-8").splitlines() if line.strip()][:args.limit]
    rounds = 1 if args.limit else ROUNDS
    cuda = args.device == "cuda"
    spoken = {t["text_id"]: full_stop(t["text"]) for t in texts}
    model = Qwen3TTSModel.from_pretrained(str(args.model), device_map="cuda:0" if cuda else "cpu", dtype=torch.bfloat16,
                                          attn_implementation="sdpa")
    asr = whisper.load_model(WHISPER["model"], device=args.device, download_root=str(args.whisper))
    loaded = time.time() - started
    args.out.mkdir(parents=True, exist_ok=True)
    clean: dict[str, list[str]] = {t["text_id"]: [] for t in texts}
    stopped = None
    with open(args.out / "log.jsonl", "w", encoding="utf-8") as log:
        for r in range(rounds):
            todo = [tid for tid in spoken if len(clean[tid]) < TAKES]
            if not todo:
                break
            if time.time() - started > 60 * args.budget_min:
                stopped = f"stopped before round {r}: {args.budget_min} min budget"
                break
            random.seed(r)
            np.random.seed(r)
            torch.manual_seed(r)
            if cuda:
                torch.cuda.manual_seed_all(r)
            t0 = time.time()
            wavs, sr = model.generate_custom_voice(text=[spoken[t] for t in todo], language=[LANGUAGE] * len(todo),
                                                   speaker=[VOICE] * len(todo), **SETTINGS)
            gen_s = time.time() - t0
            for tid, wav in zip(todo, wavs):
                audio = np.asarray(wav, dtype=np.float32).reshape(-1)
                name = f"{tid}_r{r}.wav"
                sf.write(args.out / name, audio, sr, subtype="FLOAT")
                y16 = librosa.resample(audio, orig_sr=sr, target_sr=16_000).astype(np.float32)
                heard = asr.transcribe(y16, language=WHISPER["language"], temperature=WHISPER["temperature"],
                                       fp16=False)["text"].strip() if len(audio) else ""
                extra = extra_words(spoken[tid], heard) if heard else 0
                longer = longer_chars(spoken[tid], heard)
                ok = bool(len(audio)) and bool(heard) and (
                    extra <= MAX_EXTRA if args.rule == "extra-words" else longer <= MAX_LONGER)
                if ok:
                    clean[tid].append(name)
                log.write(json.dumps({"text_id": tid, "round": r, "seed": r, "file": name, "samples": len(audio),
                                      "peak": round(float(np.abs(audio).max()), 4) if len(audio) else 0.0,
                                      "transcript": heard, "extra_words": extra,
                                      "longer": round(longer, 4), "clean": ok,
                                      "take": clean[tid].index(name) if ok and name in clean[tid][:TAKES] else None},
                                     ensure_ascii=False) + "\n")
            log.flush()
            print(f"round {r}: {len(todo)} texts in {gen_s:.0f} s; "
                  f"{sum(len(c) >= TAKES for c in clean.values())}/{len(clean)} texts have {TAKES} clean takes", flush=True)
    settings = {"model": "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice", "voice": VOICE, "language": LANGUAGE, **SETTINGS,
                "dtype": "bfloat16", "attn_implementation": "sdpa", "sample_rate": sr if texts else None,
                "takes": TAKES, "rounds": ROUNDS, "rule": args.rule,
                "max_extra_words": MAX_EXTRA, "max_longer": MAX_LONGER, "whisper": WHISPER,
                "gpu": torch.cuda.get_device_name(0) if cuda else "none (cpu)", "load_s": round(loaded, 1), "wall_s": round(time.time() - started, 1),
                "stopped": stopped, "python": platform.python_version(),
                "versions": {p: version(p) for p in ("qwen-tts", "torch", "torchaudio", "transformers", "accelerate",
                                                     "openai-whisper", "numpy")},
                "shortfalls": {tid: len(c) for tid, c in clean.items() if len(c) < TAKES}}
    (args.out / "settings.json").write_text(json.dumps(settings, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(settings))


if __name__ == "__main__":
    main()
