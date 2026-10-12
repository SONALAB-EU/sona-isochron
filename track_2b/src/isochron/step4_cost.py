"""results/step4_test_cost.md: what a step 4 line costs, per system, from the logged runs (isochron.step4).

A line is one output: for (a), one translation per item, which serves both budgets; for (b) and (c), one per
item and budget. (c) includes the (a) translation it starts from; "(c), shortening only" leaves it out.

Measured (sums over a line's logged LLM calls, then means over lines):
- LLM calls, and LLM seconds: each call's wall-clock latency at the client (llm.latency_s). The jobs kept 16
  items in flight on one H100, so a call's latency includes waiting for the shared server.
- Prompt and completion tokens (llm.usage).
- Loop evaluation seconds, for (c) only: the time each round spent checking its candidates (rounds[].nli_s).
  That is the NLI on the same H100, eSpeak and the language check on the CPU, and waiting for the NLI,
  which one worker uses at a time.
- The generation window per language: from the Apertus server being healthy to its stop, as the job log
  records them; given on the command line.

Estimated: H100-seconds per line. Only each language's window is measured. It is shared out over the lines
in proportion to a weight, by two rules, and both are reported because they differ a lot:
- worker time: LLM seconds plus loop evaluation seconds, what kept the 16 workers busy;
- completion tokens: the LLM's decode work (the NLI's GPU work is left out).
Under both rules the shares of (a), (b) and (c)'s shortening add up to the window.

    uv run python -m isochron.step4_cost RUN_DIR... --window de=1689 --window fr=1207 --out results/step4_test_cost.md
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from isochron.pilot_report import short
from isochron.provenance import git_commit

FIELDS = ("calls", "llm_s", "prompt_tokens", "completion_tokens", "eval_s")
SYSTEMS = {"a": "(a) plain translation", "b": "(b) one step to the budget", "c": "(c) translate, then shorten",
           "c_short": "(c), shortening only"}
RULES = {"worker time": lambda line: line["llm_s"] + line["eval_s"], "completion tokens": lambda line: line["completion_tokens"]}


def calls(llms: list[dict[str, Any]], eval_s: float = 0.0) -> dict[str, float]:
    return {"calls": len(llms), "llm_s": sum(c["latency_s"] for c in llms),
            "prompt_tokens": sum(c["usage"]["prompt_tokens"] for c in llms),
            "completion_tokens": sum(c["usage"]["completion_tokens"] for c in llms), "eval_s": eval_s}


def lines(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One record per line, and one per (c) shortening, with its measured sums."""
    out = []
    for it in items:
        base = {"lang": it["lang"], "id": it["id"], "seed": it["seed"]}
        a = calls([t["llm"] for t in it["a"]["tries"]])
        out.append({**base, "budget": "both", "system": "a", **a})
        for kind, entry in it["budgets"].items():
            out.append({**base, "budget": kind, "system": "b", **calls([entry["b"]["llm"]])})
            rounds = entry["c"]["loop"]["rounds"] if entry["c"].get("loop") else []
            shortening = calls([r["llm"] for r in rounds], sum(r["nli_s"] for r in rounds))
            out.append({**base, "budget": kind, "system": "c_short", **shortening})
            out.append({**base, "budget": kind, "system": "c", **{f: a[f] + shortening[f] for f in FIELDS}})
    return out


def apportion(records: list[dict[str, Any]], windows: dict[str, float]) -> dict[str, dict[str, float]]:
    """H100-seconds per weight unit, per rule and language: the window over the weights of (a), (b) and (c)'s
    shortening, which together are everything the window ran."""
    factors: dict[str, dict[str, float]] = {}
    for rule, weight in RULES.items():
        factors[rule] = {}
        for lang, window in windows.items():
            total = sum(weight(r) for r in records if r["lang"] == lang and r["system"] in ("a", "b", "c_short"))
            factors[rule][lang] = window / total
    for r in records:
        for rule, weight in RULES.items():
            r[f"h100_s ({rule})"] = factors[rule][r["lang"]] * weight(r)
    return factors


def table(records: list[dict[str, Any]], title: str) -> list[str]:
    out = [f"### {title}", "",
           "| System | Lines | LLM calls | LLM seconds | Prompt / completion tokens | Loop evaluation s "
           "| H100-s, worker time (estimate) | H100-s, completion tokens (estimate) |",
           "|--------|------:|----------:|------------:|---------------------------:|------------------:"
           "|-------------------------------:|------------------------------------:|"]
    for system, name in SYSTEMS.items():
        rs = [r for r in records if r["system"] == system]
        if not rs:
            continue

        def m(field: str, fmt: str = "{:.2f}") -> str:
            return fmt.format(np.mean([r[field] for r in rs]))

        out.append(f"| {name} | {len(rs)} | {m('calls')} | {m('llm_s')} "
                   f"| {m('prompt_tokens', '{:.0f}')} / {m('completion_tokens', '{:.0f}')} "
                   f"| {m('eval_s') if system.startswith('c') else '–'} | {m('h100_s (worker time)', '{:.3f}')} "
                   f"| {m('h100_s (completion tokens)', '{:.3f}')} |")
    return out


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Step 4: cost per line, from the logged runs.")
    ap.add_argument("runs", type=Path, nargs="+")
    ap.add_argument("--window", action="append", required=True, metavar="LANG=SECONDS",
                    help="the generation window on the H100 for one language, from the job log")
    ap.add_argument("--out", type=Path, default=Path("results/step4_test_cost.md"))
    args = ap.parse_args(argv)
    windows = {k: float(v) for k, v in (w.split("=", 1) for w in args.window)}
    cfgs = [json.loads((run / "config.json").read_text(encoding="utf-8")) for run in args.runs]
    items = [json.loads(line) for run in args.runs
             for line in (run / "items.jsonl").read_text(encoding="utf-8").splitlines() if line]
    if {it["lang"] for it in items} != set(windows):
        raise SystemExit(f"give one --window per language: {sorted({it['lang'] for it in items})}")
    records = lines(items)
    factors = apportion(records, windows)
    cfg = cfgs[0]
    n_items = defaultdict(int)
    for it in items:
        n_items[it["lang"]] += 1
    out = [
        "# Step 4 on test: cost per line",
        "",
        f"- Date: {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC",
        f"- Git commit (report): {git_commit()}; runs: "
        + ", ".join(f"`{run.name}` ({short(c['git_commit'])})" for run, c in zip(args.runs, cfgs)),
        f"- Model: {cfg['model']}, quantisation {cfg['quantisation']}, backend "
        f"{cfg['backend'].get('build_info', cfg['backend'].get('type'))}, one H100 per language, 16 items in "
        f"flight; endpoint " + ", ".join(f"{'/'.join(c['langs'])} {c['endpoint']}" for c in cfgs),
        f"- Seeds {cfg['seeds']}; items " + json.dumps(dict(sorted(n_items.items()))) + "; TTS: none",
        "- Generation windows (measured, from the job logs: server healthy to server stopped; server start and "
        "judging excluded): " + ", ".join(f"{lang} {s:,.0f} s" for lang, s in sorted(windows.items())),
        "- Calls, seconds and tokens are measured. H100-seconds per line are an estimate: each window shared out by "
        "one of two rules (module docstring).",
        "",
        "A line is one output; (c) includes the (a) translation it starts from. Means per line.",
        "",
    ]
    groups = [(f"{lang.upper()}, {kind} budget", [r for r in records if r["lang"] == lang and r["budget"] in (kind, "both")])
              for lang in sorted(windows) for kind in sorted({r["budget"] for r in records} - {"both"})]
    for title, rs in [*groups, ("All languages and budgets", records)]:
        out += table(rs, title) + [""]
    shares = []
    for rule in RULES:
        for lang in sorted(windows):
            parts = {s: factors[rule][lang] * sum(RULES[rule](r) for r in records if r["lang"] == lang and r["system"] == s)
                     for s in ("a", "b", "c_short")}
            shares.append(f"{rule}, {lang.upper()}: " + " / ".join(f"{100 * v / windows[lang]:.1f} %" for v in parts.values()))
    out += ["Share of each window for (a) / (b) / (c)'s shortening, by rule: " + "; ".join(shares) + ".", ""]
    args.out.write_text("\n".join(out), encoding="utf-8")
    print("\n".join(out))
    print(f"wrote {args.out.resolve()}")


if __name__ == "__main__":
    main()
