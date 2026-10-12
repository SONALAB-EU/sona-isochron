"""`make figures`: the report's figures, drawn from committed results files only.

Inputs (each must be tracked by git and unchanged; the run stops otherwise):
- results/step2_test.md            figure 2: fit & complete per level, with the 95 % intervals
- results/step2_test_lengths.csv   figure 3: achieved ÷ target syllables of every output
- results/hpc_8b_step4_dev.md      figure 4: step 4 fit per system and budget
- results/judge_validation_hard_v3_all.md, results/judge_validation_hard_v3_qwen3-14b_hpc_8b.md
                                   figure 5: what the NLI and the two judges catch on the hard controls
Figure 1, the pipeline, is drawn from the description in this file.

Output, in --out (default docs/figures/): figN_<name>.pdf (vector), .png (300 dpi) and .csv (the numbers
behind the figure; its # lines name each input, its git blob and the commit that last changed it).
The files carry no timestamps, so unchanged inputs give the same figures.

Style: the Okabe & Ito colour-blind-safe palette, with one colour for "without the loop" and one for "with
the loop" in every figure; lines and markers differ too. Every figure is 3.5 in wide (one column), with
text of 7 to 8.5 pt.

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
STEP4 = Path("results/hpc_8b_step4_dev.md")
JUDGE_8B = Path("results/judge_validation_hard_v3_all.md")
JUDGE_14B = Path("results/judge_validation_hard_v3_qwen3-14b_hpc_8b.md")
INPUTS = (STEP2, LENGTHS, STEP4, JUDGE_8B, JUDGE_14B)

WITHOUT = "#E69F00"  # Okabe & Ito orange: without the repair loop, in every figure
WITH = "#0072B2"  # Okabe & Ito blue: with the repair loop (our method), in every figure
PLAIN = "#999999"  # grey: plain translation, no length instruction
NLI_COLOUR, J8_COLOUR, J14_COLOUR = "#999999", "#CC79A7", "#009E73"
WIDTH = 3.5  # inches: one column
LEVELS = (90, 80, 70, 60)
LANGS = {"DE": "German", "FR": "French"}
CI = re.compile(r"(-?\d+(?:\.\d+)?) \[(-?\d+(?:\.\d+)?), (-?\d+(?:\.\d+)?)\]")
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
        "font.family": "DejaVu Sans", "font.size": 8, "axes.titlesize": 8.5, "axes.labelsize": 8,
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


def fig1_pipeline(out: Path) -> list[Path]:
    """The method, inside the offline deployment of `make run-offline`."""
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
    box(65, 49, 29, 38, "Apertus 1.5\n(GGUF, mounted\nread-only)\n\nanswers each\nprompt with\n4 candidates",
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
    note(32, 23.5, "yes, or no rounds left", ha="left")
    arrow((55, 33), (72, 49), color=WITH, rad=0.25)
    note(77, 34, "revision\nprompt", color=WITH)

    rows = [
        {"kind": "box", "name": "deployment", "label": "make run-offline: no network (network_mode: none)", "to": ""},
        {"kind": "box", "name": "app", "label": "app container (CPU)", "to": ""},
        {"kind": "box", "name": "llm", "label": "llama-server container: Apertus 1.5, GGUF mounted read-only", "to": ""},
        {"kind": "step", "name": "input", "label": "line + target level", "to": "target"},
        {"kind": "step", "name": "target", "label": "T = level × the line's syllables (eSpeak NG)", "to": "llm"},
        {"kind": "step", "name": "llm", "label": "Apertus 1.5: 4 candidates per prompt", "to": "checks"},
        {"kind": "step", "name": "checks", "label": "length within ±10 % of T; meaning both ways (NLI); "
                                                     "language (py3langid)", "to": "decision"},
        {"kind": "step", "name": "decision", "label": "best candidate passes? if not and rounds are left: "
                                                       "revision prompt with the feedback (at most 2)", "to": "llm|output"},
        {"kind": "step", "name": "output", "label": "the best candidate over all rounds", "to": ""},
    ]
    write_csv(out / "fig1_pipeline.csv", (), ["kind", "name", "label", "to"], rows)
    return save(fig, out, "fig1_pipeline")


def fig2_compression(out: Path) -> list[Path]:
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
        for loop, colour, marker, ls, dx, label in (("without", WITHOUT, "o", "--", -0.06, "without the loop"),
                                                     ("with", WITH, "s", "-", 0.06, "with the loop")):
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
    axes[0].set_ylabel("Fit & every fact kept (%)")
    axes[0].legend(loc="upper right", handlelength=2.2)
    fig.supxlabel("Target length (% of the line's syllables)", fontsize=8)
    write_csv(out / "fig2_compression.csv", (STEP2,), list(rows[0]), rows)
    return save(fig, out, "fig2_compression")


def fig3_ratio_histogram(out: Path) -> list[Path]:
    """Achieved ÷ target syllables of every German test output, without and with the loop."""
    import matplotlib.pyplot as plt

    with open(ROOT / LENGTHS, encoding="utf-8") as f:
        data = [r for r in csv.DictReader(line for line in f if not line.startswith("#"))]
    edges = np.round(np.arange(0.25, 1.75 + 1e-9, 0.05), 2)
    fig, ax = plt.subplots(figsize=(WIDTH, 2.3), layout="constrained")
    ax.axvspan(0.9, 1.1, color="#E5E5E5", lw=0, label="fits (±10 %)")
    counts = {}
    for loop, colour, ls, label in (("without", WITHOUT, "--", "without the loop"), ("with", WITH, "-", "with the loop")):
        ratios = np.array([float(r["ratio"]) for r in data if r["lang"] == "de" and r["loop"] == loop and r["ratio"]])
        counts[loop] = (np.histogram(np.clip(ratios, edges[0], edges[-1] - 1e-9), bins=edges)[0], len(ratios))
        ax.hist(np.clip(ratios, edges[0], edges[-1] - 1e-9), bins=edges, weights=np.full(len(ratios), 100 / len(ratios)),
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
    write_csv(out / "fig3_ratio_histogram.csv", (LENGTHS,), list(rows[0]), rows)
    return save(fig, out, "fig3_ratio_histogram")


def fig4_step4(out: Path) -> list[Path]:
    """Step 4 on dev: fit per system under the character and the syllable budget, German and French."""
    import matplotlib.pyplot as plt

    t = tables(STEP4)
    systems = (("(a) plain translation", "plain translation", PLAIN, ""),
               ("(b) one step to the budget", "one step to the budget (no loop)", WITHOUT, ""),
               ("(c) translate, then shorten", "translate, then shorten with the loop (ours)", WITH, ""))
    budgets = (("isometric budget (chars)", "characters"), ("isosyllabic budget (syllables)", "syllables"))
    rows = []
    for lang in LANGS:
        for key, budget in budgets:
            for r in t[f"EN → {lang}, {key}"]:
                value, lo, hi = ci(r["Fit ±10 %"])
                rows.append({"lang": lang.lower(), "budget": budget, "system": r["System"], "outputs": r["Outputs"],
                             "fit_pct": value, "ci_low": lo, "ci_high": hi})
    fig, axes = plt.subplots(1, 2, figsize=(WIDTH, 2.6), sharey=True, layout="constrained")
    x = np.arange(len(budgets))
    w = 0.26
    for ax, lang in zip(axes, LANGS):
        for k, (name, label, colour, _) in enumerate(systems):
            sel = [next(r for r in rows if r["lang"] == lang.lower() and r["budget"] == b and r["system"] == name)
                   for _, b in budgets]
            y = np.array([r["fit_pct"] for r in sel])
            err = np.array([[r["fit_pct"] - r["ci_low"] for r in sel], [r["ci_high"] - r["fit_pct"] for r in sel]])
            ax.bar(x + (k - 1) * w, y, w, color=colour, label=label, yerr=err, error_kw={"elinewidth": 0.7, "capsize": 1.5})
        ax.set_xticks(x, [f"{b[:-1]}\nbudget" for _, b in budgets])
        ax.set_title(f"English → {LANGS[lang]}")
        ax.set_ylim(0, 112)
        ax.set_yticks(range(0, 101, 20))
        ax.grid(axis="y", lw=0.4, color="#DDDDDD")
        ax.set_axisbelow(True)
    axes[0].set_ylabel("Fit within ±10 % (%)")
    plain = {b: next(r["fit_pct"] for r in rows if r["lang"] == "fr" and r["budget"] == b
                     and r["system"].startswith("(a)")) for _, b in budgets}
    fr_plain_syll = next(r for r in rows if r["lang"] == "fr" and r["budget"] == "syllables"
                         and r["system"].startswith("(a)"))
    axes[1].annotate(f"plain French:\n{plain['characters']:.0f} % with characters,\n"
                     f"{plain['syllables']:.0f} % with syllables", xy=(1 - w, fr_plain_syll["ci_high"] + 1.5),
                     xytext=(0.78, 111.5), fontsize=6.2, ha="center", va="top",
                     arrowprops={"arrowstyle": "-|>", "lw": 0.7, "color": "#333333", "mutation_scale": 6})
    fig.legend(*axes[0].get_legend_handles_labels(), loc="outside lower center", ncol=1, handlelength=1.2)
    write_csv(out / "fig4_step4.csv", (STEP4,), list(rows[0]), rows)
    return save(fig, out, "fig4_step4")


def fig5_judges(out: Path) -> list[Path]:
    """What the NLI and the two judges get right on the hard controls (German)."""
    import matplotlib.pyplot as plt

    def first(path: Path) -> list[dict[str, str]]:
        return next(rows for rows in tables(path).values() if rows and "Control" in rows[0])

    names = {"identity": "identity", "same_meaning": "same\nmeaning", "modal_changed": "modal\nchanged",
             "number_changed": "number\nchanged", "qualifier_changed": "qualifier\nchanged",
             "fact_inserted": "fact\ninserted"}
    j8, j14 = {r["Control"]: r for r in first(JUDGE_8B)}, {r["Control"]: r for r in first(JUDGE_14B)}
    rows = []
    for control in names:
        for scorer, cell in (("NLI", j14[control]["NLI, all"]), ("Qwen3-8B Q4_K_M", j8[control]["All"]),
                             ("Qwen3-14B BF16", j14[control]["All"])):
            m = SHARE.fullmatch(cell)
            rows.append({"control": control, "scorer": scorer, "correct": int(m.group(2)), "pairs": int(m.group(3)),
                         "pct": round(100 * int(m.group(2)) / int(m.group(3)), 1)})
    fig, ax = plt.subplots(figsize=(WIDTH, 2.7), layout="constrained")
    y = np.arange(len(names))[::-1]
    h = 0.26
    for k, (scorer, label, colour) in enumerate((("NLI", "NLI (mDeBERTa)", NLI_COLOUR),
                                                 ("Qwen3-8B Q4_K_M", "Qwen3-8B Q4", J8_COLOUR),
                                                 ("Qwen3-14B BF16", "Qwen3-14B BF16", J14_COLOUR))):
        ax.barh(y - (k - 1) * h, [r["pct"] for r in rows if r["scorer"] == scorer], h, color=colour, label=label)
    labels = {c: names[c].replace("\n", " ") for c in names}
    ax.set_yticks(y, [f"{labels[c]} (n = {next(r['pairs'] for r in rows if r['control'] == c)})" for c in names])
    ax.set_xlabel("Judged correctly (% of pairs)")
    ax.set_xlim(0, 100)
    ax.grid(axis="x", lw=0.4, color="#DDDDDD")
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0)
    fig.legend(*ax.get_legend_handles_labels(), loc="outside lower center", ncol=3, handlelength=1.2,
               columnspacing=0.9)
    write_csv(out / "fig5_judges.csv", (JUDGE_8B, JUDGE_14B), list(rows[0]), rows)
    return save(fig, out, "fig5_judges")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="The report's figures, from committed results files only.")
    ap.add_argument("--out", type=Path, default=Path("docs/figures"))
    args = ap.parse_args(argv)
    provenance(INPUTS)  # stops before drawing anything if an input is not committed
    style()
    args.out.mkdir(parents=True, exist_ok=True)
    for draw in (fig1_pipeline, fig2_compression, fig3_ratio_histogram, fig4_step4, fig5_judges):
        for path in draw(args.out):
            print(f"wrote {path}")


if __name__ == "__main__":
    main()
