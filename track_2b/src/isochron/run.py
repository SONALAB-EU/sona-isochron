"""Generate candidates with Apertus and save all of them, unscored.

Step 2: shorten a FLEURS reference sentence in its own language to 90 / 80 /
70 / 60 % of its length (syllables by default). Each request asks for JSON
with 4 candidates; every candidate and the raw answer are saved. Scoring is
separate (isochron.score), so a run can be rescored offline.

Writes to results/raw/<run>/ (git-ignored):
  config.json       date, git commit, model, quantisation, endpoint, seeds,
                    prompt version and hash, generation settings, items
  candidates.jsonl  one line per (sentence, level, seed)

Run from track_2b/:

    uv run python -m isochron.run --quantisation Q8_0 --limit 5 --exclude-gonogo --seeds 0
    uv run python -m isochron.run --quantisation Q8_0 --gonogo --levels 80
    uv run python -m isochron.run --mock --limit 5 --exclude-gonogo --seeds 0   (no LLM)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from isochron.candidates import N_CANDIDATES, parse_candidates
from isochron.config import ConfigError, LLMConfig
from isochron.gonogo import gonogo_ids
from isochron.llm import ChatClient
from isochron.metrics.length import counter_description, default_counter, length, target
from isochron.prompts import Prompt
from isochron.provenance import git_commit
from isochron.schema import SentenceRecord, read_jsonl

STEP = 2
LEVELS = (90, 80, 70, 60)
SEEDS = (0, 1, 2)
# Temperature 0.7, then nucleus top_p 0.95, nothing else (the vLLM / transformers
# order). top_k 0 and min_p 0 switch off llama-server's defaults (top_k 40,
# min_p 0.05); its "samplers" field sets the order, since by default it applies
# temperature last.
GENERATION: dict[str, Any] = {
    "temperature": 0.7,
    "top_p": 0.95,
    "top_k": 0,
    "min_p": 0.0,
    "max_tokens": 1024,
    "chat_template_kwargs": {"enable_thinking": False},
}
LLAMACPP_SAMPLERS = ["temperature", "top_p"]


def mock_answer(text: str, unit: str, lang: str, goal: int, seed: int, counter: str) -> str:
    """A stand-in for the LLM in dry runs: word-prefix cuts of the input, as JSON."""
    words = text.split()
    prefixes = [" ".join(words[:k]) for k in range(1, len(words) + 1)]
    best = min(range(len(prefixes)), key=lambda k: abs(length(prefixes[k], unit, lang, counter) - goal))
    picks = [prefixes[max(best - 1, 0)], prefixes[best], prefixes[min(best + 1, len(prefixes) - 1)], text]
    random.Random(seed).shuffle(picks)
    return json.dumps({"candidates": picks}, ensure_ascii=False)


def _get_json(config: LLMConfig, url: str) -> dict[str, Any] | None:
    try:
        r = httpx.get(url, headers={"Authorization": f"Bearer {config.api_key}"}, timeout=10)
        r.raise_for_status()
        data = r.json()
    except (httpx.HTTPError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def backend_info(config: LLMConfig) -> dict[str, Any]:
    """What serves the model: llama-server answers /props; vLLM and hpc/hf_server.py answer /version."""
    root = config.base_url.removesuffix("/v1")
    props = _get_json(config, f"{root}/props")
    if props and "build_info" in props:
        return {
            "type": "llama.cpp llama-server",
            "build_info": props.get("build_info"),
            "model_path": props.get("model_path"),
            "n_ctx": (props.get("default_generation_settings") or {}).get("n_ctx"),
            "samplers": LLAMACPP_SAMPLERS,
        }
    ver = _get_json(config, f"{root}/version")
    models = (_get_json(config, f"{config.base_url}/models") or {}).get("data") or [{}]
    served = next((m for m in models if m.get("id") == config.name), models[0])
    if ver and ver.get("server") == "isochron-hf-server":
        return {"type": "transformers (hpc/hf_server.py)", "build_info": f"transformers {ver.get('transformers')}",
                "model_path": ver.get("model_path"), "dtype": ver.get("dtype"), "torch": ver.get("torch")}
    if ver and "version" in ver:
        return {"type": "vLLM", "build_info": f"vLLM {ver['version']}", "model_path": served.get("root"),
                "max_model_len": served.get("max_model_len")}
    return {"type": "unknown (no /props or /version)"}


def check_endpoint(config: LLMConfig) -> None:
    try:
        r = httpx.get(
            f"{config.base_url}/models", headers={"Authorization": f"Bearer {config.api_key}"}, timeout=10
        )
        r.raise_for_status()
    except httpx.HTTPError as e:
        sys.exit(f"LLM endpoint {config.base_url} not reachable ({e}); use --mock for a dry run")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Generate step 2 candidates (shorten in the same language).")
    ap.add_argument("--lang", choices=("de", "fr"), default="de")
    ap.add_argument("--split", choices=("dev", "test"), default="dev")
    ap.add_argument("--unit", choices=("syllables", "words"), default="syllables")
    ap.add_argument("--levels", type=int, nargs="+", default=list(LEVELS))
    ap.add_argument("--seeds", type=int, nargs="+", default=list(SEEDS))
    pick = ap.add_mutually_exclusive_group()
    pick.add_argument("--gonogo", action="store_true", help="the 50 go/no-go sentences (de dev)")
    pick.add_argument("--ids", nargs="+", help="FLEURS sentence ids")
    ap.add_argument("--limit", type=int, help="first N sentences in file order")
    ap.add_argument("--exclude-gonogo", action="store_true", help="skip the 50 go/no-go sentences")
    ap.add_argument("--quantisation", help="quantisation of the served model, recorded in config.json")
    ap.add_argument("--mock", action="store_true", help="dry run without an LLM")
    ap.add_argument("--allow-test", action="store_true", help="the test split is for final numbers only")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args(argv)

    if args.split == "test" and not args.allow_test:
        sys.exit("the test split is for final numbers only; pass --allow-test to use it")
    if args.gonogo and (args.lang, args.split) != ("de", "dev"):
        sys.exit("the go/no-go sentences are German dev sentences")
    if not args.mock and not args.quantisation:
        sys.exit("--quantisation is required, so the run records what was served")

    data = Path(f"data/fleurs_{args.lang}_{args.split}.jsonl")
    records = list(read_jsonl(data, SentenceRecord))
    selection = "all sentences in file order"
    if args.gonogo:
        wanted = set(gonogo_ids())
        records = [r for r in records if r.id in wanted]
        selection = "the 50 go/no-go sentences"
    elif args.ids:
        records = [r for r in records if r.id in set(args.ids)]
        selection = f"ids {' '.join(args.ids)}"
    if args.exclude_gonogo:
        excluded = set(gonogo_ids())
        records = [r for r in records if r.id not in excluded]
        selection += ", excluding the go/no-go sentences"
    if args.limit:
        records = records[: args.limit]
        selection += f", first {args.limit}"
    if not records:
        sys.exit("no sentences selected")

    client = None
    backend: dict[str, Any] = {"type": "none (mock)"}
    extra: dict[str, Any] = {}
    if not args.mock:
        try:
            config = LLMConfig.from_env()
        except ConfigError as e:
            sys.exit(f"{e}; use --mock for a dry run")
        check_endpoint(config)
        backend = backend_info(config)
        if backend["type"] == "llama.cpp llama-server":
            extra = {"samplers": LLAMACPP_SAMPLERS}
        client = ChatClient(config, timeout=120)

    counter = default_counter()
    prompt = Prompt.load(f"shorten_{args.unit}_v1")
    started = datetime.now(timezone.utc)
    name = f"{started:%Y%m%dT%H%M%SZ}_step{STEP}_{args.lang}_{args.split}_{args.unit}" + ("_mock" if args.mock else "")
    out = args.out or Path("results/raw") / name
    out.mkdir(parents=True, exist_ok=False)

    run_config = {
        "date": started.isoformat(timespec="seconds"),
        "git_commit": git_commit(),
        "step": STEP,
        "task": "shorten a FLEURS reference sentence in the same language",
        "lang": args.lang,
        "split": args.split,
        "unit": args.unit,
        "levels": args.levels,
        "seeds": args.seeds,
        "mock": args.mock,
        "model": "mock (word-prefix cuts, no LLM)" if args.mock else config.name,
        "quantisation": "n/a (mock)" if args.mock else args.quantisation,
        "endpoint": "none (mock)" if args.mock else config.base_url,
        "generation": {**GENERATION, **extra},
        "backend": backend,
        "candidates_per_request": N_CANDIDATES,
        "prompt": {"name": prompt.name, "version": prompt.version, "sha256": prompt.sha256},
        "length_counter": {"syllables": counter_description(counter), "counter": counter},
        "data": {"file": str(data), "sha256": sha256(data)},
        "items": {"selection": selection, "n": len(records), "ids": [r.id for r in records]},
        "tts": "none",
    }
    (out / "config.json").write_text(json.dumps(run_config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    n_requests = len(records) * len(args.levels) * len(args.seeds)
    print(f"{n_requests} requests ({len(records)} sentences × {len(args.levels)} levels × {len(args.seeds)} seeds) → {out}")
    with open(out / "candidates.jsonl", "w", encoding="utf-8") as f:
        for seed in args.seeds:
            for r in records:
                n_in = length(r.ref_text, args.unit, args.lang, counter)
                for level in args.levels:
                    goal = target(level, n_in)
                    text = prompt.render(args.lang, goal, r.ref_text)
                    t0 = time.monotonic()
                    timings = None
                    if args.mock:
                        raw, finish, usage, model = mock_answer(r.ref_text, args.unit, args.lang, goal, seed, counter), "stop", {}, "mock"
                    else:
                        res = client.chat([{"role": "user", "content": text}], seed=seed, **GENERATION, **extra)
                        raw, finish, usage, model = res.text, res.finish_reason, res.usage, res.model
                        timings = res.raw.get("timings")  # llama-server: prompt/predicted tokens and speed
                    cands, error = parse_candidates(raw)
                    f.write(json.dumps({
                        "id": r.id, "lang": args.lang, "split": args.split, "unit": args.unit,
                        "level": level, "seed": seed, "input": r.ref_text, "input_len": n_in, "target": goal,
                        "prompt": text, "raw": raw, "candidates": cands, "parse_error": error,
                        "finish_reason": finish, "usage": usage, "timings": timings, "model": model,
                        "latency_s": round(time.monotonic() - t0, 3),
                    }, ensure_ascii=False) + "\n")
                    f.flush()
    if client:
        client.close()
    print(f"wrote {out / 'candidates.jsonl'}")


if __name__ == "__main__":
    main()
