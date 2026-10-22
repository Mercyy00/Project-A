"""Day 2: Themed PDF Maker using ReportLab Platypus.

Author: Vidhita (Document Engineer)
Module: creator.pdf_maker

Generates beautifully styled, multi-page PDFs with:
- Cover page with large title and metadata
- Themed headings, paragraphs, and bullet points
- Formatted tables with header and alternating row colors
- Dynamic footer with page numbers ('Page X of Y')
- Support for 'clean_light', 'dark_pro', and 'colourful' themes
"""

import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    HRFlowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

from creator.themes import THEMES, get_theme


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute and draw total page count and footer."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._saved_page_states: List[Dict[str, Any]] = []

    def showPage(self) -> None:
        """Capture page state and defer final drawing until save."""
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        """Draw footers on each captured page with total page count."""
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

                # Footer line
                self.line(54, 45, 612 - 54, 45)

                # Left: Document Title
                self.drawString(54, 32, f"{doc_title}")

                # Right: Page X of Y
                page_str = f"Page {page_num} of {num_pages}"
                self.drawRightString(612 - 54, 32, page_str)
                self.restoreState()

            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)


def _draw_page_background(canvas_obj: canvas.Canvas, doc: SimpleDocTemplate, bg_hex: str) -> None:
    """Draw full-page background color before flowables are placed.

    Args:
        canvas_obj: ReportLab canvas instance.
        doc: Document template.
        bg_hex: Background color in hex format.
    """
    canvas_obj.saveState()
    canvas_obj.setFillColor(colors.HexColor(bg_hex))
    canvas_obj.rect(0, 0, doc.pagesize[0], doc.pagesize[1], fill=1, stroke=0)
    canvas_obj.restoreState()


def _sanitize_filename(name: str) -> str:
    """Sanitize title to produce a clean, safe filename."""
    clean = re.sub(r'[\\/*?:"<>|]', "", name)
    clean = clean.strip().replace(" ", "_").lower()
    return clean[:50] or "jarvis_doc"


def make_pdf(
    title: str,
    sections: List[Dict[str, Any]],
    theme: str = "clean_light",
    out_dir: str = "workspace",
) -> str:
    """Build a themed PDF using ReportLab Platypus.

    Args:
        title: Title of the document.
        sections: List of section dictionaries. Each dictionary can contain:
            - 'heading' (str): Section title.
            - 'text' (str): Section body narrative.
            - 'bullets' (list[str]): List of bullet points.
            - 'table' (list[list[str]], optional): 2D list of table rows.
            - 'page_break_after' (bool, optional): Force page break after section.
        theme: Theme name ('clean_light', 'dark_pro', 'colourful').
               Defaults to 'clean_light' if unknown.
        out_dir: Directory where the output PDF will be saved.

    Returns:
        Absolute string path to the created PDF file.
    """
    try:
        theme_cfg = get_theme(theme)
        target_dir = Path(out_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        safe_name = _sanitize_filename(title)
        out_path = target_dir / f"{safe_name}_{theme_cfg['name']}.pdf"

        # Initialize document template
        doc = SimpleDocTemplate(
            str(out_path),
            pagesize=letter,
            leftMargin=theme_cfg["spacing"]["margin"],
            rightMargin=theme_cfg["spacing"]["margin"],
            topMargin=theme_cfg["spacing"]["margin"],
            bottomMargin=theme_cfg["spacing"]["margin"] + 15,
        )

        # Style sheet setup
        styles = getSampleStyleSheet()
        primary_col = colors.HexColor(theme_cfg["primary_color"])
        secondary_col = colors.HexColor(theme_cfg["secondary_color"])
        text_col = colors.HexColor(theme_cfg["text_color"])
        accent_col = colors.HexColor(theme_cfg["accent_color"])
        card_bg_col = colors.HexColor(theme_cfg["card_bg"])
        border_col = colors.HexColor(theme_cfg["border_color"])

        head_font = theme_cfg.get("heading_font", "Helvetica-Bold")
        body_font = theme_cfg.get("body_font", "Helvetica")

        # Custom paragraph styles
        cover_title_style = ParagraphStyle(
            name="CoverTitle",
            parent=styles["Title"],
            fontName=head_font,
            fontSize=34,
            leading=40,
            textColor=primary_col,
            alignment=0,  # Left align
            spaceAfter=15,
        )

        cover_sub_style = ParagraphStyle(
            name="CoverSubtitle",
            parent=styles["Normal"],
            fontName=body_font,
            fontSize=14,
            leading=20,
            textColor=secondary_col,
            spaceAfter=25,
        )

        meta_style = ParagraphStyle(
            name="CoverMeta",
            parent=styles["Normal"],
            fontName=body_font,
            fontSize=11,
            leading=16,
            textColor=text_col,
        )

        heading_style = ParagraphStyle(
            name="SectionHeading",
            parent=styles["Heading1"],
            fontName=head_font,
            fontSize=theme_cfg["spacing"]["heading_size"],
            leading=theme_cfg["spacing"]["heading_size"] + 6,
            textColor=primary_col,
            spaceBefore=14,
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
            fontSize=10,
            leading=13,
            textColor=text_col,
        )

        table_header_style = ParagraphStyle(
            name="TableHeaderCell",
            parent=styles["Normal"],
            fontName=head_font,
            fontSize=10,
            leading=13,
            textColor=colors.HexColor(theme_cfg["table_header_text"]),
        )

        story: List[Any] = []

        # -------------------------------------------------------------
        # 1. Cover Page
        # -------------------------------------------------------------
        story.append(Spacer(1, 100))
        story.append(
            HRFlowable(
                width="100%",
                thickness=4,
                color=accent_col,
                spaceBefore=0,
                spaceAfter=25,
            )
        )
        story.append(Paragraph(title, cover_title_style))
        story.append(
            Paragraph("JARVIS Autonomous Document Engine · System Report", cover_sub_style)
        )
        story.append(Spacer(1, 120))

        story.append(
            Paragraph(
                f"<b>Theme:</b> {theme_cfg['name']} &nbsp;|&nbsp; <b>Author:</b> Vidhita (Documents)",
                meta_style,
            )
        )
        story.append(
            Paragraph(
                "<b>Status:</b> Production Ready &nbsp;|&nbsp; <b>Engine:</b> ReportLab Platypus",
                meta_style,
            )
        )
        story.append(
            HRFlowable(
                width="100%",
                thickness=1,
                color=border_col,
                spaceBefore=15,
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
                story.append(Paragraph(heading, heading_style))
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
                story.append(Paragraph(body_text, body_style))

            bullets = sec.get("bullets", [])
            if bullets:
                for bullet in bullets:
                    bullet_text = f"&bull; &nbsp; {bullet}"
                    story.append(Paragraph(bullet_text, bullet_style))
                story.append(Spacer(1, 8))

            table_data = sec.get("table")
            if table_data and isinstance(table_data, list):
                flowable_table_data = []
                for row_idx, row in enumerate(table_data):
                    styled_row = []
                    for cell in row:
                        if row_idx == 0:
                            styled_row.append(Paragraph(str(cell), table_header_style))
                        else:
                            styled_row.append(Paragraph(str(cell), table_cell_style))
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

            if sec.get("page_break_after") and idx < len(sections) - 1:
                story.append(PageBreak())
            else:
                story.append(Spacer(1, 10))

        # Build document with custom canvas and page background callback
        bg_hex = theme_cfg.get("bg_color", "#FFFFFF")

        def on_page(canv: canvas.Canvas, d: SimpleDocTemplate) -> None:
            _draw_page_background(canv, d, bg_hex)

        doc.build(
            story,
            onFirstPage=on_page,
            onLaterPages=on_page,
            canvasmaker=lambda *args, **kwargs: _init_canvas(
                args, kwargs, theme_cfg=theme_cfg, doc_title=title
            ),
        )

        return str(out_path.resolve())

    except Exception as exc:
        raise RuntimeError(f"make_pdf failed for '{title}': {exc}") from exc


def _init_canvas(args: tuple, kwargs: dict, theme_cfg: dict, doc_title: str) -> NumberedCanvas:
    """Helper to initialize NumberedCanvas with document parameters."""
    canv = NumberedCanvas(*args, **kwargs)
    setattr(canv, "_theme_cfg", theme_cfg)
    setattr(canv, "_doc_title", doc_title)
    return canv
