"""Day 3: Themed PowerPoint PPTX Maker using python-pptx (Claude-Quality Elevation).

Author: Vidhita (Document Engineer)
Module: creator.pptx_maker

Generates clean 16:9 widescreen presentation decks with:
- Title slide (title >= 28 pt, subtitle, theme branding, vertical accent bar)
- Section slides (one per section, titles >= 28 pt, body >= 18 pt)
- Automatic bullet splitting: at most 6 bullets per slide
- Bento grid metric card slides (2x2 cards with accent borders and large callout numbers)
- Table rendering support on slides
- Closing 'Thank you' slide
- Devanagari font embedding (Noto Sans Devanagari / Nirmala UI)
- Consistent theme colors and typography
- Optional auto-open feature using os.startfile()
- Strict Python 3.11+ type hints, robust error handling, and multi-theme support.
"""

from __future__ import annotations

import math
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

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
    return clean[:50] or "jarvis_presentation"


def _apply_slide_background(slide: Any, bg_hex: str) -> None:
    """Apply a solid background color to a presentation slide.

    Args:
        slide: pptx.slide.Slide instance.
        bg_hex: Color hex string (e.g., '#0F172A').
    """
    background = slide.background
    fill = background.fill
    fill.solid()
    r, g, b = hex_to_rgb(bg_hex)
    fill.fore_color.rgb = RGBColor(r, g, b)


def _chunk_list(items: List[Any], chunk_size: int = 6) -> List[List[Any]]:
    """Split a list into chunks of maximum size chunk_size."""
    if not items:
        return []
    return [items[i : i + chunk_size] for i in range(0, len(items), chunk_size)]


def _pick_font(text: str, default_font: str) -> str:
    """Pick appropriate font family, falling back to Devanagari if needed."""
    if contains_devanagari(text):
        return "Noto Sans Devanagari"
    return default_font


def make_pptx(
    title: str,
    sections: List[Dict[str, Any]],
    theme: str = "clean_light",
    out_dir: str = "workspace",
    subtitle: Optional[str] = None,
    auto_open: bool = True,
) -> str:
    """Build a themed, Claude-quality PowerPoint presentation deck (16:9).

    Slide structure:
    1. Title slide (>= 28 pt title, subtitle, accent bar)
    2. Section slides (max 6 bullets per slide, split automatically)
    3. Bento metric callout slides (if section contains 'metrics')
    4. Table slides (if section contains 'table')
    5. Closing 'Thank you' slide

    Typography constraints:
    - Titles >= 28 pt
    - Body >= 18 pt
    - Strong contrast and consistent fonts

    Args:
        title: Presentation title.
        sections: List of section dictionaries.
        theme: Theme name ('clean_light', 'dark_pro', 'colourful').
        out_dir: Target output directory.
        subtitle: Optional subtitle for title slide.
        auto_open: If True, opens the generated presentation automatically.

    Returns:
        str: Absolute filesystem path to the created PPTX file.
    """
    try:
        theme_cfg = get_theme(theme)
        target_dir = Path(out_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        safe_name = _sanitize_filename(title)
        out_path = target_dir / f"{safe_name}_{theme_cfg['name']}.pptx"

        prs = Presentation()
        # 16:9 widescreen dimensions (13.333 in x 7.5 in)
        prs.slide_width = Inches(13.333)
        prs.slide_height = Inches(7.5)

        blank_layout = prs.slide_layouts[6]  # Blank slide

        font_name = theme_cfg.get("font_family_name", "Arial")
        bg_hex = theme_cfg.get("bg_color", "#FFFFFF")
        prim_rgb = RGBColor(*hex_to_rgb(theme_cfg["primary_color"]))
        sec_rgb = RGBColor(*hex_to_rgb(theme_cfg["secondary_color"]))
        text_rgb = RGBColor(*hex_to_rgb(theme_cfg["text_color"]))
        accent_rgb = RGBColor(*hex_to_rgb(theme_cfg["accent_color"]))
        sub_rgb = RGBColor(*hex_to_rgb(theme_cfg.get("subtitle_color", "#64748B")))

        # -------------------------------------------------------------
        # 1. Title Slide
        # -------------------------------------------------------------
        title_slide = prs.slides.add_slide(blank_layout)
        _apply_slide_background(title_slide, bg_hex)

        # Full-bleed top accent stripe
        top_stripe = title_slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            Inches(0),
            Inches(0),
            Inches(13.333),
            Inches(0.18),
        )
        top_stripe.fill.solid()
        top_stripe.fill.fore_color.rgb = prim_rgb
        top_stripe.line.fill.background()

        # Vertical decorative accent bar
        accent_bar = title_slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            Inches(1.2),
            Inches(1.8),
            Inches(0.15),
            Inches(3.8),
        )
        accent_bar.fill.solid()
        accent_bar.fill.fore_color.rgb = accent_rgb
        accent_bar.line.fill.background()

        # Title text frame
        t_box = title_slide.shapes.add_textbox(
            Inches(1.6), Inches(1.8), Inches(10.5), Inches(3.8)
        )
        tf = t_box.text_frame
        tf.word_wrap = True

        p_main = tf.paragraphs[0]
        p_main.text = title
        p_main.font.name = _pick_font(title, font_name)
        p_main.font.size = Pt(40)  # >= 28 pt
        p_main.font.bold = True
        p_main.font.color.rgb = prim_rgb
        p_main.space_after = Pt(14)

        sub_text = subtitle or f"JARVIS Presentation Suite  |  Theme: {theme_cfg['name'].replace('_', ' ').title()}"
        p_sub = tf.add_paragraph()
        p_sub.text = sub_text
        p_sub.font.name = _pick_font(sub_text, font_name)
        p_sub.font.size = Pt(20)  # >= 18 pt
        p_sub.font.color.rgb = sec_rgb
        p_sub.space_after = Pt(14)

        p_author = tf.add_paragraph()
        p_author.text = "Author: Vidhita (Document Engineer)  •  Project JARVIS"
        p_author.font.name = font_name
        p_author.font.size = Pt(18)  # >= 18 pt
        p_author.font.color.rgb = text_rgb

        # -------------------------------------------------------------
        # 2. Section Slides
        # -------------------------------------------------------------
        for sec in sections:
            heading = sec.get("heading", "Topic Overview")
            body_text = sec.get("text", "")
            bullets = sec.get("bullets", [])
            table_data = sec.get("table")
            metrics = sec.get("metrics") or sec.get("bento_cards")

            # Split bullets if more than 6
            bullet_chunks = _chunk_list(bullets, chunk_size=6)
            if not bullet_chunks and not body_text and not table_data and not metrics:
                bullet_chunks = [[]]
            elif not bullet_chunks:
                bullet_chunks = [[]]

            for chunk_idx, chunk in enumerate(bullet_chunks):
                slide = prs.slides.add_slide(blank_layout)
                _apply_slide_background(slide, bg_hex)

                # Slide Heading (Titles >= 28 pt)
                h_box = slide.shapes.add_textbox(
                    Inches(1.0), Inches(0.7), Inches(11.333), Inches(1.1)
                )
                h_tf = h_box.text_frame
                h_tf.word_wrap = True
                h_p = h_tf.paragraphs[0]

                slide_title = heading
                if len(bullet_chunks) > 1 and chunk_idx > 0:
                    slide_title = f"{heading} (Cont.)"

                h_p.text = slide_title
                h_p.font.name = _pick_font(slide_title, font_name)
                h_p.font.size = Pt(30)  # >= 28 pt
                h_p.font.bold = True
                h_p.font.color.rgb = prim_rgb

                # Top decorative line under header
                hdr_line = slide.shapes.add_shape(
                    MSO_SHAPE.RECTANGLE,
                    Inches(1.0),
                    Inches(1.85),
                    Inches(11.333),
                    Inches(0.04),
                )
                hdr_line.fill.solid()
                hdr_line.fill.fore_color.rgb = sec_rgb
                hdr_line.line.fill.background()

                # Slide Body Frame
                b_box = slide.shapes.add_textbox(
                    Inches(1.0), Inches(2.1), Inches(11.333), Inches(4.6)
                )
                b_tf = b_box.text_frame
                b_tf.word_wrap = True

                first_para = True

                # Include narrative text on first chunk slide
                if body_text and chunk_idx == 0:
                    b_p = b_tf.paragraphs[0]
                    first_para = False
                    b_p.text = body_text
                    b_p.font.name = _pick_font(body_text, font_name)
                    b_p.font.size = Pt(19)  # >= 18 pt
                    b_p.font.color.rgb = text_rgb
                    b_p.space_after = Pt(14)

                # Render bullets (max 6 bullets, >= 18 pt body)
                for b_item in chunk:
                    if first_para:
                        p_item = b_tf.paragraphs[0]
                        first_para = False
                    else:
                        p_item = b_tf.add_paragraph()

                    p_item.text = f"•  {b_item}"
                    p_item.font.name = _pick_font(b_item, font_name)
                    p_item.font.size = Pt(18)  # >= 18 pt
                    p_item.font.color.rgb = text_rgb
                    p_item.space_after = Pt(10)

                # Footer tag on each slide
                f_box = slide.shapes.add_textbox(
                    Inches(1.0), Inches(6.8), Inches(11.333), Inches(0.4)
                )
                f_tf = f_box.text_frame
                f_p = f_tf.paragraphs[0]
                f_p.text = f"JARVIS  •  {title[:40]}"
                f_p.font.name = font_name
                f_p.font.size = Pt(11)
                f_p.font.color.rgb = sec_rgb

            # Bento Grid Metric Callout Slide
            if metrics and isinstance(metrics, list) and len(metrics) > 0:
                m_slide = prs.slides.add_slide(blank_layout)
                _apply_slide_background(m_slide, bg_hex)

                # Header
                mh_box = m_slide.shapes.add_textbox(Inches(1.0), Inches(0.7), Inches(11.333), Inches(1.1))
                mh_tf = mh_box.text_frame
                mh_p = mh_tf.paragraphs[0]
                mh_p.text = f"{heading} - Key Performance Metrics"
                mh_p.font.name = _pick_font(heading, font_name)
                mh_p.font.size = Pt(30)
                mh_p.font.bold = True
                mh_p.font.color.rgb = prim_rgb

                # 2x2 Bento Box Grid
                card_w = Inches(5.4)
                card_h = Inches(1.8)
                gap_x = Inches(0.533)
                gap_y = Inches(0.4)
                start_x = Inches(1.0)
                start_y = Inches(2.2)

                b_card_bg = RGBColor(*hex_to_rgb(theme_cfg.get("card_bg", "#F8FAFC")))
                b_border_rgb = RGBColor(*hex_to_rgb(theme_cfg.get("primary_color", "#1E40AF")))

                for m_idx, m_item in enumerate(metrics[:4]):
                    r_i = m_idx // 2
                    c_i = m_idx % 2
                    x = start_x + c_i * (card_w + gap_x)
                    y = start_y + r_i * (card_h + gap_y)

                    c_shape = m_slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, card_w, card_h)
                    c_shape.fill.solid()
                    c_shape.fill.fore_color.rgb = b_card_bg
                    c_shape.line.color.rgb = b_border_rgb
                    c_shape.line.width = Pt(1.5)

                    c_tf = c_shape.text_frame
                    c_tf.word_wrap = True
                    c_tf.margin_top = Inches(0.2)
                    c_tf.margin_left = Inches(0.3)

                    val_str = str(m_item.get("value", ""))
                    lbl_str = str(m_item.get("label", m_item.get("title", "")))

                    vp = c_tf.paragraphs[0]
                    vp.text = val_str
                    vp.font.name = _pick_font(val_str, font_name)
                    vp.font.size = Pt(32)
                    vp.font.bold = True
                    vp.font.color.rgb = prim_rgb
                    vp.space_after = Pt(4)

                    lp = c_tf.add_paragraph()
                    lp.text = lbl_str
                    lp.font.name = _pick_font(lbl_str, font_name)
                    lp.font.size = Pt(16)
                    lp.font.color.rgb = sub_rgb

            # Table slide if section has a table
            if table_data and isinstance(table_data, list) and len(table_data) > 0:
                t_slide = prs.slides.add_slide(blank_layout)
                _apply_slide_background(t_slide, bg_hex)

                th_box = t_slide.shapes.add_textbox(Inches(1.0), Inches(0.7), Inches(11.333), Inches(1.1))
                th_tf = th_box.text_frame
                th_tf.word_wrap = True
                th_p = th_tf.paragraphs[0]
                th_p.text = f"{heading} - Data Table"
                th_p.font.name = _pick_font(heading, font_name)
                th_p.font.size = Pt(30)  # >= 28 pt
                th_p.font.bold = True
                th_p.font.color.rgb = prim_rgb

                num_rows = len(table_data)
                num_cols = len(table_data[0]) if num_rows > 0 else 1
                table_shape = t_slide.shapes.add_table(
                    num_rows, num_cols, Inches(1.0), Inches(2.1), Inches(11.333), Inches(4.2)
                )
                tbl = table_shape.table

                hdr_bg_rgb = RGBColor(*hex_to_rgb(theme_cfg.get("table_header_bg", "#1E40AF")))
                hdr_txt_rgb = RGBColor(*hex_to_rgb(theme_cfg.get("table_header_text", "#FFFFFF")))
                row_alt_rgb = RGBColor(*hex_to_rgb(theme_cfg.get("table_row_alt", "#F1F5F9")))

                for r_idx, row in enumerate(table_data):
                    for c_idx, cell_value in enumerate(row):
                        cell = tbl.cell(r_idx, c_idx)
                        cell.text = str(cell_value)
                        cell_p = cell.text_frame.paragraphs[0]
                        cell_p.font.name = _pick_font(str(cell_value), font_name)

                        if r_idx == 0:
                            cell.fill.solid()
                            cell.fill.fore_color.rgb = hdr_bg_rgb
                            cell_p.font.size = Pt(18)
                            cell_p.font.bold = True
                            cell_p.font.color.rgb = hdr_txt_rgb
                        else:
                            if r_idx % 2 == 1:
                                cell.fill.solid()
                                cell.fill.fore_color.rgb = row_alt_rgb
                            cell_p.font.size = Pt(16)
                            cell_p.font.color.rgb = text_rgb

                # Footer
                tf_box = t_slide.shapes.add_textbox(Inches(1.0), Inches(6.8), Inches(11.333), Inches(0.4))
                tf_tf = tf_box.text_frame
                tf_p = tf_tf.paragraphs[0]
                tf_p.text = f"JARVIS  •  {title[:40]}"
                tf_p.font.name = font_name
                tf_p.font.size = Pt(11)
                tf_p.font.color.rgb = sec_rgb

            # Chart slide if section has a chart (Day 4 Deliverable)
            chart_cfg = sec.get("chart")
            chart_path = sec.get("chart_path") or sec.get("image_path")
            if chart_cfg and isinstance(chart_cfg, dict):
                try:
                    c_type = chart_cfg.get("type", "bar")
                    c_data = chart_cfg.get("data", {})
                    c_title = chart_cfg.get("title", f"{heading} Visualisation")
                    chart_path = generate_chart(
                        chart_type=c_type,
                        data=c_data,
                        title=c_title,
                        theme=theme,
                        out_dir=out_dir,
                    )
                except Exception:
                    chart_path = None

            if chart_path and os.path.exists(chart_path):
                c_slide = prs.slides.add_slide(blank_layout)
                _apply_slide_background(c_slide, bg_hex)

                ch_box = c_slide.shapes.add_textbox(Inches(1.0), Inches(0.7), Inches(11.333), Inches(1.1))
                ch_tf = ch_box.text_frame
                ch_tf.word_wrap = True
                ch_p = ch_tf.paragraphs[0]
                ch_p.text = f"{heading} - Data Visualisation"
                ch_p.font.name = _pick_font(heading, font_name)
                ch_p.font.size = Pt(30)
                ch_p.font.bold = True
                ch_p.font.color.rgb = prim_rgb

                # Top decorative line under header
                hdr_line = c_slide.shapes.add_shape(
                    MSO_SHAPE.RECTANGLE,
                    Inches(1.0),
                    Inches(1.85),
                    Inches(11.333),
                    Inches(0.04),
                )
                hdr_line.fill.solid()
                hdr_line.fill.fore_color.rgb = sec_rgb
                hdr_line.line.fill.background()

                # Center picture on 16:9 widescreen slide
                c_slide.shapes.add_picture(chart_path, Inches(2.666), Inches(2.1), width=Inches(8.0))

                # Footer
                cf_box = c_slide.shapes.add_textbox(Inches(1.0), Inches(6.8), Inches(11.333), Inches(0.4))
                cf_tf = cf_box.text_frame
                cf_p = cf_tf.paragraphs[0]
                cf_p.text = f"JARVIS  •  {title[:40]}"
                cf_p.font.name = font_name
                cf_p.font.size = Pt(11)
                cf_p.font.color.rgb = sec_rgb

        # -------------------------------------------------------------
        # 3. Closing 'Thank You' Slide
        # -------------------------------------------------------------
        thank_slide = prs.slides.add_slide(blank_layout)
        _apply_slide_background(thank_slide, bg_hex)

        ty_box = thank_slide.shapes.add_textbox(Inches(1.5), Inches(2.2), Inches(10.333), Inches(3.2))
        ty_tf = ty_box.text_frame
        ty_tf.word_wrap = True

        ty_p1 = ty_tf.paragraphs[0]
        ty_p1.text = "Thank You"
        ty_p1.font.name = font_name
        ty_p1.font.size = Pt(46)  # >= 28 pt
        ty_p1.font.bold = True
        ty_p1.font.color.rgb = prim_rgb
        ty_p1.alignment = PP_ALIGN.CENTER
        ty_p1.space_after = Pt(18)

        ty_p2 = ty_tf.add_paragraph()
        ty_p2.text = "Questions & Discussion | Project JARVIS"
        ty_p2.font.name = font_name
        ty_p2.font.size = Pt(22)  # >= 18 pt
        ty_p2.font.color.rgb = sec_rgb
        ty_p2.alignment = PP_ALIGN.CENTER

        prs.save(str(out_path))
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
        raise RuntimeError(f"make_pptx failed for '{title}': {exc}") from exc
