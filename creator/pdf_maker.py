"""Day 2 & Day 3: Themed PDF Maker using ReportLab Platypus (Claude-Quality Elevation).

Author: Vidhita (Document Engineer)
Module: creator.pdf_maker

Generates publication-grade, beautifully styled, multi-page PDFs with:
- Executive cover page (full-bleed accent stripe, subtitle, structured metadata card)
- Bento grid metric callouts (2x2 key metric cards with accent borders and bold numerals)
- Themed headings, paragraphs, and bullet points
- Formatted modern tables with header and alternating row colors
- Devanagari font embedding (Noto Sans Devanagari) preventing square-box corruption
- Dynamic footer with page numbers ('Page X of Y')
- Optional auto-open feature using os.startfile()
- Strict Python 3.11+ type hints, robust error handling, and multi-theme support.
"""

from __future__ import annotations

import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    Image as RLImage,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from creator.chart_maker import generate_chart
from creator.themes import (
    THEMES,
    contains_devanagari,
    get_theme,
    register_devanagari_fonts,
)


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute total page count and draw running footers."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._saved_page_states: List[Dict[str, Any]] = []

    def showPage(self) -> None:
        """Capture page state and defer final drawing until save."""
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        """Draw running footers on each captured page with total page count."""
        num_pages = len(self._saved_page_states)
        theme_cfg = getattr(self, "_theme_cfg", THEMES["clean_light"])
        doc_title = getattr(self, "_doc_title", "Project JARVIS")

        text_hex = theme_cfg.get("text_color", "#1E293B")
        border_hex = theme_cfg.get("border_color", "#CBD5E1")
        footer_color = colors.HexColor(text_hex)
        line_color = colors.HexColor(border_hex)

        for state in self._saved_page_states:
            self.__dict__.update(state)
            page_num = self._pageNumber

            # Only show footer on pages after cover page
            if page_num > 1:
                self.saveState()
                self.setFont("Helvetica", 9)
                self.setFillColor(footer_color)
                self.setStrokeColor(line_color)
                self.setLineWidth(0.5)

                # Running divider line
                self.line(54, 45, 612 - 54, 45)

                # Left: Document Title
                clean_title = doc_title[:45] + ("..." if len(doc_title) > 45 else "")
                self.drawString(54, 32, f"{clean_title} • Project JARVIS")

                # Right: Page X of Y
                page_str = f"Page {page_num} of {num_pages}"
                self.drawRightString(612 - 54, 32, page_str)
                self.restoreState()

            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)


def _draw_page_background(canvas_obj: canvas.Canvas, doc: SimpleDocTemplate, theme_cfg: Dict[str, Any], is_cover: bool) -> None:
    """Draw full-page background color and executive cover decorations.

    Args:
        canvas_obj: ReportLab canvas instance.
        doc: Document template.
        theme_cfg: Active theme dictionary.
        is_cover: Whether this is the first (cover) page.
    """
    canvas_obj.saveState()
    bg_hex = theme_cfg.get("bg_color", "#FFFFFF")
    page_w, page_h = doc.pagesize

    # Background wash
    canvas_obj.setFillColor(colors.HexColor(bg_hex))
    canvas_obj.rect(0, 0, page_w, page_h, fill=1, stroke=0)

    # Executive Cover Page: Full-bleed accent stripe at top
    if is_cover:
        stripe_hex = theme_cfg.get("cover_stripe_color", theme_cfg.get("primary_color", "#1E40AF"))
        canvas_obj.setFillColor(colors.HexColor(stripe_hex))
        canvas_obj.rect(0, page_h - 18, page_w, 18, fill=1, stroke=0)

        # Thin secondary accent pinstripe
        sec_hex = theme_cfg.get("secondary_color", "#3B82F6")
        canvas_obj.setFillColor(colors.HexColor(sec_hex))
        canvas_obj.rect(0, page_h - 22, page_w, 4, fill=1, stroke=0)

    canvas_obj.restoreState()


def _sanitize_filename(name: str) -> str:
    """Sanitize title to produce a safe filesystem filename."""
    clean = re.sub(r'[\\/*?:"<>|]', "", name)
    clean = clean.strip().replace(" ", "_").lower()
    return clean[:50] or "jarvis_doc"


def _build_bento_grid(metrics: List[Dict[str, Any]], theme_cfg: Dict[str, Any], body_font: str, head_font: str) -> Table:
    """Construct a 2x2 or 2xN Bento Grid metric callout panel.

    Args:
        metrics: List of metric dicts with 'label' and 'value'.
        theme_cfg: Active theme configuration.
        body_font: Base body font name.
        head_font: Bold heading font name.

    Returns:
        Table: Styled ReportLab Table representing the Bento Grid.
    """
    bento_cfg = theme_cfg.get("bento", {})
    card_bg = colors.HexColor(bento_cfg.get("card_bg", theme_cfg.get("card_bg", "#F8FAFC")))
    border_col = colors.HexColor(bento_cfg.get("border_color", theme_cfg.get("primary_color", "#1E40AF")))
    metric_col = colors.HexColor(bento_cfg.get("metric_color", theme_cfg.get("primary_color", "#1E40AF")))
    label_col = colors.HexColor(bento_cfg.get("label_color", theme_cfg.get("subtitle_color", "#64748B")))

    metric_style = ParagraphStyle(
        name="BentoMetric",
        fontName=head_font,
        fontSize=20,
        leading=24,
        textColor=metric_col,
        alignment=0,
    )
    label_style = ParagraphStyle(
        name="BentoLabel",
        fontName=body_font,
        fontSize=9.5,
        leading=13,
        textColor=label_col,
        alignment=0,
    )

    card_cells = []
    for item in metrics:
        val = str(item.get("value", ""))
        lbl = str(item.get("label", item.get("title", "")))

        # Handle Devanagari in metric labels
        c_val_font = theme_cfg.get("devanagari_bold_font", head_font) if contains_devanagari(val) else head_font
        c_lbl_font = theme_cfg.get("devanagari_font", body_font) if contains_devanagari(lbl) else body_font

        v_style = ParagraphStyle("BMVal", parent=metric_style, fontName=c_val_font)
        l_style = ParagraphStyle("BMLbl", parent=label_style, fontName=c_lbl_font)

        cell_flowables = [
            Paragraph(f"<b>{val}</b>", v_style),
            Spacer(1, 3),
            Paragraph(lbl, l_style),
        ]
        card_cells.append(cell_flowables)

    # Arrange into 2 columns
    grid_rows: List[List[Any]] = []
    for i in range(0, len(card_cells), 2):
        row = [card_cells[i]]
        if i + 1 < len(card_cells):
            row.append(card_cells[i + 1])
        else:
            row.append("")
        grid_rows.append(row)

    table = Table(grid_rows, colWidths=[246, 246])
    table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), card_bg),
            ("BOX", (0, 0), (-1, -1), 1.2, border_col),
            ("INNERGRID", (0, 0), (-1, -1), 1, colors.HexColor(theme_cfg.get("border_color", "#CBD5E1"))),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ])
    )
    return table


def make_pdf(
    title: str,
    sections: List[Dict[str, Any]],
    theme: str = "clean_light",
    out_dir: str = "workspace",
    subtitle: Optional[str] = None,
    auto_open: bool = True,
) -> str:
    """Build a themed, Claude-quality PDF document using ReportLab Platypus.

    Args:
        title: Title of the document.
        sections: List of section dictionaries. Each can include:
            - 'heading' (str): Section title.
            - 'text' (str): Narrative body paragraph.
            - 'bullets' (list[str]): Bullet points.
            - 'metrics' (list[dict], optional): Bento grid metrics with 'label' and 'value'.
            - 'table' (list[list[str]], optional): 2D list of table rows.
            - 'page_break_after' (bool, optional): Force page break after section.
        theme: Theme name ('clean_light', 'dark_pro', 'colourful').
        out_dir: Output directory.
        subtitle: Optional subtitle for executive cover page.
        auto_open: If True, opens the generated PDF in the default Windows viewer.

    Returns:
        str: Absolute filesystem path to the created PDF document.
    """
    try:
        # Register TrueType Devanagari font (Noto Sans Devanagari)
        dev_registered = register_devanagari_fonts()

        theme_cfg = get_theme(theme)
        target_dir = Path(out_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        safe_name = _sanitize_filename(title)
        out_path = target_dir / f"{safe_name}_{theme_cfg['name']}.pdf"

        # Initialize document template
        margin_pt = theme_cfg["spacing"]["margin"]
        doc = SimpleDocTemplate(
            str(out_path),
            pagesize=letter,
            leftMargin=margin_pt,
            rightMargin=margin_pt,
            topMargin=margin_pt,
            bottomMargin=margin_pt + 15,
        )

        # Style palette setup
        styles = getSampleStyleSheet()
        primary_col = colors.HexColor(theme_cfg["primary_color"])
        secondary_col = colors.HexColor(theme_cfg["secondary_color"])
        text_col = colors.HexColor(theme_cfg["text_color"])
        accent_col = colors.HexColor(theme_cfg["accent_color"])
        card_bg_col = colors.HexColor(theme_cfg["card_bg"])
        border_col = colors.HexColor(theme_cfg["border_color"])
        sub_col = colors.HexColor(theme_cfg.get("subtitle_color", "#64748B"))

        # Check title script
        is_title_dev = contains_devanagari(title)
        head_font = theme_cfg.get("devanagari_bold_font", "NotoSansDevanagari-Bold") if (is_title_dev and dev_registered) else theme_cfg.get("heading_font", "Helvetica-Bold")
        body_font = theme_cfg.get("devanagari_font", "NotoSansDevanagari") if (is_title_dev and dev_registered) else theme_cfg.get("body_font", "Helvetica")

        # Custom paragraph styles
        cover_title_style = ParagraphStyle(
            name="CoverTitle",
            parent=styles["Title"],
            fontName=head_font,
            fontSize=theme_cfg["spacing"]["title_size"],
            leading=theme_cfg["spacing"]["title_size"] + 8,
            textColor=primary_col,
            alignment=0,
            spaceAfter=12,
        )

        cover_sub_style = ParagraphStyle(
            name="CoverSubtitle",
            parent=styles["Normal"],
            fontName=body_font,
            fontSize=13,
            leading=18,
            textColor=sub_col,
            spaceAfter=30,
        )

        heading_style = ParagraphStyle(
            name="SectionHeading",
            parent=styles["Heading1"],
            fontName=head_font,
            fontSize=theme_cfg["spacing"]["heading_size"],
            leading=theme_cfg["spacing"]["heading_size"] + 6,
            textColor=primary_col,
            spaceBefore=16,
            spaceAfter=8,
            keepWithNext=True,
        )

        body_style = ParagraphStyle(
            name="SectionBody",
            parent=styles["Normal"],
            fontName=body_font,
            fontSize=theme_cfg["spacing"]["body_size"],
            leading=theme_cfg["spacing"]["line_spacing"],
            textColor=text_col,
            spaceAfter=8,
        )

        bullet_style = ParagraphStyle(
            name="SectionBullet",
            parent=styles["Normal"],
            fontName=body_font,
            fontSize=theme_cfg["spacing"]["bullet_size"],
            leading=theme_cfg["spacing"]["bullet_size"] + 5,
            textColor=text_col,
            leftIndent=15,
            firstLineIndent=-10,
            spaceAfter=4,
        )

        table_cell_style = ParagraphStyle(
            name="TableCell",
            parent=styles["Normal"],
            fontName=body_font,
            fontSize=9.5,
            leading=13,
            textColor=text_col,
        )

        table_header_style = ParagraphStyle(
            name="TableHeaderCell",
            parent=styles["Normal"],
            fontName=head_font,
            fontSize=10,
            leading=14,
            textColor=colors.HexColor(theme_cfg["table_header_text"]),
        )

        meta_label_style = ParagraphStyle(
            name="MetaLabel",
            parent=styles["Normal"],
            fontName=head_font,
            fontSize=9,
            leading=12,
            textColor=sub_col,
        )
        meta_value_style = ParagraphStyle(
            name="MetaVal",
            parent=styles["Normal"],
            fontName=body_font,
            fontSize=10,
            leading=13,
            textColor=text_col,
        )

        story: List[Any] = []

        # -------------------------------------------------------------
        # 1. Executive Cover Page
        # -------------------------------------------------------------
        story.append(Spacer(1, 90))

        # Title
        story.append(Paragraph(title, cover_title_style))

        # Subtitle
        sub_text = subtitle or "JARVIS Autonomous Intelligence • Executive Document"
        sub_font = theme_cfg.get("devanagari_font", body_font) if (contains_devanagari(sub_text) and dev_registered) else body_font
        story.append(Paragraph(sub_text, ParagraphStyle("ExecSub", parent=cover_sub_style, fontName=sub_font)))

        story.append(
            HRFlowable(
                width="100%",
                thickness=3,
                color=secondary_col,
                spaceBefore=5,
                spaceAfter=35,
            )
        )

        # Executive Metadata Card
        meta_table_data = [
            [
                Paragraph("<b>AUTHOR:</b>", meta_label_style),
                Paragraph("Vidhita (Document Engineer) • Pair D", meta_value_style),
                Paragraph("<b>STATUS:</b>", meta_label_style),
                Paragraph("Production Verified", meta_value_style),
            ],
            [
                Paragraph("<b>THEME:</b>", meta_label_style),
                Paragraph(theme_cfg["name"].replace("_", " ").title(), meta_value_style),
                Paragraph("<b>ENGINE:</b>", meta_label_style),
                Paragraph("ReportLab Platypus", meta_value_style),
            ],
        ]
        meta_table = Table(meta_table_data, colWidths=[65, 185, 65, 175])
        meta_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), card_bg_col),
                ("BOX", (0, 0), (-1, -1), 1.2, border_col),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, border_col),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ])
        )
        story.append(meta_table)
        story.append(Spacer(1, 140))

        story.append(
            HRFlowable(
                width="100%",
                thickness=1,
                color=border_col,
                spaceBefore=10,
                spaceAfter=15,
            )
        )
        story.append(PageBreak())

        # -------------------------------------------------------------
        # 2. Content Sections
        # -------------------------------------------------------------
        for idx, sec in enumerate(sections):
            heading = sec.get("heading")
            if heading:
                h_font = theme_cfg.get("devanagari_bold_font", head_font) if (contains_devanagari(heading) and dev_registered) else head_font
                cur_h_style = ParagraphStyle("SecH", parent=heading_style, fontName=h_font)
                story.append(Paragraph(heading, cur_h_style))
                story.append(
                    HRFlowable(
                        width="100%",
                        thickness=0.75,
                        color=secondary_col,
                        spaceBefore=2,
                        spaceAfter=8,
                    )
                )

            body_text = sec.get("text")
            if body_text:
                b_font = theme_cfg.get("devanagari_font", body_font) if (contains_devanagari(body_text) and dev_registered) else body_font
                cur_b_style = ParagraphStyle("SecB", parent=body_style, fontName=b_font)
                story.append(Paragraph(body_text, cur_b_style))

            # Bento Grid Metric Callout Cards
            metrics = sec.get("metrics") or sec.get("bento_cards")
            if metrics and isinstance(metrics, list):
                story.append(Spacer(1, 4))
                bento_tbl = _build_bento_grid(metrics, theme_cfg, body_font, head_font)
                story.append(bento_tbl)
                story.append(Spacer(1, 8))

            bullets = sec.get("bullets", [])
            if bullets:
                for bullet in bullets:
                    bullet_font = theme_cfg.get("devanagari_font", body_font) if (contains_devanagari(bullet) and dev_registered) else body_font
                    cur_bl_style = ParagraphStyle("SecBl", parent=bullet_style, fontName=bullet_font)
                    bullet_text = f"&bull; &nbsp; {bullet}"
                    story.append(Paragraph(bullet_text, cur_bl_style))
                story.append(Spacer(1, 8))

            table_data = sec.get("table")
            if table_data and isinstance(table_data, list):
                flowable_table_data = []
                for row_idx, row in enumerate(table_data):
                    styled_row = []
                    for cell in row:
                        c_str = str(cell)
                        c_font = theme_cfg.get("devanagari_font", body_font) if (contains_devanagari(c_str) and dev_registered) else body_font
                        if row_idx == 0:
                            h_cell_font = theme_cfg.get("devanagari_bold_font", head_font) if (contains_devanagari(c_str) and dev_registered) else head_font
                            c_style = ParagraphStyle("THC", parent=table_header_style, fontName=h_cell_font)
                            styled_row.append(Paragraph(c_str, c_style))
                        else:
                            c_style = ParagraphStyle("TDC", parent=table_cell_style, fontName=c_font)
                            styled_row.append(Paragraph(c_str, c_style))
                    flowable_table_data.append(styled_row)

                tbl = Table(flowable_table_data, colWidths=None)
                tbl.setStyle(
                    TableStyle([
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(theme_cfg["table_header_bg"])),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                        ("TOPPADDING", (0, 0), (-1, 0), 6),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor(theme_cfg["card_bg"]), colors.HexColor(theme_cfg["table_row_alt"])]),
                        ("INNERGRID", (0, 0), (-1, -1), 0.5, border_col),
                        ("BOX", (0, 0), (-1, -1), 1, border_col),
                        ("TOPPADDING", (0, 1), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
                        ("LEFTPADDING", (0, 0), (-1, -1), 8),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ])
                )
                story.append(Spacer(1, 6))
                story.append(tbl)
                story.append(Spacer(1, 12))

            # Chart Embedding (Day 4 Deliverable)
            chart_cfg = sec.get("chart")
            chart_path = sec.get("chart_path") or sec.get("image_path")
            if chart_cfg and isinstance(chart_cfg, dict):
                try:
                    c_type = chart_cfg.get("type", "bar")
                    c_data = chart_cfg.get("data", {})
                    c_title = chart_cfg.get("title", f"{heading} Chart")
                    chart_path = generate_chart(
                        chart_type=c_type,
                        data=c_data,
                        title=c_title,
                        theme=theme,
                        out_dir=out_dir,
                    )
                except Exception as _c_err:
                    chart_path = None

            if chart_path and os.path.exists(chart_path):
                try:
                    c_img = RLImage(chart_path, width=440, height=230)
                    c_img.hAlign = "CENTER"
                    story.append(Spacer(1, 6))
                    story.append(c_img)
                    story.append(Spacer(1, 10))
                except Exception:
                    pass

            if sec.get("page_break_after") and idx < len(sections) - 1:
                story.append(PageBreak())
            else:
                story.append(Spacer(1, 10))

        # Build document with custom canvas and executive background callback
        def on_first(canv: canvas.Canvas, d: SimpleDocTemplate) -> None:
            _draw_page_background(canv, d, theme_cfg, is_cover=True)

        def on_later(canv: canvas.Canvas, d: SimpleDocTemplate) -> None:
            _draw_page_background(canv, d, theme_cfg, is_cover=False)

        doc.build(
            story,
            onFirstPage=on_first,
            onLaterPages=on_later,
            canvasmaker=lambda *args, **kwargs: _init_canvas(
                args, kwargs, theme_cfg=theme_cfg, doc_title=title
            ),
        )

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
        raise RuntimeError(f"make_pdf failed for '{title}': {exc}") from exc


def _init_canvas(args: tuple, kwargs: dict, theme_cfg: dict, doc_title: str) -> NumberedCanvas:
    """Helper to initialize NumberedCanvas with document parameters."""
    canv = NumberedCanvas(*args, **kwargs)
    setattr(canv, "_theme_cfg", theme_cfg)
    setattr(canv, "_doc_title", doc_title)
    return canv
