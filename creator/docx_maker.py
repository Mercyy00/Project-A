"""Day 3: Themed Word DOCX Maker using python-docx.

Author: Vidhita (Document Engineer)
Module: creator.docx_maker

Generates beautifully styled Word (.docx) documents with:
- Title with theme colors and typography
- Section headings (Heading 1) with primary theme color
- Formatted paragraphs and bullet lists
- Clean tables with light borders, styled headers, and alternating row fills
- Document header and footer
- Support for 'clean_light', 'dark_pro', and 'colourful' themes
"""

import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional

import docx
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import nsdecls, qn

from creator.themes import THEMES, get_theme, hex_to_rgb


def _sanitize_filename(name: str) -> str:
    """Sanitize title to produce a clean, safe filename."""
    clean = re.sub(r'[\\/*?:"<>|]', "", name)
    clean = clean.strip().replace(" ", "_").lower()
    return clean[:50] or "jarvis_doc"


def _set_cell_background(cell: Any, fill_hex: str) -> None:
    """Set the background shading of a table cell.

    Args:
        cell: docx.table._Cell instance.
        fill_hex: Hex color string (without '#').
    """
    clean_hex = fill_hex.lstrip("#")
    tcPr = cell._tc.get_or_add_tcPr()
    # Remove existing shading if any
    existing_shd = tcPr.findall(qn("w:shd"))
    for s in existing_shd:
        tcPr.remove(s)
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{clean_hex}"/>')
    tcPr.append(shd)


def _set_table_borders(table: Any, border_hex: str = "CBD5E1") -> None:
    """Apply elegant light borders to a docx table.

    Args:
        table: docx.table.Table instance.
        border_hex: Hex color for borders.
    """
    clean_hex = border_hex.lstrip("#")
    tblPr = table._tbl.tblPr
    existing_borders = tblPr.findall(qn("w:tblBorders"))
    for b in existing_borders:
        tblPr.remove(b)

    tbl_borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'  <w:top w:val="single" w:sz="4" w:space="0" w:color="{clean_hex}"/>'
        f'  <w:left w:val="none"/>'
        f'  <w:bottom w:val="single" w:sz="6" w:space="0" w:color="{clean_hex}"/>'
        f'  <w:right w:val="none"/>'
        f'  <w:insideH w:val="single" w:sz="4" w:space="0" w:color="{clean_hex}"/>'
        f'  <w:insideV w:val="none"/>'
        f"</w:tblBorders>"
    )
    tblPr.append(tbl_borders)


def make_docx(
    title: str,
    sections: List[Dict[str, Any]],
    theme: str = "clean_light",
    out_dir: str = "workspace",
) -> str:
    """Build a themed Word document using python-docx.

    Args:
        title: Document title.
        sections: List of section dicts with 'heading', 'text', 'bullets', and optional 'table'.
        theme: Theme name ('clean_light', 'dark_pro', 'colourful'). Defaults to 'clean_light'.
        out_dir: Target output directory.

    Returns:
        Absolute string path to the created DOCX file.
    """
    try:
        theme_cfg = get_theme(theme)
        target_dir = Path(out_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        safe_name = _sanitize_filename(title)
        out_path = target_dir / f"{safe_name}_{theme_cfg['name']}.docx"

        doc = docx.Document()

        # Page margins
        for section in doc.sections:
            section.top_margin = Inches(0.8)
            section.bottom_margin = Inches(0.8)
            section.left_margin = Inches(0.8)
            section.right_margin = Inches(0.8)

            # Header & Footer
            header = section.header
            header_p = header.paragraphs[0]
            header_p.text = f"{title} | JARVIS Document Engine"
            header_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            if header_p.runs:
                header_p.runs[0].font.name = theme_cfg.get("font_family_name", "Arial")
                header_p.runs[0].font.size = Pt(8.5)
                r, g, b = hex_to_rgb(theme_cfg.get("secondary_color", "#3B82F6"))
                header_p.runs[0].font.color.rgb = RGBColor(r, g, b)

            footer = section.footer
            footer_p = footer.paragraphs[0]
            footer_p.text = f"Theme: {theme_cfg['name']}  •  Author: Vidhita (Documents)"
            footer_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            if footer_p.runs:
                footer_p.runs[0].font.name = theme_cfg.get("font_family_name", "Arial")
                footer_p.runs[0].font.size = Pt(8.5)
                r, g, b = hex_to_rgb(theme_cfg.get("text_color", "#1E293B"))
                footer_p.runs[0].font.color.rgb = RGBColor(r, g, b)

        font_name = theme_cfg.get("font_family_name", "Arial")
        prim_rgb = hex_to_rgb(theme_cfg["primary_color"])
        sec_rgb = hex_to_rgb(theme_cfg["secondary_color"])
        text_rgb = hex_to_rgb(theme_cfg["text_color"])

        # Title
        title_p = doc.add_paragraph()
        title_run = title_p.add_run(title)
        title_run.font.name = font_name
        title_run.font.size = Pt(theme_cfg["spacing"]["title_size"])
        title_run.font.bold = True
        title_run.font.color.rgb = RGBColor(*prim_rgb)
        title_p.paragraph_format.space_before = Pt(0)
        title_p.paragraph_format.space_after = Pt(4)

        # Subtitle / Metadata
        sub_p = doc.add_paragraph()
        sub_run = sub_p.add_run(f"Project JARVIS  |  Theme: {theme_cfg['name']}")
        sub_run.font.name = font_name
        sub_run.font.size = Pt(11)
        sub_run.font.italic = True
        sub_run.font.color.rgb = RGBColor(*sec_rgb)
        sub_p.paragraph_format.space_after = Pt(20)

        # Iterate over sections
        for sec in sections:
            # Section Heading (Heading 1)
            heading = sec.get("heading")
            if heading:
                h_p = doc.add_paragraph()
                h_run = h_p.add_run(heading)
                h_run.font.name = font_name
                h_run.font.size = Pt(theme_cfg["spacing"]["heading_size"])
                h_run.font.bold = True
                h_run.font.color.rgb = RGBColor(*prim_rgb)
                h_p.paragraph_format.space_before = Pt(16)
                h_p.paragraph_format.space_after = Pt(6)
                h_p.paragraph_format.keep_with_next = True

            # Narrative Text
            body_text = sec.get("text")
            if body_text:
                b_p = doc.add_paragraph()
                b_run = b_p.add_run(body_text)
                b_run.font.name = font_name
                b_run.font.size = Pt(theme_cfg["spacing"]["body_size"])
                b_run.font.color.rgb = RGBColor(*text_rgb)
                b_p.paragraph_format.space_before = Pt(0)
                b_p.paragraph_format.space_after = Pt(8)
                b_p.paragraph_format.line_spacing = 1.15

            # Bullet List
            bullets = sec.get("bullets", [])
            if bullets:
                for bullet in bullets:
                    bullet_p = doc.add_paragraph(style="List Bullet")
                    bullet_run = bullet_p.add_run(bullet)
                    bullet_run.font.name = font_name
                    bullet_run.font.size = Pt(theme_cfg["spacing"]["bullet_size"])
                    bullet_run.font.color.rgb = RGBColor(*text_rgb)
                    bullet_p.paragraph_format.space_before = Pt(0)
                    bullet_p.paragraph_format.space_after = Pt(3)

            # Table (if present)
            table_data = sec.get("table")
            if table_data and isinstance(table_data, list) and len(table_data) > 0:
                rows_count = len(table_data)
                cols_count = len(table_data[0]) if rows_count > 0 else 0

                table = doc.add_table(rows=rows_count, cols=cols_count)
                table.alignment = WD_TABLE_ALIGNMENT.CENTER
                _set_table_borders(table, border_hex=theme_cfg["border_color"])

                # Header row styling
                header_text_rgb = hex_to_rgb(theme_cfg["table_header_text"])
                for col_idx, cell_value in enumerate(table_data[0]):
                    cell = table.cell(0, col_idx)
                    cell.text = str(cell_value)
                    _set_cell_background(cell, theme_cfg["table_header_bg"])
                    for p in cell.paragraphs:
                        p.paragraph_format.space_before = Pt(4)
                        p.paragraph_format.space_after = Pt(4)
                        for r in p.runs:
                            r.font.name = font_name
                            r.font.size = Pt(10)
                            r.font.bold = True
                            r.font.color.rgb = RGBColor(*header_text_rgb)

                # Body rows styling
                for row_idx in range(1, rows_count):
                    bg_fill = (
                        theme_cfg["card_bg"]
                        if row_idx % 2 == 1
                        else theme_cfg["table_row_alt"]
                    )
                    for col_idx, cell_value in enumerate(table_data[row_idx]):
                        cell = table.cell(row_idx, col_idx)
                        cell.text = str(cell_value)
                        _set_cell_background(cell, bg_fill)
                        for p in cell.paragraphs:
                            p.paragraph_format.space_before = Pt(3)
                            p.paragraph_format.space_after = Pt(3)
                            for r in p.runs:
                                r.font.name = font_name
                                r.font.size = Pt(9.5)
                                r.font.color.rgb = RGBColor(*text_rgb)

                # Add space after table
                spacer_p = doc.add_paragraph()
                spacer_p.paragraph_format.space_before = Pt(6)
                spacer_p.paragraph_format.space_after = Pt(0)

            # Check for page break
            if sec.get("page_break_after"):
                doc.add_page_break()

        doc.save(str(out_path))
        return str(out_path.resolve())

    except Exception as exc:
        raise RuntimeError(f"make_docx failed for '{title}': {exc}") from exc
