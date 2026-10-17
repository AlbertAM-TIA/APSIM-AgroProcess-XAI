#!/usr/bin/env python3
"""Build a journal-ready native Word table for Table 15."""

from __future__ import annotations

import json
from pathlib import Path
import os

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_ALIGN_VERTICAL, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt


HERE = Path(os.environ.get("RA_RESULTS_DIR", Path(__file__).resolve().parents[2] / "outputs/anova_shap_raw"))
HERE.mkdir(parents=True, exist_ok=True)
SOURCE = HERE / "Table15_source_data.json"
OUTPUT = HERE / "Table15_SOC_variance_decomposition.docx"

FONT = "Arial"
BLACK = "000000"
GREY = "D9D9D9"
LIGHT_GREY = "F2F2F2"


def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_borders(cell, **edges) -> None:
    """Set individual cell borders; values are dictionaries of OOXML attributes."""
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = tc_pr.first_child_found_in("w:tcBorders")
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tc_pr.append(borders)
    for edge_name, attrs in edges.items():
        tag = f"w:{edge_name}"
        edge = borders.find(qn(tag))
        if edge is None:
            edge = OxmlElement(tag)
            borders.append(edge)
        for key, value in attrs.items():
            edge.set(qn(f"w:{key}"), str(value))


def no_side_borders(cell) -> None:
    set_cell_borders(
        cell,
        left={"val": "nil"},
        right={"val": "nil"},
        insideV={"val": "nil"},
    )


def style_run(run, size=10.0, bold=False, italic=False) -> None:
    run.font.name = FONT
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = None
    r_pr = run._element.get_or_add_rPr()
    r_fonts = r_pr.rFonts
    if r_fonts is None:
        r_fonts = OxmlElement("w:rFonts")
        r_pr.append(r_fonts)
    r_fonts.set(qn("w:ascii"), FONT)
    r_fonts.set(qn("w:hAnsi"), FONT)
    r_fonts.set(qn("w:eastAsia"), FONT)


def write_cell(
    cell,
    text: str,
    *,
    align=WD_ALIGN_PARAGRAPH.LEFT,
    bold=False,
    italic=False,
    size=10.0,
) -> None:
    cell.text = ""
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    p = cell.paragraphs[0]
    p.alignment = align
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = 1.0
    run = p.add_run(text)
    style_run(run, size=size, bold=bold, italic=italic)


def set_repeat_table_header(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def set_exact_row_height(row, height_twips: int) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    tr_height = OxmlElement("w:trHeight")
    tr_height.set(qn("w:val"), str(height_twips))
    tr_height.set(qn("w:hRule"), "atLeast")
    tr_pr.append(tr_height)


def add_compact_paragraph(document: Document, text: str, *, size=9.0) -> None:
    p = document.add_paragraph()
    p.paragraph_format.space_before = Pt(3)
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = 1.0
    run = p.add_run(text)
    style_run(run, size=size)


def main() -> None:
    payload = json.loads(SOURCE.read_text(encoding="utf-8"))
    rows = payload["table15"]

    document = Document()
    section = document.sections[0]
    section.orientation = WD_ORIENT.PORTRAIT
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(1.8)
    section.bottom_margin = Cm(1.8)
    section.left_margin = Cm(2.0)
    section.right_margin = Cm(2.0)

    normal = document.styles["Normal"]
    normal.font.name = FONT
    normal.font.size = Pt(10)
    normal.font.color.rgb = None
    normal.paragraph_format.space_after = Pt(0)

    caption = document.add_paragraph()
    caption.paragraph_format.space_after = Pt(5)
    caption.paragraph_format.line_spacing = 1.0
    run = caption.add_run(
        "Table 15. Descriptive factorial decomposition of variation in "
        "cumulative and annual soil organic carbon responses under "
        "regenerative management."
    )
    style_run(run, size=10.5, bold=True)

    table = document.add_table(rows=1, cols=4)
    table.autofit = False
    table.alignment = 1
    table.allow_autofit = False
    widths = [Cm(8.2), Cm(1.5), Cm(3.2), Cm(4.0)]
    headers = ["Source", "df", "Sum of squares", "Share of total SS (%)"]

    header = table.rows[0]
    set_repeat_table_header(header)
    set_exact_row_height(header, 420)
    for cell, width, text in zip(header.cells, widths, headers):
        cell.width = width
        set_cell_shading(cell, GREY)
        write_cell(
            cell,
            text,
            align=(
                WD_ALIGN_PARAGRAPH.LEFT
                if text == "Source"
                else WD_ALIGN_PARAGRAPH.CENTER
            ),
            bold=True,
            size=9.8,
        )
        set_cell_borders(
            cell,
            top={"val": "single", "sz": "12", "color": BLACK},
            bottom={"val": "single", "sz": "8", "color": BLACK},
            left={"val": "nil"},
            right={"val": "nil"},
        )

    for panel in ["A", "B"]:
        panel_rows = [row for row in rows if row["Panel"] == panel]
        label = (
            "A. Cumulative SOC"
            if panel == "A"
            else "B. Annual SOC change"
        )
        panel_row = table.add_row()
        merged = panel_row.cells[0]
        for other in panel_row.cells[1:]:
            merged = merged.merge(other)
        set_cell_shading(merged, LIGHT_GREY)
        write_cell(merged, label, bold=True, size=10.0)
        set_cell_borders(
            merged,
            top={"val": "single", "sz": "8", "color": BLACK},
            bottom={"val": "single", "sz": "6", "color": "808080"},
            left={"val": "nil"},
            right={"val": "nil"},
        )
        set_exact_row_height(panel_row, 340)

        for item in panel_rows:
            row = table.add_row()
            values = [
                item["Source"],
                f"{int(item['df'])}",
                f"{item['Sum of squares']:.3f}",
                (
                    f"{item['Share of total SS (%)']:.2f}"
                    if item["Share of total SS (%)"] < 0.1
                    else f"{item['Share of total SS (%)']:.1f}"
                ),
            ]
            for index, (cell, width, value) in enumerate(
                zip(row.cells, widths, values)
            ):
                cell.width = width
                write_cell(
                    cell,
                    value,
                    align=(
                        WD_ALIGN_PARAGRAPH.LEFT
                        if index == 0
                        else WD_ALIGN_PARAGRAPH.RIGHT
                    ),
                    size=9.8,
                )
                set_cell_borders(
                    cell,
                    bottom={"val": "single", "sz": "3", "color": "BFBFBF"},
                    left={"val": "nil"},
                    right={"val": "nil"},
                )
            set_exact_row_height(row, 315)

    last_row = table.rows[-1]
    for cell in last_row.cells:
        set_cell_borders(
            cell,
            bottom={"val": "single", "sz": "12", "color": BLACK},
            left={"val": "nil"},
            right={"val": "nil"},
        )

    add_compact_paragraph(
        document,
        "Notes: df, degrees of freedom; SS, sums of squares; SOC, soil organic "
        "carbon. Climate denotes climate period in panel A and climate year in "
        "panel B. Season denotes the winter or spring rotation.",
        size=8.8,
    )
    add_compact_paragraph(
        document,
        "Residual denotes the omitted Management × Climate × Season term and "
        "is not independently replicated error; F tests and p-values are "
        "therefore not reported. Analyses used the six complete management "
        "systems, both climate periods and the higher fixed CO₂ scenario.",
        size=8.8,
    )

    document.save(OUTPUT)


if __name__ == "__main__":
    main()
