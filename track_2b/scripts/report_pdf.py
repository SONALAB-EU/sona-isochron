# /// script
# requires-python = ">=3.11"
# dependencies = ["markdown-it-py==4.2.0", "pypdf==6.20.0"]
# ///
"""Render technical_report.md to PDF and count its pages (the submission allows at most 6).

Markdown → HTML (markdown-it-py: CommonMark, as GitHub renders it, plus tables) → PDF with headless Chrome
or Chromium. The layout is fixed here,
because the page count depends on it:
- A4 with 16 mm margins, two columns 6 mm apart, 9.5 pt text;
- the title block (everything before the first "## ") spans both columns;
- figures fill a column (about 8.6 cm), and each caption stays with its figure;
- a table inside `<div class="wide">` (blank lines around it) spans both columns.

    uv run scripts/report_pdf.py [--out FILE.pdf] [--chrome PATH]

Chrome is looked up at the usual macOS and Linux paths unless --chrome is given.
"""

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from markdown_it import MarkdownIt
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "google-chrome", "chromium",
              "chromium-browser")
CSS = """
@page { size: A4; margin: 16mm; }
body { font-family: "Helvetica Neue", Helvetica, Arial, sans-serif; font-size: 9.5pt; line-height: 1.3; color: #111; }
h1 { font-size: 15pt; margin: 0 0 3pt; } h2 { font-size: 11pt; margin: 8pt 0 2pt; break-after: avoid; }
p { margin: 2.5pt 0; } ul, ol { margin: 1.5pt 0; padding-left: 13pt; } li { margin: 0.8pt 0; }
.cols { column-count: 2; column-gap: 6mm; }
table { border-collapse: collapse; font-size: 7.6pt; margin: 3pt 0; break-inside: avoid; }
th, td { border-bottom: 0.5pt solid #bbb; padding: 1.2pt 3pt; text-align: left; vertical-align: top; }
code { font-size: 8.4pt; } img { display: block; width: 100%; margin: 3pt 0 0; }
p:has(> img) { break-inside: avoid; break-after: avoid; margin: 0; }
p:has(> img) + p { font-size: 8pt; margin: 1pt 0 6pt; break-before: avoid; break-inside: avoid; }
.wide { column-span: all; margin: 2pt 0 4pt; } .wide table { width: 100%; } .wide td { white-space: nowrap; }
"""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--report", type=Path, default=ROOT / "technical_report.md")
    ap.add_argument("--out", type=Path, default=Path(tempfile.gettempdir()) / "technical_report.pdf")
    ap.add_argument("--chrome")
    args = ap.parse_args()
    args.report = args.report.resolve()
    chrome = args.chrome or next((c for c in CANDIDATES if Path(c).exists() or shutil.which(c)), None)
    if not chrome:
        sys.exit("no Chrome or Chromium found: pass --chrome PATH")
    text = args.report.read_text(encoding="utf-8")
    cut = text.index("\n## ")
    md = MarkdownIt("commonmark").enable("table")
    head, rest = md.render(text[:cut]), md.render(text[cut:])
    html = (f'<!doctype html><html><head><meta charset="utf-8"><base href="{args.report.parent.as_uri()}/">'
            f'<style>{CSS}</style></head><body>{head}<div class="cols">{rest}</div></body></html>')
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "report.html"
        page.write_text(html, encoding="utf-8")
        subprocess.run([shutil.which(chrome) or chrome, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                        f"--print-to-pdf={args.out.resolve()}", page.as_uri()], check=True, capture_output=True)
    pages = len(PdfReader(args.out).pages)
    print(f"{args.out}: {pages} pages (A4, two columns, 9.5 pt){'' if pages <= 6 else ' — over the 6-page limit'}")


if __name__ == "__main__":
    main()
