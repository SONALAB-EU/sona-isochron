# /// script
# requires-python = ">=3.11,<3.12"
# dependencies = ["openai-whisper==20250625", "soundfile", "librosa"]
# ///
"""Transcribe the time check's TTS takes with Whisper (small, German, temperature 0), as a check that each
take says its text and nothing more (isochron.time_check qc reads the output). Diagnosis only.

    uv run scripts/asr_whisper.py audio/tts/*_take*.wav > results/time_check/asr.jsonl
"""

import json
import sys

import librosa
import numpy as np
import soundfile as sf
import whisper

model = whisper.load_model("small")
for path in sys.argv[1:]:
    y, sr = sf.read(path, dtype="float32")
    y = librosa.resample(y, orig_sr=sr, target_sr=16_000).astype(np.float32)
    result = model.transcribe(y, language="de", temperature=0.0, fp16=False)
    print(json.dumps({"file": path.rsplit("/", 1)[-1], "text": result["text"].strip()}, ensure_ascii=False), flush=True)
