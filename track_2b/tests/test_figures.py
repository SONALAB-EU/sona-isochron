"""make figures: the parsers read the committed reports, the inputs must be committed, and the figures draw."""

from __future__ import annotations

import struct
from pathlib import Path

import pytest

from isochron import figures


def test_ci_reads_a_value_and_its_interval() -> None:
    assert figures.ci("34.9 [32.5, 37.3]") == (34.9, 32.5, 37.3)
    assert figures.ci("-1.5 [-5.6, 2.5]") == (-1.5, -5.6, 2.5)
    with pytest.raises(ValueError):
        figures.ci("34.9")


def test_tables_read_the_committed_reports() -> None:
    step2 = figures.tables(figures.STEP2)
    de90 = {r["Repair loop"]: r for r in step2["DE: level 90 %"]}
    assert figures.ci(de90["without"]["Fit & complete"]) == (8.5, 6.3, 10.8)
    assert figures.ci(de90["with"]["Fit & complete"]) == (65.1, 61.4, 68.8)
    step4 = figures.tables(figures.STEP4)
    plain = step4["EN → FR, isosyllabic budget (syllables)"][0]
    assert plain["System"] == "(a) plain translation" and figures.ci(plain["Fit ±10 %"])[0] == 60.7
    judge = next(rows for rows in figures.tables(figures.JUDGE_14B).values() if rows and "Control" in rows[0])
    assert {r["Control"]: r["All"] for r in judge}["qualifier_changed"] == "50 % (7/14)"


def test_inputs_must_be_committed() -> None:
    assert all(line.startswith("# ") for line in figures.provenance(figures.INPUTS))
    with pytest.raises(SystemExit, match="committed"):
        figures.provenance((Path("results/no_such_report.md"),))


def test_every_figure_is_drawn_one_column_wide(tmp_path: Path) -> None:
    pytest.importorskip("matplotlib")
    figures.main(["--out", str(tmp_path)])
    names = ("fig1_pipeline", "fig2_compression", "fig3_ratio_histogram", "fig4_step4", "fig5_judges")
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted(f"{n}.{ext}" for n in names for ext in ("csv", "pdf", "png"))
    for name in names:
        png = (tmp_path / f"{name}.png").read_bytes()
        width = struct.unpack(">I", png[16:20])[0]
        assert width == round(figures.WIDTH * 300), f"{name}: {width} px"
        assert (tmp_path / f"{name}.csv").read_text(encoding="utf-8").startswith("# drawn by isochron.figures")
    rows = [line for line in (tmp_path / "fig2_compression.csv").read_text(encoding="utf-8").splitlines()
            if not line.startswith("#")]
    assert len(rows) == 1 + 2 * 4 * 2  # header + languages × levels × conditions
    # the committed figures show the committed results: same numbers in every CSV (run make figures if not)
    committed = Path(__file__).resolve().parents[1] / "docs" / "figures"

    def data(path: Path) -> list[str]:
        return [line for line in path.read_text(encoding="utf-8").splitlines() if not line.startswith("#")]

    for name in names:
        assert data(committed / f"{name}.csv") == data(tmp_path / f"{name}.csv"), f"{name}: run make figures"
