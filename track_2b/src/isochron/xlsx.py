"""A minimal XLSX writer and reader, with the standard library only (for the native-speaker sheet).

The writer makes a workbook of plain sheets: text and whole-number cells in a few fixed styles, column
widths, row heights, a frozen header row, drop-down lists (data validation) and print settings. It writes
no document properties (no author, title or dates), and the same input gives the same bytes.

The reader returns one sheet's cells as text, as Excel, LibreOffice, Numbers and Google Sheets save them
(shared or inline strings, numbers, a formula's cached value).
"""

from __future__ import annotations

import os
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree as ET

MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
DOC_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
XML_HEAD = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
ZIP_TIME = (1980, 1, 1, 0, 0, 0)  # fixed, so the same workbook gives the same bytes

# cell styles (the index is the cell's s attribute, into cellXfs below)
NORMAL, HEADER, TEXT, INPUT, TITLE, BODY, LABEL, NUMBER, NOTE, BOLD = range(10)
STYLES = """<styleSheet xmlns="{main}">
<fonts count="4">
<font><sz val="11"/><name val="Calibri"/><family val="2"/></font>
<font><b/><sz val="11"/><name val="Calibri"/><family val="2"/></font>
<font><b/><sz val="14"/><name val="Calibri"/><family val="2"/></font>
<font><i/><sz val="11"/><name val="Calibri"/><family val="2"/></font>
</fonts>
<fills count="4">
<fill><patternFill patternType="none"/></fill>
<fill><patternFill patternType="gray125"/></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FFDDEBF7"/><bgColor indexed="64"/></patternFill></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FFFFF2CC"/><bgColor indexed="64"/></patternFill></fill>
</fills>
<borders count="2">
<border><left/><right/><top/><bottom/><diagonal/></border>
<border><left style="thin"><color rgb="FFBFBFBF"/></left><right style="thin"><color rgb="FFBFBFBF"/></right>\
<top style="thin"><color rgb="FFBFBFBF"/></top><bottom style="thin"><color rgb="FFBFBFBF"/></bottom><diagonal/></border>
</borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="10">
<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
<xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" \
applyAlignment="1"><alignment vertical="center" wrapText="1"/></xf>
<xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1" applyAlignment="1">\
<alignment vertical="top" wrapText="1"/></xf>
<xf numFmtId="0" fontId="0" fillId="3" borderId="1" xfId="0" applyFill="1" applyBorder="1" applyAlignment="1">\
<alignment vertical="top" wrapText="1"/></xf>
<xf numFmtId="0" fontId="2" fillId="0" borderId="0" xfId="0" applyFont="1"/>
<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="top" \
wrapText="1"/></xf>
<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1" applyAlignment="1">\
<alignment vertical="top" wrapText="1"/></xf>
<xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1" applyAlignment="1">\
<alignment horizontal="center" vertical="top"/></xf>
<xf numFmtId="0" fontId="3" fillId="0" borderId="0" xfId="0" applyFont="1" applyAlignment="1">\
<alignment vertical="top" wrapText="1"/></xf>
<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/>
</cellXfs>
<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>""".replace("{main}", MAIN)
BAD_CHARS = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]")


@dataclass
class Cell:
    value: str | int | None = None
    style: int = NORMAL


@dataclass
class DropDown:
    cells: str  # e.g. "D2:D51"
    options: tuple[str, ...]
    title: str  # shown above the prompt and the error (at most 32 characters)
    prompt: str  # shown when a cell is selected (at most 255 characters)


@dataclass
class Sheet:
    name: str
    rows: list[list[Cell]]  # from A1, row by row
    widths: list[float]  # per column, in characters
    heights: dict[int, float] = field(default_factory=dict)  # row number (from 1) -> points
    freeze_header: bool = False
    gridlines: bool = True
    drop_downs: list[DropDown] = field(default_factory=list)
    landscape: bool = False
    fit_width: bool = False  # print one page wide
    repeat_header: bool = False  # print row 1 on every page


def column(index: int) -> str:
    """0 -> A, 25 -> Z, 26 -> AA."""
    name = ""
    index += 1
    while index:
        index, rest = divmod(index - 1, 26)
        name = chr(65 + rest) + name
    return name


def text(value: str) -> str:
    if BAD_CHARS.search(value):
        raise ValueError(f"a character XML cannot hold, in {value[:40]!r}")
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def attr(value: str) -> str:
    return text(value).replace('"', "&quot;").replace("\n", "&#10;").replace("\r", "&#13;").replace("\t", "&#9;")


def write(path: Path, sheets: list[Sheet]) -> None:
    """Write the workbook; the first sheet is the one shown when it opens."""
    if len({s.name for s in sheets}) != len(sheets) or any(len(s.name) > 31 or re.search(r"[\[\]:*?/\\]", s.name)
                                                           for s in sheets):
        raise ValueError("sheet names must be unique, at most 31 characters, without []:*?/\\")
    strings: dict[str, int] = {}
    uses = 0
    parts: dict[str, str] = {}
    for n, sheet in enumerate(sheets, 1):
        rows_xml = []
        for r, row in enumerate(sheet.rows, 1):
            cells = []
            for c, cell in enumerate(row):
                ref = f"{column(c)}{r}"
                if cell.value is None or cell.value == "":
                    cells.append(f'<c r="{ref}" s="{cell.style}"/>')
                elif isinstance(cell.value, bool) or not isinstance(cell.value, (int, str)):
                    raise TypeError(f"{ref}: only text and whole numbers, not {cell.value!r}")
                elif isinstance(cell.value, int):
                    cells.append(f'<c r="{ref}" s="{cell.style}"><v>{cell.value}</v></c>')
                else:
                    uses += 1
                    index = strings.setdefault(cell.value, len(strings))
                    cells.append(f'<c r="{ref}" s="{cell.style}" t="s"><v>{index}</v></c>')
            height = sheet.heights.get(r)
            ht = f' ht="{height:g}" customHeight="1"' if height else ""
            rows_xml.append(f'<row r="{r}"{ht}>{"".join(cells)}</row>')
        last = f"{column(max(1, max((len(row) for row in sheet.rows), default=1)) - 1)}{max(1, len(sheet.rows))}"
        gridlines = "" if sheet.gridlines else ' showGridLines="0"'
        selected = ' tabSelected="1"' if n == 1 else ""
        view = f'<sheetView workbookViewId="0"{gridlines}{selected}>'
        if sheet.freeze_header:
            view += ('<pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>'
                     '<selection pane="bottomLeft" activeCell="A2" sqref="A2"/>')
        cols = "".join(f'<col min="{i}" max="{i}" width="{w:g}" customWidth="1"/>' for i, w in enumerate(sheet.widths, 1))
        validations = ""
        if sheet.drop_downs:
            items = []
            for d in sheet.drop_downs:
                if len(d.title) > 32 or len(d.prompt) > 255 or len(",".join(d.options)) > 255 \
                        or any("," in o or '"' in o for o in d.options):
                    raise ValueError(f"drop-down {d.cells}: title, prompt or options too long, or a comma or quote")
                items.append(f'<dataValidation type="list" allowBlank="1" showInputMessage="1" showErrorMessage="1" '
                             f'errorTitle="{attr(d.title)}" error="{attr("Please choose from the list: " + ", ".join(d.options) + ".")}" '
                             f'promptTitle="{attr(d.title)}" prompt="{attr(d.prompt)}" sqref="{d.cells}">'
                             f'<formula1>"{text(",".join(d.options))}"</formula1></dataValidation>')
            validations = f'<dataValidations count="{len(items)}">{"".join(items)}</dataValidations>'
        orientation = "landscape" if sheet.landscape else "portrait"
        fit_attrs = ' fitToWidth="1" fitToHeight="0"' if sheet.fit_width else ""
        setup = f'<pageSetup paperSize="9" orientation="{orientation}"{fit_attrs}/>'
        fit = '<sheetPr><pageSetUpPr fitToPage="1"/></sheetPr>' if sheet.fit_width else ""
        parts[f"xl/worksheets/sheet{n}.xml"] = (
            f'{XML_HEAD}<worksheet xmlns="{MAIN}" xmlns:r="{DOC_REL}">{fit}<dimension ref="A1:{last}"/>'
            f'<sheetViews>{view}</sheetView></sheetViews><sheetFormatPr defaultRowHeight="15"/><cols>{cols}</cols>'
            f'<sheetData>{"".join(rows_xml)}</sheetData>{validations}'
            '<pageMargins left="0.5" right="0.5" top="0.6" bottom="0.6" header="0.3" footer="0.3"/>'
            f"{setup}</worksheet>")
    shared = "".join(f'<si><t xml:space="preserve">{text(s)}</t></si>' for s in strings)
    parts["xl/sharedStrings.xml"] = f'{XML_HEAD}<sst xmlns="{MAIN}" count="{uses}" uniqueCount="{len(strings)}">{shared}</sst>'
    parts["xl/styles.xml"] = XML_HEAD + STYLES
    titles = "".join(f'<definedName name="_xlnm.Print_Titles" localSheetId="{i}">{s.name}!$1:$1</definedName>'
                     for i, s in enumerate(sheets) if s.repeat_header)
    if titles and any(not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", s.name) for s in sheets if s.repeat_header):
        raise ValueError("a sheet whose header row repeats needs a plain name (letters, digits, _)")
    parts["xl/workbook.xml"] = (
        f'{XML_HEAD}<workbook xmlns="{MAIN}" xmlns:r="{DOC_REL}"><bookViews><workbookView activeTab="0"/></bookViews>'
        "<sheets>" + "".join(f'<sheet name="{attr(s.name)}" sheetId="{n}" r:id="rId{n}"/>' for n, s in enumerate(sheets, 1))
        + "</sheets>" + (f"<definedNames>{titles}</definedNames>" if titles else "") + "</workbook>")
    k = len(sheets)
    parts["xl/_rels/workbook.xml.rels"] = (
        f'{XML_HEAD}<Relationships xmlns="{PKG_REL}">'
        + "".join(f'<Relationship Id="rId{n}" Type="{DOC_REL}/worksheet" Target="worksheets/sheet{n}.xml"/>'
                  for n in range(1, k + 1))
        + f'<Relationship Id="rId{k + 1}" Type="{DOC_REL}/styles" Target="styles.xml"/>'
        + f'<Relationship Id="rId{k + 2}" Type="{DOC_REL}/sharedStrings" Target="sharedStrings.xml"/></Relationships>')
    parts["_rels/.rels"] = (f'{XML_HEAD}<Relationships xmlns="{PKG_REL}"><Relationship Id="rId1" '
                            f'Type="{DOC_REL}/officeDocument" Target="xl/workbook.xml"/></Relationships>')
    sml = "application/vnd.openxmlformats-officedocument.spreadsheetml"
    parts["[Content_Types].xml"] = (
        f'{XML_HEAD}<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        f'<Override PartName="/xl/workbook.xml" ContentType="{sml}.sheet.main+xml"/>'
        + "".join(f'<Override PartName="/xl/worksheets/sheet{n}.xml" ContentType="{sml}.worksheet+xml"/>'
                  for n in range(1, k + 1))
        + f'<Override PartName="/xl/styles.xml" ContentType="{sml}.styles+xml"/>'
        f'<Override PartName="/xl/sharedStrings.xml" ContentType="{sml}.sharedStrings+xml"/></Types>')
    order = ["[Content_Types].xml", "_rels/.rels", "xl/workbook.xml", "xl/_rels/workbook.xml.rels", "xl/styles.xml",
             "xl/sharedStrings.xml", *(f"xl/worksheets/sheet{n}.xml" for n in range(1, k + 1))]
    for name in order:
        ET.fromstring(parts[name].encode("utf-8"))  # every part must be well-formed XML, before anything is written
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".partial")
    with zipfile.ZipFile(partial, "w") as z:
        for name in order:
            info = zipfile.ZipInfo(name, ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 0
            info.external_attr = 0o644 << 16
            z.writestr(info, parts[name].encode("utf-8"), compresslevel=9)
    os.replace(partial, path)  # an existing file is replaced only by a complete one


def _xml(z: zipfile.ZipFile, name: str) -> ET.Element:
    data = z.read(name)
    if b"<!DOCTYPE" in data or b"<!ENTITY" in data:
        raise ValueError(f"{name}: a document type declaration, which a spreadsheet never needs")
    return ET.fromstring(data)


def _part(base: str, target: str) -> str:
    """A relationship's target, as a path inside the ZIP file."""
    if target.startswith("/"):
        return target.lstrip("/")
    parts: list[str] = []
    for piece in (PurePosixPath(base).parent / target).parts:
        if piece == "..":
            parts.pop()
        elif piece != ".":
            parts.append(piece)
    return "/".join(parts)


def read(path: Path, sheet: str) -> list[list[str]]:
    """The cells of one sheet as text, row by row from row 1; empty cells are ""."""
    m = f"{{{MAIN}}}"
    with zipfile.ZipFile(path) as z:
        book = _xml(z, "xl/workbook.xml")
        rels = {r.get("Id"): r for r in _xml(z, "xl/_rels/workbook.xml.rels")}
        names = [s.get("name") for s in book.iter(f"{m}sheet")]
        rid = next((s.get(f"{{{DOC_REL}}}id") for s in book.iter(f"{m}sheet") if s.get("name") == sheet), None)
        if rid is None:
            raise ValueError(f"{path} has no sheet {sheet!r} (it has {names})")
        shared: list[str] = []
        for r in rels.values():
            if r.get("Type", "").endswith("/sharedStrings"):
                for si in _xml(z, _part("xl/workbook.xml", r.get("Target"))).iter(f"{m}si"):
                    # the text of the string, or of its runs; never its phonetic hints (rPh)
                    shared.append("".join(t.text or "" for t in [*si.findall(f"{m}t"), *si.findall(f"{m}r/{m}t")]))
        grid: dict[int, dict[int, str]] = {}
        row_number = 0
        for row in _xml(z, _part("xl/workbook.xml", rels[rid].get("Target"))).iter(f"{m}row"):
            row_number = int(row.get("r") or row_number + 1)
            col = -1
            for c in row.findall(f"{m}c"):
                ref = c.get("r")
                if ref:
                    letters = re.match(r"[A-Z]+", ref).group()
                    col = sum((ord(ch) - 64) * 26 ** i for i, ch in enumerate(reversed(letters))) - 1
                else:
                    col += 1
                kind, v = c.get("t"), c.find(f"{m}v")
                if kind == "s":
                    value = shared[int(v.text)] if v is not None and v.text else ""
                elif kind == "inlineStr":
                    inline = c.find(f"{m}is")
                    value = "" if inline is None else "".join(
                        t.text or "" for t in [*inline.findall(f"{m}t"), *inline.findall(f"{m}r/{m}t")])
                else:
                    value = (v.text or "") if v is not None else ""
                grid.setdefault(row_number, {})[col] = value
    if not grid:
        return []
    width = max(max(cols) for cols in grid.values() if cols) + 1 if any(grid.values()) else 0
    return [[grid.get(r, {}).get(c, "") for c in range(width)] for r in range(1, max(grid) + 1)]
