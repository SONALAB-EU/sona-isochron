"""`make run`: our method, prompt v1 with the repair loop, on a file of lines to shorten.

Input: JSON lines (README.md, "Input and output"). Each line needs:
- id:    a unique string
- lang:  "de" or "fr", the language of the line
- text:  the line to shorten, for example a dubbing translation that is too long for its slot
- level: the target length in % of the line's syllables (1 to 100)
Other fields are ignored.

Output, in --out:
- results.jsonl: one line per input line, in input order (README.md describes the fields)
- summary.md:    how the run was made (date, commit, model, endpoint, settings), one row per line, totals
- raw/<time>/:   the full log of every round, per language and level, exactly as isochron.loop_run writes
                 it for the experiments (config.json and items.jsonl)

The method is the experiments' code (isochron.loop_run.run with variant v1, one seed): Apertus writes 4
candidates; if the best one misses the syllable target by more than 10 %, or the NLI finds information
dropped or added, or it is in the wrong language, Apertus gets one revision prompt with that feedback,
at most twice. The LLM is reached only through LLM_NAME, LLM_BASE_URL and LLM_API_KEY. The NLI and the
language check run on the CPU unless --device says otherwise.

    uv run python -m isochron.app --input data/sample_input.jsonl --out output
    uv run python -m isochron.app --input data/sample_input.jsonl --out output --mock     (dry run, no LLM)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from isochron.language import check as check_language
from isochron.metrics.length import ESPEAK, espeak_available, espeak_version, length

LANGS = ("de", "fr")
ESPEAK_VERSION = "1.52.0"  # the version every result in this repository was counted with
SEED = 0


@dataclass(frozen=True)
class Line:
    """One input line. isochron.loop_run.run reads only id and ref_text of its records."""

    id: str
    lang: str
    ref_text: str
    level: int


def read_lines(path: Path) -> list[Line]:
    lines, seen = [], set()
    for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"{path}:{n}: not JSON ({e})") from None
        missing = [k for k in ("id", "lang", "text", "level") if k not in obj]
        if missing:
            raise ValueError(f"{path}:{n}: missing {', '.join(missing)}")
        line_id, lang, text, level = str(obj["id"]), obj["lang"], obj["text"], obj["level"]
        if line_id in seen:
            raise ValueError(f"{path}:{n}: id {line_id} appears twice")
        if lang not in LANGS:
            raise ValueError(f"{path}:{n}: lang must be one of {', '.join(LANGS)}, not {lang!r}")
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"{path}:{n}: text must be a non-empty string")
        if isinstance(level, bool) or not isinstance(level, int) or not 1 <= level <= 100:
            raise ValueError(f"{path}:{n}: level must be a whole number from 1 to 100, not {level!r}")
        seen.add(line_id)
        lines.append(Line(line_id, lang, text.strip(), level))
    if not lines:
        raise ValueError(f"{path}: no lines")
    return lines


def groups(lines: list[Line]) -> list[tuple[str, int, list[Line]]]:
    """Lines by (language, level), in order of first appearance: each group is one loop_run run."""
    by: dict[tuple[str, int], list[Line]] = {}
    for line in lines:
        by.setdefault((line.lang, line.level), []).append(line)
    return [(lang, level, members) for (lang, level), members in by.items()]


def usable(c: dict[str, Any] | None, lang: str) -> bool:
    """An answer in the right language (the loop's own language check, as the reports count it)."""
    return bool(c) and not check_language(c["text"], lang).wrong


def result(line: Line, it: dict[str, Any], counter: str) -> dict[str, Any]:
    final, r0 = it["final"], it["closest_round0"]
    ok, ok0 = usable(final, line.lang), usable(r0, line.lang)
    return {
        "id": line.id, "lang": line.lang, "level": line.level, "input": line.ref_text,
        "input_syllables": length(line.ref_text, "syllables", line.lang, counter),
        "target_syllables": it["target"],
        "output": final["text"] if final else None,
        "output_syllables": final["syllables"] if final else None,
        "fit": bool(ok and final["hit"]),
        "nli_kept": bool(ok and final["kept"]),
        "language": check_language(final["text"], line.lang).label if final else None,
        "wrong_language": bool(final) and not ok,
        "accepted": it["final_accepted"],
        "revisions": it["revisions"],
        "retries": it.get("retries", 0),
        "round0": {"output": r0["text"] if r0 else None, "output_syllables": r0["syllables"] if r0 else None,
                   "fit": bool(ok0 and r0["hit"]), "nli_kept": bool(ok0 and r0["kept"])},
        "time_s": it["time_total_s"],
    }


def summary(results: list[dict[str, Any]], cfgs: list[dict[str, Any]], args: argparse.Namespace,
            raw_dir: Path, started: datetime) -> str:
    c0, s0 = cfgs[0], cfgs[0]["sessions"][0]
    n = len(results)

    def count(f) -> str:
        return f"{sum(1 for r in results if f(r))}/{n}"

    rows = []
    for r in results:
        out = (r["output"] or "(no output)").replace("|", "\\|")
        rows.append(f"| {r['id']} | {r['level']} % | {r['input_syllables']} → {r['target_syllables']} → "
                    f"{r['output_syllables'] if r['output_syllables'] is not None else '–'} | "
                    f"{'yes' if r['fit'] else 'no'} | {'yes' if r['nli_kept'] else 'no'} | "
                    f"{'yes' if r['round0']['fit'] else 'no'} | {r['revisions']} | {r['time_s']:.1f} | {out} |")
    return "\n".join([
        "# Shortened lines (`make run`)",
        "",
        f"- Date: {started:%Y-%m-%d %H:%M} UTC",
        f"- Git commit: {s0['git_commit']}",
        f"- Model: {c0['model']}, quantisation {c0['quantisation']}, endpoint {c0['endpoint']}, "
        f"backend {json.dumps(c0['backend'], ensure_ascii=False)}",
        f"- Method: prompt `{c0['prompt']['name']}` ({c0['prompt']['sha256'][:12]}) with the repair loop "
        f"(`{c0['revise_prompt']['name']}`, {c0['revise_prompt']['sha256'][:12]}), at most {c0['max_revisions']} "
        "revisions",
        f"- Checks in the loop: syllables by {c0['length_counter']['syllables']}; NLI {c0['nli']}; "
        f"language {c0['language_check']}",
        f"- Generation: {json.dumps(c0['generation'])}; seed {SEED} for round 0, then {c0['round_seed']}",
        f"- Input: `{args.input}` (SHA-256 {c0['data']['sha256'][:12]}), n = {n} lines",
        "- TTS: none",
        f"- Raw logs: `{raw_dir}`" + (" (dry run: no LLM)" if args.mock else ""),
        "",
        "Fit: within ±10 % of the target syllables. NLI kept: the NLI finds entailment in both directions",
        "between the line and the output (the loop's own check, not a final judge). An output in the wrong",
        "language counts as neither. Round 0: the closest of the first 4 candidates, before any revision.",
        "",
        "| Id | Level | Syllables: input → target → output | Fit | NLI kept | Fit at round 0 | Revisions | Time (s) | Output |",
        "|----|------:|-----------------------------------|-----|----------|----------------|----------:|---------:|--------|",
        *rows,
        "",
        f"**Totals:** fit {count(lambda r: r['fit'])} (round 0: {count(lambda r: r['round0']['fit'])}); "
        f"NLI kept {count(lambda r: r['nli_kept'])} (round 0: {count(lambda r: r['round0']['nli_kept'])}); "
        f"fit and kept {count(lambda r: r['accepted'])}; wrong language {count(lambda r: r['wrong_language'])}; "
        f"no output {count(lambda r: r['output'] is None)}; "
        f"{sum(r['revisions'] for r in results) / n:.2f} revisions and "
        f"{sum(r['time_s'] for r in results) / n:.1f} s per line.",
        "",
        "These lines show the method at work; they are not an evaluation. The evaluation is in",
        "`technical_report.md`.",
        "",
    ])


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Shorten lines to a syllable target with Apertus (our method).")
    ap.add_argument("--input", type=Path, default=Path("data/sample_input.jsonl"))
    ap.add_argument("--out", type=Path, default=Path("output"))
    ap.add_argument("--device", default="cpu", help="NLI device (default: cpu)")
    ap.add_argument("--workers", type=int, default=1, help="lines in flight at once (the server must allow it)")
    ap.add_argument("--mock", action="store_true", help="dry run without an LLM: word-prefix cuts of the input")
    args = ap.parse_args(argv)

    try:
        lines = read_lines(args.input)
    except (OSError, ValueError) as e:
        sys.exit(f"isochron.app: {e}")
    if not espeak_available():
        sys.exit(f"isochron.app: {ESPEAK} {ESPEAK_VERSION} is needed to count syllables (the Docker image has it)")
    if ESPEAK_VERSION not in espeak_version():
        print(f"warning: {espeak_version()} is not {ESPEAK_VERSION}; syllable counts can differ from ours",
              file=sys.stderr)
    from isochron.loop_run import run

    started = datetime.now(timezone.utc)
    raw_dir = args.out / "raw" / f"{started:%Y%m%dT%H%M%SZ}"
    quantisation = os.environ.get("LLM_QUANTISATION") or "not reported (set LLM_QUANTISATION to record it)"
    items: dict[str, dict[str, Any]] = {}
    cfgs = []
    for lang, level, members in groups(lines):
        print(f"{lang}, level {level} %: {len(members)} line(s)", flush=True)
        run_dir = run(members, variant="v1", lang=lang, split="n/a (make run input)", levels=[level], seeds=[SEED],
                      out=raw_dir / f"{lang}_L{level}", kind="make run",
                      selection=f"lines of {args.input} with lang {lang} and level {level}", data=args.input,
                      quantisation=quantisation, mock=args.mock, workers=args.workers, device=args.device)
        cfgs.append(json.loads((run_dir / "config.json").read_text(encoding="utf-8")))
        for raw in (run_dir / "items.jsonl").read_text(encoding="utf-8").splitlines():
            it = json.loads(raw)
            items[str(it["id"])] = it
    counter = cfgs[0]["length_counter"]["counter"]
    results = [result(line, items[line.id], counter) for line in lines]
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "results.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in results), encoding="utf-8")
    (args.out / "summary.md").write_text(summary(results, cfgs, args, raw_dir, started), encoding="utf-8")
    digest = hashlib.sha256((args.out / "results.jsonl").read_bytes()).hexdigest()[:12]
    print(f"wrote {args.out / 'results.jsonl'} ({len(results)} lines, SHA-256 {digest}) and {args.out / 'summary.md'}")


if __name__ == "__main__":
    main()
