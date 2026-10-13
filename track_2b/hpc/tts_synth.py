"""Synthesise the time check's German lines with Chatterbox multilingual (run by hpc/tts.sbatch).

Runs in the TTS environment (hpc/tts_requirements.txt), not the project's, so it imports nothing from
isochron. Input: the plan that isochron.time_check writes (one JSON object per text: text_id, text). For
every text and every take, it seeds torch with the take's seed and writes <text_id>_take<k>.wav (mono,
the model's 24 kHz), then log.jsonl with each clip's seed, settings and generation time, and
settings.json. The voice is the model's built-in default (conds.pt): no reference audio, so no cloning.
It stops starting new clips once --budget-min minutes have passed, and says so.

    python hpc/tts_synth.py PLAN.jsonl --ckpt DIR --out DIR [--takes 3] [--budget-min 22]
"""

from __future__ import annotations

import argparse
import json
import platform
import random
import time
from importlib.metadata import version
from pathlib import Path

SETTINGS = {  # chatterbox-tts 0.1.7's own defaults for generate(), fixed here
    "language_id": "de", "exaggeration": 0.5, "cfg_weight": 0.5, "temperature": 0.8,
    "repetition_penalty": 2.0, "min_p": 0.05, "top_p": 1.0, "audio_prompt_path": None,
}
SEEDS = (0, 1, 2)  # take k uses seed SEEDS[k]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("plan", type=Path)
    ap.add_argument("--ckpt", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--takes", type=int, default=3)
    ap.add_argument("--budget-min", type=float, default=22.0)
    args = ap.parse_args()
    started = time.time()
    import numpy as np
    import soundfile as sf
    import torch
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS

    texts = [json.loads(line) for line in args.plan.read_text(encoding="utf-8").splitlines() if line.strip()]
    args.out.mkdir(parents=True, exist_ok=True)
    model = ChatterboxMultilingualTTS.from_local(args.ckpt, "cuda")
    loaded = time.time() - started
    settings = {**SETTINGS, "seeds": list(SEEDS[:args.takes]), "sample_rate": model.sr, "device": "cuda",
                "gpu": torch.cuda.get_device_name(0), "load_s": round(loaded, 1),
                "versions": {p: version(p) for p in ("chatterbox-tts", "torch", "torchaudio", "transformers",
                                                     "resemble-perth", "numpy")},
                "python": platform.python_version(), "texts": len(texts), "takes": args.takes}
    stopped = None
    with open(args.out / "log.jsonl", "a", encoding="utf-8") as log:
        for t in texts:
            for k in range(args.takes):
                path = args.out / f"{t['text_id']}_take{k}.wav"
                if path.exists():
                    continue
                if time.time() - started > 60 * args.budget_min:
                    stopped = f"stopped at {t['text_id']} take {k}: {args.budget_min} min budget"
                    break
                seed = SEEDS[k]
                random.seed(seed)
                np.random.seed(seed)
                torch.manual_seed(seed)
                torch.cuda.manual_seed_all(seed)
                t0 = time.time()
                wav = model.generate(t["text"], **SETTINGS)
                audio = wav.squeeze(0).cpu().numpy().astype("float32")
                sf.write(path, audio, model.sr, subtype="PCM_16")
                log.write(json.dumps({"text_id": t["text_id"], "take": k, "seed": seed, "file": path.name,
                                      "samples": len(audio), "peak": round(float(np.abs(audio).max()), 4),
                                      "gen_s": round(time.time() - t0, 2)}) + "\n")
                log.flush()
            if stopped:
                break
    settings["wall_s"] = round(time.time() - started, 1)
    settings["stopped"] = stopped
    (args.out / "settings.json").write_text(json.dumps(settings, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(settings))


if __name__ == "__main__":
    main()
