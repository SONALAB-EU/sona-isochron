"""`make figures`: the report's figures, drawn from committed results files only.

Inputs (each must be tracked by git and unchanged; the run stops otherwise):
- results/step4_test.md            figure 2: step 4 on test, fit per system and budget;
                                   figure 4: fit gained and meaning lost against plain translation (paired)
- results/hpc_8b_step4_dev.md      figure 2: step 4 on dev (exploratory), fit, as markers
- results/step4_test_lengths.csv   figure 3: step 4 output length ÷ budget of every output, per system
- results/step4_test_nli2.md       figure 4: meaning lost under the second NLI (paired)
- results/step2_test.md            figure 5: step 2, fit & complete per level, with the 95 % intervals
- results/step2_test_rounds.csv    figure 6: fit & complete after each round of the loop (with
  results/step2_test_rounds.md     the report that names the runs behind it)
- results/step2_test_lengths.csv   extra_step2_lengths: achieved ÷ target syllables of every step 2 output
- results/judge_validation_hard_v3_all.md, results/judge_validation_hard_v3_qwen3-14b_hpc_8b.md
                                   extra_judges: what the NLI and the two judges catch on the hard controls
Figure 1, the pipeline, is drawn from the description in this file. Figures 1-6 are in technical_report.md;
the two extra_ figures are linked from it, not inserted.

Output, in --out (default docs/figures/): figN_<name>.pdf (vector), .png (300 dpi) and .csv (the numbers
behind the figure; its # lines name each input, its git blob and the commit that last changed it).
The files carry no timestamps, so unchanged inputs give the same figures.

Style: the Okabe & Ito colour-blind-safe palette, with one colour for "without the loop" and one for "with
the loop" in every figure; lines and markers differ too. Every figure is 3.5 in wide (one column), with
text of 6 to 8.5 pt.

    uv run --group figures python -m isochron.figures [--out docs/figures]
"""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
STEP2 = Path("results/step2_test.md")
LENGTHS = Path("results/step2_test_lengths.csv")
ROUNDS_CSV = Path("results/step2_test_rounds.csv")
ROUNDS_MD = Path("results/step2_test_rounds.md")
STEP4 = Path("results/hpc_8b_step4_dev.md")
STEP4_TEST = Path("results/step4_test.md")
STEP4_LENGTHS = Path("results/step4_test_lengths.csv")
STEP4_NLI2 = Path("results/step4_test_nli2.md")
JUDGE_8B = Path("results/judge_validation_hard_v3_all.md")
JUDGE_14B = Path("results/judge_validation_hard_v3_qwen3-14b_hpc_8b.md")
INPUTS = (STEP4_TEST, STEP4, STEP4_LENGTHS, STEP4_NLI2, STEP2, LENGTHS, ROUNDS_CSV, ROUNDS_MD, JUDGE_8B, JUDGE_14B)

WITHOUT = "#E69F00"  # Okabe & Ito orange: without the repair loop, in every figure
WITH = "#0072B2"  # Okabe & Ito blue: with the repair loop (our method), in every figure
PLAIN = "#999999"  # grey: plain translation, no length instruction
NLI_COLOUR, J8_COLOUR, J14_COLOUR = "#333333", "#CC79A7", "#009E73"  # grey is plain translation
LEVEL_COLOURS = {90: "#9ECAE1", 80: "#6BAED6", 70: "#2171B5", 60: "#08306B"}  # ColorBrewer Blues: all with the loop
LEVEL_MARKERS = {90: "o", 80: "s", 70: "^", 60: "D"}
WIDTH = 3.5  # inches: one column
LEVELS = (90, 80, 70, 60)
LANGS = {"DE": "German", "FR": "French"}
CI = re.compile(r"([+-]?\d+(?:\.\d+)?) \[([+-]?\d+(?:\.\d+)?), ([+-]?\d+(?:\.\d+)?)\]")
SHARE = re.compile(r"(\d+) % \((\d+)/(\d+)\)")


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()


def provenance(paths: tuple[Path, ...]) -> list[str]:
    """# lines for a CSV. Stops unless every input is tracked by git and unchanged."""
    if paths:
        try:
            git("ls-files", "--error-unmatch", *map(str, paths))
        except (OSError, subprocess.CalledProcessError):
            sys.exit("isochron.figures reads committed results files only: " + ", ".join(map(str, paths))
                     + " must be tracked by git")
        if git("status", "--porcelain", "--", *map(str, paths)):
            sys.exit("isochron.figures: commit the inputs first; uncommitted changes in "
                     + ", ".join(map(str, paths)))
    code = git("log", "-1", "--format=%h", "--", "src/isochron/figures.py") or "uncommitted"
    if git("status", "--porcelain", "--", "src/isochron/figures.py"):
        code += " (with uncommitted changes)"
    lines = [f"# drawn by isochron.figures (code last changed in commit {code})"]
    for p in paths:
        blob = git("ls-files", "-s", str(p)).split()[1]
        last = git("log", "-1", "--format=%h (%cI)", "--", str(p))
        lines.append(f"# input {p}: blob {blob[:12]}, last changed in commit {last}")
    if paths:
        lines.append("# date, model, quantisation, endpoint, seeds and n of each run: see the input's header")
    return lines


def write_csv(path: Path, inputs: tuple[Path, ...], fields: list[str], rows: list[dict]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        for line in provenance(inputs):
            f.write(line + "\n")
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def tables(path: Path) -> dict[str, list[dict[str, str]]]:
    """The first markdown table under each heading of a report: heading -> rows (column -> cell)."""
    out: dict[str, list[dict[str, str]]] = {}
    lines, heading, i = (ROOT / path).read_text(encoding="utf-8").splitlines(), "", 0
    while i < len(lines):
        if lines[i].startswith("#"):
            heading = lines[i].lstrip("#").strip()
        elif (lines[i].startswith("|") and i + 1 < len(lines)
              and set(lines[i + 1].replace("|", "").strip()) <= set("-: ")):
            header = [c.strip() for c in lines[i].strip().strip("|").split("|")]
            rows = []
            i += 2
            while i < len(lines) and lines[i].startswith("|"):
                rows.append(dict(zip(header, (c.strip() for c in lines[i].strip().strip("|").split("|")))))
                i += 1
            out.setdefault(heading, rows)
            continue
        i += 1
    return out


def ci(cell: str) -> tuple[float, float, float]:
    m = CI.fullmatch(cell)
    if not m:
        raise ValueError(f"not a value with an interval: {cell!r}")
    return float(m.group(1)), float(m.group(2)), float(m.group(3))


def style() -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({
        "font.family": "Inter Display", "font.size": 8, "axes.titlesize": 8.5, "axes.labelsize": 8,
        "xtick.labelsize": 7.5, "ytick.labelsize": 7.5, "legend.fontsize": 7, "legend.frameon": False,
        "axes.spines.top": False, "axes.spines.right": False, "axes.linewidth": 0.6,
        "xtick.major.width": 0.6, "ytick.major.width": 0.6, "lines.linewidth": 1.3, "errorbar.capsize": 2,
        "pdf.fonttype": 42, "svg.hashsalt": "isochron", "figure.dpi": 100,
    })


def save(fig, out: Path, name: str) -> list[Path]:
    paths = [out / f"{name}.pdf", out / f"{name}.png"]
    fig.savefig(paths[0], metadata={"CreationDate": None, "ModDate": None, "Producer": None, "Creator": None})
    fig.savefig(paths[1], dpi=300, metadata={"Software": None})
    import matplotlib.pyplot as plt

    plt.close(fig)
    return paths


def ratio_bins(low: float, high: float) -> np.ndarray:
    """Bins 0.04 wide whose edges fall on 0.90 and 1.10, the ±10 % band, so that the middle bin of the band is
    centred on 1.0 (outputs exactly on target sit there, not in a bin above the target)."""
    return np.round(np.arange(low, high + 1e-9, 0.04), 2)


def in_bins(ratios, edges: np.ndarray) -> np.ndarray:
    """Ratios ready for np.histogram over edges: clipped to the range, and a ratio of exactly 1.10 (which fits)
    moved just below the band's upper edge, since histogram bins are closed on the left."""
    r = np.asarray(ratios, dtype=float)
    r = np.where(r > 1.0, r - 1e-9, r)
    return np.clip(r, edges[0], edges[-1] - 1e-9)


def fig1_pipeline(out: Path) -> list[Path]:
    """The engine (the repair loop), inside the offline deployment of `make run-offline`."""
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

    fig, ax = plt.subplots(figsize=(WIDTH, 3.9), layout="constrained")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 112)
    ax.axis("off")

    def box(x, y, w, h, text, fc="white", ec="#333333", ls="-", lw=0.8, size=6.8, r=1.5):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}", fc=fc, ec=ec,
                                    ls=ls, lw=lw))
        if text:
            ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=size, linespacing=1.25)

    def arrow(p, q, color="#333333", rad=0.0):
        ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=7, color=color, lw=0.9,
                                     connectionstyle=f"arc3,rad={rad}", shrinkA=0, shrinkB=0))

    def note(x, y, text, color="#333333", ha="center"):
        ax.text(x, y, text, ha=ha, va="center", fontsize=6.3, color=color, linespacing=1.15)

    # the offline deployment: two containers without network interfaces, sharing only the loopback
    box(1, 1, 98, 110, "", fc="none", ec="#555555", ls=(0, (3, 2)), lw=0.9, r=2.5)
    ax.text(50, 107, "make run-offline: no network (network_mode: none)", ha="center", va="center",
            fontsize=7.2, weight="bold")
    note(50, 102.3, "the two containers share only the loopback interface, 127.0.0.1", color="#444444")
    box(3, 4, 55, 94, "", fc="#F4F4F4", ec="#BBBBBB", lw=0.6)
    note(30.5, 94.5, "app container (CPU)", color="#444444")
    box(62, 44, 35, 54, "", fc="#F4F4F4", ec="#BBBBBB", lw=0.6)
    note(79.5, 93, "llama-server\ncontainer", color="#444444")
    box(65, 49, 29, 38, "Apertus 1.5\n(GGUF, mounted\nread-only)\n\nasked for\n4 candidates\nper prompt",
        size=6.6)

    # the method: prompt v1 to Apertus, checks on its candidates, revisions with feedback (blue: the loop)
    box(6, 80, 49, 9, "Line + target level, e.g. 80 %")
    box(6, 66, 49, 9, "Target T = level × syllables\nof the line (eSpeak NG)")
    box(6, 45, 49, 16, "Check every candidate\n• length: ±10 % of T\n• meaning: NLI, both ways\n"
        "• language: py3langid")
    box(6, 27, 49, 12, "Best candidate passes?\nIf not, and rounds are left:\nrevise with feedback (≤ 2)",
        fc="#E8F1F8", ec=WITH)
    box(6, 7, 49, 13, "Output: the best candidate\nover all rounds, with its\nsyllables and checks")
    arrow((30.5, 80), (30.5, 75))
    arrow((55, 70.5), (65, 74))
    arrow((65, 60), (55, 55))
    arrow((30.5, 45), (30.5, 39))
    arrow((30.5, 27), (30.5, 20))
    note(32, 23.5, "yes, or no\nrounds left", ha="left")
    arrow((55, 33), (72, 49), color=WITH, rad=0.25)
    note(77, 34, "revision\nprompt", color=WITH)

    rows = [
        {"kind": "box", "name": "deployment", "label": "make run-offline: no network (network_mode: none)", "to": ""},
        {"kind": "box", "name": "app", "label": "app container (CPU)", "to": ""},
        {"kind": "box", "name": "llm", "label": "llama-server container: Apertus 1.5, GGUF mounted read-only", "to": ""},
        {"kind": "step", "name": "input", "label": "line + target level", "to": "target"},
        {"kind": "step", "name": "target", "label": "T = level × the line's syllables (eSpeak NG)", "to": "llm"},
        {"kind": "step", "name": "llm", "label": "Apertus 1.5: asked for 4 candidates per prompt", "to": "checks"},
        {"kind": "step", "name": "checks", "label": "length within ±10 % of T; meaning both ways (NLI); "
                                                     "language (py3langid)", "to": "decision"},
        {"kind": "step", "name": "decision", "label": "best candidate passes? if not and rounds are left: "
                                                       "revision prompt with the feedback (at most 2)", "to": "llm|output"},
        {"kind": "step", "name": "output", "label": "the best candidate over all rounds", "to": ""},
    ]
    write_csv(out / "fig1_pipeline.csv", (), ["kind", "name", "label", "to"], rows)
    return save(fig, out, "fig1_pipeline")


def fig3_step4_lengths(out: Path) -> list[Path]:
    """Step 4 on test: output length ÷ budget of (a), (b) and (c), per language and ruler, with the ±10 % band."""
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    with open(ROOT / STEP4_LENGTHS, encoding="utf-8") as f:
        data = [r for r in csv.DictReader(line for line in f if not line.startswith("#"))]
    edges = ratio_bins(0.42, 1.78)
    systems = (("a", "(a) plain translation", PLAIN, ":"), ("b", "(b) one step to the budget (no loop)", WITHOUT, "--"),
               ("c", "(c) ours: translate, then shorten with the loop", WITH, "-"))
    rulers = (("isometric", "characters"), ("isosyllabic", "syllables"))
    fig, axes = plt.subplots(2, 2, figsize=(WIDTH, 3.05), sharex=True, sharey=True, layout="constrained")
    rows = []
    for i, lang in enumerate(LANGS):
        for j, (budget, ruler) in enumerate(rulers):
            ax = axes[i, j]
            ax.axvspan(0.9, 1.1, color="#E5E5E5", lw=0)
            fits = []
            for system, label, colour, ls in systems:
                rs = [r for r in data if r["lang"] == lang.lower() and r["budget"] == budget and r["system"] == system]
                ratios = in_bins([float(r["ratio"]) for r in rs if r["ratio"]], edges)
                counts = np.histogram(ratios, bins=edges)[0]
                ax.hist(ratios, bins=edges, weights=np.full(len(ratios), 100 / len(rs)), histtype="step", color=colour,
                        ls=ls, lw=1.3 if system == "c" else 1.1, label=label)
                fits.append(100 * sum(r["fit"] == "1" for r in rs) / len(rs))
                rows += [{"lang": lang.lower(), "ruler": ruler, "system": system, "bin_from": f"{a:.2f}",
                          "bin_to": f"{b:.2f}", "outputs": int(n), "pct_of_all_outputs": round(100 * n / len(rs), 3)}
                         for a, b, n in zip(edges[:-1], edges[1:], counts)]
            ax.axvline(1.0, color="#555555", lw=0.6)
            ax.set_title(f"{LANGS[lang]}, {ruler}")
            ax.text(0.97, 0.96, "fit\n" + " / ".join(f"{v:.0f}" for v in fits) + " %", transform=ax.transAxes,
                    ha="right", va="top", fontsize=6.2, linespacing=1.1)
            ax.set_xlim(edges[0], edges[-1])
            ax.grid(axis="y", lw=0.4, color="#DDDDDD")
            ax.set_axisbelow(True)
    for ax in axes[1]:
        ax.set_xlabel("Output length ÷ budget")
    for ax in axes[:, 0]:
        ax.set_ylabel("Outputs (%)")
    handles, labels = axes[0, 0].get_legend_handles_labels()
    handles.append(Patch(color="#E5E5E5", lw=0))
    labels.append("fits (±10 %); fit: (a) / (b) / (c)")
    fig.legend(handles, labels, loc="outside lower center", ncol=1, handlelength=1.8)
    write_csv(out / "fig3_step4_lengths.csv", (STEP4_LENGTHS,), list(rows[0]), rows)
    return save(fig, out, "fig3_step4_lengths")


def fig4_tradeoff(out: Path) -> list[Path]:
    """Step 4 on test: fit gained against meaning lost, both over plain translation, per setting, under both NLIs."""
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    test, second = tables(STEP4_TEST), tables(STEP4_NLI2)
    settings = (("DE", "isometric budget (chars)", "DE, characters", "o"),
                ("DE", "isosyllabic budget (syllables)", "DE, syllables", "s"),
                ("FR", "isometric budget (chars)", "FR, characters", "^"),
                ("FR", "isosyllabic budget (syllables)", "FR, syllables", "D"))
    systems = (("b", "one step", WITHOUT), ("c", "ours", WITH))
    panels = (("Main NLI\n(the loop's own)", "main"), ("Second NLI\n(never in the loop)", "second"))
    fig, axes = plt.subplots(1, 2, figsize=(WIDTH, 2.6), sharex=True, sharey=True, layout="constrained")
    rows = []
    for lang, key, name, marker in settings:
        heading = f"EN → {lang}, {key}: paired differences (post-hoc, added after test outputs existed; percentage points)"
        main = {r["Difference"]: r for r in test[heading]}
        other = {r["Difference"]: r for r in second[heading]}
        for system, _, colour in systems:
            pair = f"({system}) − (a)"
            fit = ci(main[pair]["Fit ±10 %"])
            for ax, (_, model) in zip(axes, panels):
                kept = ci(main[pair]["Kept vs reference"] if model == "main" else other[pair]["Kept vs reference: second NLI"])
                lost = (-kept[0], -kept[2], -kept[1])
                ax.errorbar(fit[0], lost[0], xerr=[[fit[0] - fit[1]], [fit[2] - fit[0]]],
                            yerr=[[lost[0] - lost[1]], [lost[2] - lost[0]]], fmt=marker, ms=4.2, color=colour,
                            mfc=colour, mec=colour, elinewidth=0.6, capsize=1.2, zorder=3)
                rows.append({"setting": name, "system": system, "nli": model, "fit_gain": fit[0], "fit_gain_low": fit[1],
                             "fit_gain_high": fit[2], "meaning_lost": lost[0], "meaning_lost_low": lost[1],
                             "meaning_lost_high": lost[2]})
    for ax, (title, _) in zip(axes, panels):
        ax.axhline(0, color="#555555", lw=0.6, zorder=1)
        ax.set_title(title)
        ax.grid(lw=0.4, color="#DDDDDD")
        ax.set_axisbelow(True)
        ax.set_xlabel("Fit gained (points)")
    axes[0].set_ylabel("Meaning lost (points)")
    handles = [Line2D([], [], ls="", marker="s", ms=4.5, color=colour, label=label) for _, label, colour in systems]
    handles += [Line2D([], [], ls="", marker=marker, ms=4, color="#333333", mfc="white", label=name)
                for _, _, name, marker in settings]
    fig.legend(handles=handles, loc="outside lower center", ncol=3, handlelength=1.0, columnspacing=0.9)
    write_csv(out / "fig4_tradeoff.csv", (STEP4_TEST, STEP4_NLI2), list(rows[0]), rows)
    return save(fig, out, "fig4_tradeoff")


def fig5_compression(out: Path) -> list[Path]:
    """Fit & complete per target level, without and with the loop, German and French test."""
    import matplotlib.pyplot as plt

    t = tables(STEP2)
    header = (ROOT / STEP2).read_text(encoding="utf-8")
    sentences = {lang.upper(): int(n) for lang, n in re.findall(r"(\w\w) test: (\d+) sentences", header)}
    rows = []
    for lang in LANGS:
        for level in LEVELS:
            for r in t[f"{lang}: level {level} %"]:
                value, lo, hi = ci(r["Fit & complete"])
                rows.append({"lang": lang.lower(), "level": level, "loop": r["Repair loop"], "outputs": r["Outputs"],
                             "fit_and_complete_pct": value, "ci_low": lo, "ci_high": hi})
    fig, axes = plt.subplots(1, 2, figsize=(WIDTH, 2.35), sharey=True, layout="constrained")
    x = np.arange(len(LEVELS))
    for ax, lang in zip(axes, LANGS):
        for loop, colour, marker, ls, dx, label in (("without", WITHOUT, "o", "--", -0.1, "without the loop"),
                                                     ("with", WITH, "s", "-", 0.1, "with the loop")):
            sel = [r for r in rows if r["lang"] == lang.lower() and r["loop"] == loop]
            y = np.array([r["fit_and_complete_pct"] for r in sel])
            err = np.array([[r["fit_and_complete_pct"] - r["ci_low"] for r in sel],
                            [r["ci_high"] - r["fit_and_complete_pct"] for r in sel]])
            ax.errorbar(x + dx, y, yerr=err, color=colour, marker=marker, ms=3.5, ls=ls, lw=1.3, elinewidth=0.9,
                        label=label)
        ax.set_title(f"{LANGS[lang]}, {sentences[lang]} sentences")
        ax.set_xticks(x, [f"{lv}" for lv in LEVELS])
        ax.set_ylim(0, 80)
        ax.grid(axis="y", lw=0.4, color="#DDDDDD")
        ax.set_axisbelow(True)
    axes[0].set_ylabel("Fit & complete (%)")
    axes[0].legend(loc="upper right", handlelength=2.2)
    fig.supxlabel("Target length (% of the line's syllables)", fontsize=8)
    write_csv(out / "fig5_compression.csv", (STEP2,), list(rows[0]), rows)
    return save(fig, out, "fig5_compression")


def extra_step2_lengths(out: Path) -> list[Path]:
    """Achieved ÷ target syllables of every German test output, without and with the loop."""
    import matplotlib.pyplot as plt

    with open(ROOT / LENGTHS, encoding="utf-8") as f:
        data = [r for r in csv.DictReader(line for line in f if not line.startswith("#"))]
    edges = ratio_bins(0.26, 1.74)
    fig, ax = plt.subplots(figsize=(WIDTH, 2.3), layout="constrained")
    ax.axvspan(0.9, 1.1, color="#E5E5E5", lw=0, label="fits (±10 %)")
    counts = {}
    for loop, colour, ls, label in (("without", WITHOUT, "--", "without the loop"), ("with", WITH, "-", "with the loop")):
        ratios = in_bins([float(r["ratio"]) for r in data if r["lang"] == "de" and r["loop"] == loop and r["ratio"]],
                         edges)
        counts[loop] = (np.histogram(ratios, bins=edges)[0], len(ratios))
        ax.hist(ratios, bins=edges, weights=np.full(len(ratios), 100 / len(ratios)),
                histtype="step", color=colour, ls=ls, lw=1.3, label=label)
    ax.axvline(1.0, color="#555555", lw=0.6)
    ax.set_xlabel("Achieved ÷ target (syllables)")
    ax.set_ylabel("Outputs (%)")
    ax.set_xlim(edges[0], edges[-1])
    ax.set_title("German test, all levels")
    ax.legend(loc="upper left", handlelength=1.8)
    rows = [{"bin_from": f"{a:.2f}", "bin_to": f"{b:.2f}", "outputs_without": int(cw), "outputs_with": int(cl),
             "pct_without": round(100 * cw / counts["without"][1], 3), "pct_with": round(100 * cl / counts["with"][1], 3)}
            for a, b, cw, cl in zip(edges[:-1], edges[1:], counts["without"][0], counts["with"][0])]
    write_csv(out / "extra_step2_lengths.csv", (LENGTHS,), list(rows[0]), rows)
    return save(fig, out, "extra_step2_lengths")


def fig6_rounds(out: Path) -> list[Path]:
    """Fit & complete after round 0, 1 and 2 of the loop, per level, German and French test."""
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    with open(ROOT / ROUNDS_CSV, encoding="utf-8") as f:
        data = [r for r in csv.DictReader(line for line in f if not line.startswith("#"))]
    fig, axes = plt.subplots(1, 2, figsize=(WIDTH, 2.3), sharey=True, layout="constrained")
    x = np.array([0, 1, 2])
    rows = []
    for ax, lang in zip(axes, LANGS):
        for level in ("all", *LEVEL_COLOURS):  # "all levels" first, beneath the levels
            sel = sorted((r for r in data if r["lang"] == lang.lower() and r["level"] == str(level)),
                         key=lambda r: int(r["round"]))
            low = np.array([float(r["fit_complete_low_pct"]) for r in sel])
            style = ({"color": "#000000", "lw": 1.0, "ls": ":", "marker": None, "zorder": 1} if level == "all" else
                     {"color": LEVEL_COLOURS[level], "lw": 1.1, "marker": LEVEL_MARKERS[level], "ms": 3, "zorder": 2})
            ax.plot(x, low, **style)
            rows += [{"lang": lang.lower(), "level": level, "round": int(r["round"]), "items": int(r["items"]),
                      "fit_complete_low_pct": float(r["fit_complete_low_pct"]),
                      "fit_complete_high_pct": float(r["fit_complete_high_pct"])} for r in sel]
        ax.set_title(LANGS[lang])
        ax.set_xticks(x, ["0", "1", "2"])
        ax.set_xlabel("after round")
        ax.set_ylim(0, 80)
        ax.grid(axis="y", lw=0.4, color="#DDDDDD")
        ax.set_axisbelow(True)
    axes[0].set_ylabel("Fit & complete (%)")
    handles = [Line2D([], [], color=LEVEL_COLOURS[lv], marker=LEVEL_MARKERS[lv], ms=3, lw=1.1, label=f"{lv} %")
               for lv in LEVEL_COLOURS] + [Line2D([], [], color="#000000", lw=1.0, ls=":", label="all levels")]
    fig.legend(handles=handles, loc="outside lower center", ncol=5, handlelength=1.4, columnspacing=0.8,
               title="target length (% of the line's syllables)", title_fontsize=7)
    write_csv(out / "fig6_rounds.csv", (ROUNDS_CSV, ROUNDS_MD), list(rows[0]), rows)
    return save(fig, out, "fig6_rounds")


def fig2_step4(out: Path) -> list[Path]:
    """Step 4 on test (final): fit per system and budget, German and French; dev fit (exploratory) as markers."""
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    test, dev = tables(STEP4_TEST), tables(STEP4)
    systems = (("(a) plain translation", "(a) plain translation", PLAIN),
               ("(b) one step to the budget", "(b) one step to the budget (no loop)", WITHOUT),
               ("(c) translate, then shorten", "(c) ours: translate, then shorten with the loop", WITH))
    budgets = (("isometric budget (chars)", "characters"), ("isosyllabic budget (syllables)", "syllables"))
    rows = []
    for lang in LANGS:
        for key, budget in budgets:
            main = {r["System"]: r for r in test[f"EN → {lang}, {key}"]}
            dev_rows = {r["System"]: r for r in dev[f"EN → {lang}, {key}"]}
            for name, _, _ in systems:
                fit, lo, hi = ci(main[name]["Fit ±10 %"])
                rows.append({"lang": lang.lower(), "budget": budget, "system": name, "outputs": main[name]["Outputs"],
                             "fit_pct": fit, "ci_low": lo, "ci_high": hi,
                             "dev_fit_pct": ci(dev_rows[name]["Fit ±10 %"])[0]})
    fig, axes = plt.subplots(1, 2, figsize=(WIDTH, 2.55), sharey=True, layout="constrained")
    x = np.arange(len(budgets))
    w = 0.26
    for ax, lang in zip(axes, LANGS):
        for k, (name, label, colour) in enumerate(systems):
            sel = [next(r for r in rows if r["lang"] == lang.lower() and r["budget"] == b and r["system"] == name)
                   for _, b in budgets]
            y = np.array([r["fit_pct"] for r in sel])
            err = np.array([[r["fit_pct"] - r["ci_low"] for r in sel], [r["ci_high"] - r["fit_pct"] for r in sel]])
            ax.bar(x + (k - 1) * w, y, w, color=colour, label=label, yerr=err,
                   error_kw={"elinewidth": 0.7, "capsize": 1.5})
            ax.scatter(x + (k - 1) * w + 0.07, [r["dev_fit_pct"] for r in sel], marker="D", s=11, facecolor="white",
                       edgecolor="#000000", linewidths=0.7, zorder=3)
        ax.set_title(f"English → {LANGS[lang]}")
        ax.set_xticks(x, [f"{b[:-1]}\nbudget" for _, b in budgets])
        ax.set_ylim(0, 100)
        ax.grid(axis="y", lw=0.4, color="#DDDDDD")
        ax.set_axisbelow(True)
    axes[0].set_ylabel("Lines within ±10 % (%)")
    handles, labels = axes[0].get_legend_handles_labels()
    handles.append(Line2D([], [], marker="D", ms=3.5, ls="", mfc="white", mec="#000000", mew=0.7))
    labels.append("dev (exploratory)")
    fig.legend(handles, labels, loc="outside lower center", ncol=1, handlelength=1.2)
    write_csv(out / "fig2_step4.csv", (STEP4_TEST, STEP4), list(rows[0]), rows)
    return save(fig, out, "fig2_step4")


def extra_judges(out: Path) -> list[Path]:
    """The German hard controls with a German source: what the main NLI and the two judges get right."""
    import matplotlib.pyplot as plt

    def first(path: Path) -> list[dict[str, str]]:
        return next(rows for rows in tables(path).values() if rows and "Control" in rows[0])

    names = {"identity": "identity", "same_meaning": "same meaning", "qualifier_changed": "qualifier changed",
             "modal_changed": "modal changed", "number_changed": "number changed", "fact_inserted": "inserted fact"}
    passes = ("identity", "same_meaning")  # judged correctly = passed as kept; the rest = the change is caught
    j8, j14 = {r["Control"]: r for r in first(JUDGE_8B)}, {r["Control"]: r for r in first(JUDGE_14B)}
    rows = []
    for control in names:
        for scorer, cell in (("NLI", j14[control]["NLI, all"]), ("Qwen3-8B Q4_K_M", j8[control]["All"]),
                             ("Qwen3-14B BF16", j14[control]["All"])):
            m = SHARE.fullmatch(cell)
            rows.append({"control": control, "scorer": scorer, "correct": int(m.group(2)), "pairs": int(m.group(3)),
                         "pct": round(100 * int(m.group(2)) / int(m.group(3)), 1)})
    fig, ax = plt.subplots(figsize=(WIDTH, 2.9), layout="constrained")
    y = np.arange(len(names))[::-1].astype(float)
    y[len(passes):] -= 0.5  # a gap between the rows that should pass and the rows that should be caught
    h = 0.26
    for k, (scorer, label, colour) in enumerate((("NLI", "main NLI (the loop's)", NLI_COLOUR),
                                                 ("Qwen3-8B Q4_K_M", "Qwen3-8B Q4 (pilot, dev)", J8_COLOUR),
                                                 ("Qwen3-14B BF16", "Qwen3-14B BF16 (main judge)", J14_COLOUR))):
        ax.barh(y - (k - 1) * h, [r["pct"] for r in rows if r["scorer"] == scorer], h, color=colour, label=label)
    ax.set_yticks(y, [f"{'passed' if c in passes else 'caught'}: {names[c]} "
                      f"(n = {next(r['pairs'] for r in rows if r['control'] == c)})" for c in names])
    ax.axhline((y[len(passes) - 1] + y[len(passes)]) / 2, color="#999999", lw=0.6)
    ax.set_xlabel("Judged correctly (% of pairs)")
    ax.set_xlim(0, 100)
    fig.suptitle("Hard controls, German source (140 pairs written by Claude)", fontsize=8.5)
    ax.grid(axis="x", lw=0.4, color="#DDDDDD")
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0)
    fig.legend(*ax.get_legend_handles_labels(), loc="outside lower center", ncol=2, handlelength=1.2,
               columnspacing=0.9)
    write_csv(out / "extra_judges.csv", (JUDGE_8B, JUDGE_14B), list(rows[0]), rows)
    return save(fig, out, "extra_judges")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="The report's figures, from committed results files only.")
    ap.add_argument("--out", type=Path, default=Path("docs/figures"))
    args = ap.parse_args(argv)
    provenance(INPUTS)  # stops before drawing anything if an input is not committed
    style()
    args.out.mkdir(parents=True, exist_ok=True)
    for draw in (fig1_pipeline, fig2_step4, fig3_step4_lengths, fig4_tradeoff, fig5_compression, fig6_rounds,
                 extra_step2_lengths, extra_judges):
        for path in draw(args.out):
            print(f"wrote {path}")


if __name__ == "__main__":
    main()
