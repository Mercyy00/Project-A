"""Day 3: Themed Word DOCX Maker using python-docx (Claude-Quality Elevation).

Author: Document Engineer
Module: creator.docx_maker

Generates publication-grade, beautifully styled Word (.docx) documents with:
- Executive cover page (accent banner, large title, subtitle, metadata card, page break)
- Bento grid metric callouts (2-column shaded card tables with colored borders)
- Section headings (Heading 1) with primary theme color
- Formatted paragraphs and bullet lists
- Clean modern tables with header shading and alternating row fills
- Devanagari font embedding (Noto Sans Devanagari / Nirmala UI)
- Document headers and footers with page number context
- Optional auto-open feature using os.startfile()
- Strict Python 3.11+ type hints, robust error handling, and multi-theme support.
"""

from __future__ import annotations

import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional

import docx
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Inches, Pt, RGBColor

from creator.chart_maker import generate_chart
from creator.themes import (
    THEMES,
    contains_devanagari,
    get_theme,
    hex_to_rgb,
)


def _sanitize_filename(name: str) -> str:
    """Sanitize title to produce a safe filesystem filename."""
    clean = re.sub(r'[\\/*?:"<>|]', "", name)
    clean = clean.strip().replace(" ", "_").lower()
    return clean[:50] or "jarvis_doc"


def _set_cell_background(cell: Any, fill_hex: str) -> None:
    """Set the background shading of a table cell.

    Args:
        cell: docx.table._Cell instance.
        fill_hex: Hex color string.
    """
    clean_hex = fill_hex.lstrip("#")
    tcPr = cell._tc.get_or_add_tcPr()
    existing_shd = tcPr.findall(qn("w:shd"))
    for s in existing_shd:
        tcPr.remove(s)
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{clean_hex}"/>')
    tcPr.append(shd)


def _set_cell_margins(cell: Any, top: int = 140, bottom: int = 140, left: int = 180, right: int = 180) -> None:
    """Set internal cell margins (padding in dxa, 20 dxa = 1 pt)."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'  <w:top w:w="{top}" w:type="dxa"/>'
        f'  <w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'  <w:left w:w="{left}" w:type="dxa"/>'
        f'  <w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tcPr.append(tcMar)


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
        f'  <w:top w:val="single" w:sz="6" w:space="0" w:color="{clean_hex}"/>'
        f'  <w:left w:val="none"/>'
        f'  <w:bottom w:val="single" w:sz="8" w:space="0" w:color="{clean_hex}"/>'
        f'  <w:right w:val="none"/>'
        f'  <w:insideH w:val="single" w:sz="4" w:space="0" w:color="{clean_hex}"/>'
        f'  <w:insideV w:val="none"/>'
        f'</w:tblBorders>'
    )
    tblPr.append(tbl_borders)


def _set_card_borders(table: Any, border_hex: str = "3B82F6") -> None:
    """Apply boxed card borders to a Bento Grid table."""
    clean_hex = border_hex.lstrip("#")
    tblPr = table._tbl.tblPr
    existing_borders = tblPr.findall(qn("w:tblBorders"))
    for b in existing_borders:
        tblPr.remove(b)

    tbl_borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'  <w:top w:val="single" w:sz="8" w:space="0" w:color="{clean_hex}"/>'
        f'  <w:left w:val="single" w:sz="8" w:space="0" w:color="{clean_hex}"/>'
        f'  <w:bottom w:val="single" w:sz="8" w:space="0" w:color="{clean_hex}"/>'
        f'  <w:right w:val="single" w:sz="8" w:space="0" w:color="{clean_hex}"/>'
        f'  <w:insideH w:val="single" w:sz="6" w:space="0" w:color="{clean_hex}"/>'
        f'  <w:insideV w:val="single" w:sz="6" w:space="0" w:color="{clean_hex}"/>'
        f'</w:tblBorders>'
    )
    tblPr.append(tbl_borders)


def _format_run(run: Any, text: str, font_name: str, size_pt: float, color_rgb: RGBColor, bold: bool = False, italic: bool = False) -> None:
    """Helper to format a text run with full font, Devanagari complex script, and color."""
    run.text = text
    run.font.name = font_name
    run.font.size = Pt(size_pt)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color_rgb

    # Devanagari complex script font tag for Word
    if contains_devanagari(text):
        rPr = run._r.get_or_add_rPr()
        rFonts = parse_xml(
            f'<w:rFonts {nsdecls("w")} w:ascii="{font_name}" w:hAnsi="{font_name}" w:cs="Noto Sans Devanagari"/>'
        )
        rPr.append(rFonts)


def make_docx(
    title: str,
    sections: List[Dict[str, Any]],
    theme: str = "clean_light",
    out_dir: str = "workspace",
    subtitle: Optional[str] = None,
    auto_open: bool = True,
    cover_page: bool = True,
    header_text: Optional[str] = None,
    footer_text: Optional[str] = None,
    author: Optional[str] = None,
) -> str:
    """Build a themed, Claude-quality Word document using python-docx.

    Args:
        title: Document title.
        sections: List of section dicts with 'heading', 'text', 'bullets', 'metrics', and optional 'table'.
        theme: Theme name ('clean_light', 'dark_pro', 'colourful').
        out_dir: Target output directory.
        subtitle: Optional subtitle for executive cover page.
        auto_open: If True, opens the generated Word document automatically.
        cover_page: Whether to include an executive cover page (default: True).
        header_text: Optional running header text.
        footer_text: Optional running footer text.

    Returns:
        str: Absolute filesystem path to the created DOCX file.
    """
    try:
        theme_cfg = get_theme(theme)
        target_dir = Path(out_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        safe_name = _sanitize_filename(title)
        out_path = target_dir / f"{safe_name}_{theme_cfg['name']}.docx"

        doc = docx.Document()
        doc_author = (author or "").strip() or "Project JARVIS"

        # Page margins
        for section in doc.sections:
            section.top_margin = Inches(0.8)
            section.bottom_margin = Inches(0.8)
            section.left_margin = Inches(0.8)
            section.right_margin = Inches(0.8)

            # Header & Footer branding
            header = section.header
            header_p = header.paragraphs[0]
            header_p.text = header_text or f"{title[:40]} | JARVIS Autonomous Document Engine"
            header_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            if header_p.runs:
                _format_run(
                    header_p.runs[0],
                    header_p.text,
                    theme_cfg.get("font_family_name", "Arial"),
                    8.5,
                    RGBColor(*hex_to_rgb(theme_cfg.get("secondary_color", "#3B82F6"))),
                )

            footer = section.footer
            footer_p = footer.paragraphs[0]
            if footer_text:
                footer_p.text = footer_text
            elif author and author.strip():
                footer_p.text = f"Theme: {theme_cfg['name'].replace('_', ' ').title()}  •  Author: {author.strip()}  •  Project JARVIS"
            else:
                footer_p.text = f"Theme: {theme_cfg['name'].replace('_', ' ').title()}  •  Project JARVIS Document Engine"
            footer_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            if footer_p.runs:
                _format_run(
                    footer_p.runs[0],
                    footer_p.text,
                    theme_cfg.get("font_family_name", "Arial"),
                    8.5,
                    RGBColor(*hex_to_rgb(theme_cfg.get("text_color", "#1E293B"))),
                )

        font_name = theme_cfg.get("font_family_name", "Arial")
        prim_rgb = RGBColor(*hex_to_rgb(theme_cfg["primary_color"]))
        sec_rgb = RGBColor(*hex_to_rgb(theme_cfg["secondary_color"]))
        text_rgb = RGBColor(*hex_to_rgb(theme_cfg["text_color"]))
        sub_rgb = RGBColor(*hex_to_rgb(theme_cfg.get("subtitle_color", "#64748B")))
        border_hex = theme_cfg.get("border_color", "#CBD5E1").lstrip("#")

        # -------------------------------------------------------------
        # 1. Executive Cover Page (Optional)
        # -------------------------------------------------------------
        if cover_page:
            # Accent top banner spacing
            banner_p = doc.add_paragraph()
            banner_p.paragraph_format.space_before = Pt(36)
            banner_p.paragraph_format.space_after = Pt(8)

            # Title
            title_p = doc.add_paragraph()
            t_run = title_p.add_run()
            _format_run(t_run, title, font_name, theme_cfg["spacing"]["title_size"], prim_rgb, bold=True)
            title_p.paragraph_format.space_after = Pt(6)

            # Subtitle
            sub_p = doc.add_paragraph()
            sub_text = subtitle or "JARVIS Autonomous Intelligence • Executive Document"
            s_run = sub_p.add_run()
            _format_run(s_run, sub_text, font_name, 13, sub_rgb, italic=True)
            sub_p.paragraph_format.space_after = Pt(28)

            # Executive Metadata Card Table
            meta_table = doc.add_table(rows=2, cols=2)
            meta_table.alignment = WD_TABLE_ALIGNMENT.CENTER
            meta_table.autofit = False

            meta_rows_data = [
                [("AUTHOR", doc_author), ("STATUS", "Production Verified")],
                [("THEME", theme_cfg["name"].replace("_", " ").title()), ("ENGINE", "python-docx Executive")],
            ]
            for r_idx, row in enumerate(meta_rows_data):
                for c_idx, (label, val) in enumerate(row):
                    cell = meta_table.cell(r_idx, c_idx)
                    cell.width = Inches(3.3)
                    _set_cell_background(cell, theme_cfg.get("card_bg", "#F8FAFC"))
                    _set_cell_margins(cell, top=160, bottom=160, left=180, right=180)

                    cp = cell.paragraphs[0]
                    cp.paragraph_format.space_after = Pt(2)
                    l_run = cp.add_run()
                    _format_run(l_run, f"{label}: ", font_name, 9, sub_rgb, bold=True)
                    v_run = cp.add_run()
                    _format_run(v_run, val, font_name, 10, text_rgb)

            _set_card_borders(meta_table, border_hex)

            # Space and PageBreak to move content to Page 2
            post_p = doc.add_paragraph()
            post_p.paragraph_format.space_before = Pt(120)
            doc.add_page_break()
        else:
            # Inline header for single-page or cover-free documents
            title_p = doc.add_paragraph()
            t_run = title_p.add_run()
            _format_run(t_run, title, font_name, theme_cfg["spacing"]["title_size"], prim_rgb, bold=True)
            title_p.paragraph_format.space_after = Pt(4)
            if subtitle:
                sub_p = doc.add_paragraph()
                s_run = sub_p.add_run()
                _format_run(s_run, subtitle, font_name, 12, sub_rgb, italic=True)
                sub_p.paragraph_format.space_after = Pt(14)

        # -------------------------------------------------------------
        # 2. Content Sections
        # -------------------------------------------------------------
        for sec in sections:
            # Heading 1
            heading = sec.get("heading")
            if heading:
                h_p = doc.add_paragraph()
                h_run = h_p.add_run()
                _format_run(h_run, heading, font_name, theme_cfg["spacing"]["heading_size"], prim_rgb, bold=True)
                h_p.paragraph_format.space_before = Pt(16)
                h_p.paragraph_format.space_after = Pt(6)
                h_p.paragraph_format.keep_with_next = True

            # Narrative body
            body_text = sec.get("text")
            if body_text:
                b_p = doc.add_paragraph()
                b_run = b_p.add_run()
                _format_run(b_run, body_text, font_name, theme_cfg["spacing"]["body_size"], text_rgb)
                b_p.paragraph_format.space_after = Pt(8)

            # Bento Grid Metric Callout Cards
            metrics = sec.get("metrics") or sec.get("bento_cards")
            if metrics and isinstance(metrics, list):
                num_items = len(metrics)
                rows_count = (num_items + 1) // 2
                bento_table = doc.add_table(rows=rows_count, cols=2)
                bento_table.alignment = WD_TABLE_ALIGNMENT.CENTER
                _set_card_borders(bento_table, theme_cfg.get("primary_color", "#1E40AF"))

                b_metric_rgb = RGBColor(*hex_to_rgb(theme_cfg.get("primary_color", "#1E40AF")))
                b_card_bg = theme_cfg.get("card_bg", "#F8FAFC")

                for idx, item in enumerate(metrics):
                    r_i = idx // 2
                    c_i = idx % 2
                    cell = bento_table.cell(r_i, c_i)
                    cell.width = Inches(3.3)
                    _set_cell_background(cell, b_card_bg)
                    _set_cell_margins(cell, top=160, bottom=160, left=180, right=180)

                    val_str = str(item.get("value", ""))
                    lbl_str = str(item.get("label", item.get("title", "")))

                    cp = cell.paragraphs[0]
                    cp.paragraph_format.space_after = Pt(2)
                    v_run = cp.add_run()
                    _format_run(v_run, val_str, font_name, 18, b_metric_rgb, bold=True)

                    lp = cell.add_paragraph()
                    lp.paragraph_format.space_after = Pt(0)
                    l_run = lp.add_run()
                    _format_run(l_run, lbl_str, font_name, 9.5, sub_rgb)

                # Clean spacing after bento grid
                gap_p = doc.add_paragraph()
                gap_p.paragraph_format.space_before = Pt(6)

            # Bullets
            bullets = sec.get("bullets", [])
            for bullet in bullets:
                bl_p = doc.add_paragraph(style="List Bullet")
                bl_run = bl_p.add_run()
                _format_run(bl_run, bullet, font_name, theme_cfg["spacing"]["bullet_size"], text_rgb)
                bl_p.paragraph_format.space_after = Pt(4)

            # Table
            table_data = sec.get("table")
            if table_data and isinstance(table_data, list):
                num_rows = len(table_data)
                num_cols = max(len(row) for row in table_data) if num_rows > 0 else 0

                if num_rows > 0 and num_cols > 0:
                    tbl = doc.add_table(rows=num_rows, cols=num_cols)
                    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
                    _set_table_borders(tbl, border_hex)

                    hdr_bg = theme_cfg["table_header_bg"]
                    hdr_text_rgb = RGBColor(*hex_to_rgb(theme_cfg["table_header_text"]))
                    alt_bg = theme_cfg["table_row_alt"]
                    card_bg = theme_cfg["card_bg"]

                    for r_idx, row in enumerate(table_data):
                        is_hdr = (r_idx == 0)
                        row_bg = hdr_bg if is_hdr else (alt_bg if r_idx % 2 == 1 else card_bg)

                        for c_idx, cell_value in enumerate(row):
                            if c_idx < num_cols:
                                cell = tbl.cell(r_idx, c_idx)
                                _set_cell_background(cell, row_bg)
                                _set_cell_margins(cell, top=120, bottom=120, left=140, right=140)

                                cell_p = cell.paragraphs[0]
                                cell_p.paragraph_format.space_after = Pt(0)
                                c_run = cell_p.add_run()
                                if is_hdr:
                                    _format_run(c_run, str(cell_value), font_name, 10, hdr_text_rgb, bold=True)
                                else:
                                    _format_run(c_run, str(cell_value), font_name, 9.5, text_rgb)

                    # Space after table
                    tbl_gap = doc.add_paragraph()
                    tbl_gap.paragraph_format.space_before = Pt(8)

            # Chart Embedding (Days 4 & 6 Deliverable)
            chart_cfg = sec.get("chart")
            chart_path = sec.get("chart_path") or sec.get("image_path")
            if chart_cfg and isinstance(chart_cfg, dict):
                try:
                    if "labels" in chart_cfg and "values" in chart_cfg:
                        from creator.charts import make_chart
                        c_kind = chart_cfg.get("kind", chart_cfg.get("type", "bar"))
                        c_labels = chart_cfg.get("labels", [])
                        c_values = chart_cfg.get("values", [])
                        c_title = chart_cfg.get("title", f"{heading} Chart")
                        chart_path = make_chart(
                            kind=c_kind,
                            labels=c_labels,
                            values=c_values,
                            title=c_title,
                            theme=theme,
                            out_dir=out_dir,
                        )
                    else:
                        c_type = chart_cfg.get("type", chart_cfg.get("kind", "bar"))
                        c_data = chart_cfg.get("data", {})
                        c_title = chart_cfg.get("title", f"{heading} Chart")
                        chart_path = generate_chart(
                            chart_type=c_type,
                            data=c_data,
                            title=c_title,
                            theme=theme,
                            out_dir=out_dir,
                        )
                except Exception:
                    chart_path = None
            elif chart_cfg and isinstance(chart_cfg, str) and os.path.exists(chart_cfg):
                chart_path = chart_cfg

            if chart_path and os.path.exists(chart_path):
                try:
                    pic_p = doc.add_paragraph()
                    pic_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    pic_p.paragraph_format.space_before = Pt(8)
                    pic_p.paragraph_format.space_after = Pt(8)
                    r = pic_p.add_run()
                    r.add_picture(chart_path, width=Inches(5.5))
                except Exception:
                    pass

            # Optional section page break
            if sec.get("page_break_after"):
                doc.add_page_break()

        doc.save(str(out_path))
        resolved_path = str(out_path.resolve())

        # Auto-open feature (calls os.startfile on Windows)
        if auto_open:
            try:
                if hasattr(os, "startfile"):
                    os.startfile(resolved_path)
            except Exception:
                pass

        return resolved_path

    except Exception as exc:
        raise RuntimeError(f"make_docx failed for '{title}': {exc}") from exc
