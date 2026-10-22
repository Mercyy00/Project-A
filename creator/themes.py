"""Themes configuration for JARVIS Document Creator (Claude-Quality Elevation).

Author: Vidhita (Document Engineer)
Module: creator.themes

Defines theme palettes, typography, bento-grid card styles, executive cover page
geometry, and Devanagari font embedding for PDF, DOCX, and PPTX generators.
Themes:
- 'clean_light': Crisp corporate design, navy/slate palette, clear structure.
- 'dark_pro': High-contrast dark theme, slate/cyan palette, modern tech aesthetic.
- 'colourful': Vibrant expressive theme, purple/coral/warm palette, creative tone.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Tuple

# Fonts directory
FONTS_DIR: Path = Path(__file__).resolve().parent / "fonts"
DEVANAGARI_REGULAR: Path = FONTS_DIR / "NotoSansDevanagari-Regular.ttf"
DEVANAGARI_BOLD: Path = FONTS_DIR / "NotoSansDevanagari-Bold.ttf"

_devanagari_registered: bool = False


def register_devanagari_fonts() -> bool:
    """Register Noto Sans Devanagari TrueType fonts into ReportLab.

    Prevents square-box corruption ('tofu') when rendering Hindi or Marathi text.
    Falls back gracefully if fonts cannot be loaded.

    Returns:
        bool: True if font registration succeeded, False otherwise.
    """
    global _devanagari_registered
    if _devanagari_registered:
        return True

    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        registered_any = False
        if DEVANAGARI_REGULAR.exists():
            pdfmetrics.registerFont(TTFont("NotoSansDevanagari", str(DEVANAGARI_REGULAR)))
            registered_any = True

        if DEVANAGARI_BOLD.exists():
            pdfmetrics.registerFont(TTFont("NotoSansDevanagari-Bold", str(DEVANAGARI_BOLD)))
        elif DEVANAGARI_REGULAR.exists():
            pdfmetrics.registerFont(TTFont("NotoSansDevanagari-Bold", str(DEVANAGARI_REGULAR)))

        # Fallback to Windows system Devanagari font if font directory is missing TTF
        if not registered_any:
            win_nirmala = Path("C:/Windows/Fonts/Nirmala.ttf")
            if win_nirmala.exists():
                pdfmetrics.registerFont(TTFont("NotoSansDevanagari", str(win_nirmala)))
                pdfmetrics.registerFont(TTFont("NotoSansDevanagari-Bold", str(win_nirmala)))
                registered_any = True

        _devanagari_registered = registered_any
        return registered_any
    except Exception as exc:
        # Never crash host process on font registration error
        return False


def contains_devanagari(text: str | None) -> bool:
    """Detect whether a string contains Devanagari characters (Hindi or Marathi).

    Args:
        text: Input string to test.

    Returns:
        bool: True if any character falls in the Devanagari Unicode block (U+0900 - U+097F).
    """
    if not text:
        return False
    return any("\u0900" <= ch <= "\u097f" for ch in text)


THEMES: Dict[str, Dict[str, Any]] = {
    "clean_light": {
        "name": "clean_light",
        "description": "Clean, crisp light theme with deep navy and royal blue accents.",
        "bg_color": "#FFFFFF",
        "text_color": "#1E293B",
        "primary_color": "#1E40AF",       # Royal Blue
        "secondary_color": "#3B82F6",     # Bright Blue
        "accent_color": "#0D9488",        # Teal accent
        "card_bg": "#F8FAFC",             # Slate-50
        "border_color": "#CBD5E1",        # Slate-300
        "cover_stripe_color": "#1E40AF",  # Full-bleed cover accent stripe
        "subtitle_color": "#64748B",      # Slate-500
        # Bento Grid Card styling
        "bento": {
            "card_bg": "#F8FAFC",
            "border_color": "#3B82F6",
            "metric_color": "#1E40AF",
            "label_color": "#64748B",
            "title_color": "#0F172A",
        },
        # Modern Table styling
        "table_header_bg": "#1E40AF",
        "table_header_text": "#FFFFFF",
        "table_row_alt": "#F1F5F9",
        "table_border": "#E2E8F0",
        "heading_font": "Helvetica-Bold",
        "body_font": "Helvetica",
        "devanagari_font": "NotoSansDevanagari",
        "devanagari_bold_font": "NotoSansDevanagari-Bold",
        "font_family_name": "Arial",
        "spacing": {
            "margin": 54,  # 0.75 in (54 pt)
            "title_size": 32,
            "heading_size": 20,
            "subheading_size": 14,
            "body_size": 11,
            "bullet_size": 11,
            "line_spacing": 15,
            "paragraph_space": 10,
        },
    },
    "dark_pro": {
        "name": "dark_pro",
        "description": "Professional dark theme with high contrast cyan and slate tones.",
        "bg_color": "#0F172A",             # Slate-900
        "text_color": "#F8FAFC",           # Slate-50
        "primary_color": "#38BDF8",        # Sky Cyan
        "secondary_color": "#818CF8",      # Indigo
        "accent_color": "#34D399",         # Emerald
        "card_bg": "#1E293B",              # Slate-800
        "border_color": "#334155",         # Slate-700
        "cover_stripe_color": "#38BDF8",   # Sky accent stripe
        "subtitle_color": "#94A3B8",       # Slate-400
        # Bento Grid Card styling
        "bento": {
            "card_bg": "#1E293B",
            "border_color": "#38BDF8",
            "metric_color": "#38BDF8",
            "label_color": "#94A3B8",
            "title_color": "#F8FAFC",
        },
        # Modern Table styling
        "table_header_bg": "#0284C7",      # Sky-600
        "table_header_text": "#FFFFFF",
        "table_row_alt": "#1E293B",
        "table_border": "#334155",
        "heading_font": "Helvetica-Bold",
        "body_font": "Helvetica",
        "devanagari_font": "NotoSansDevanagari",
        "devanagari_bold_font": "NotoSansDevanagari-Bold",
        "font_family_name": "Calibri",
        "spacing": {
            "margin": 54,
            "title_size": 32,
            "heading_size": 20,
            "subheading_size": 14,
            "body_size": 11,
            "bullet_size": 11,
            "line_spacing": 15,
            "paragraph_space": 10,
        },
    },
    "colourful": {
        "name": "colourful",
        "description": "Vibrant and expressive theme with warm background and vivid accents.",
        "bg_color": "#FFFDF7",             # Warm Ivory
        "text_color": "#1E1B4B",           # Deep Indigo
        "primary_color": "#7C3AED",        # Purple-600
        "secondary_color": "#EC4899",      # Pink-500
        "accent_color": "#F59E0B",         # Amber-500
        "card_bg": "#FDF4FF",              # Fuchsia-50
        "border_color": "#FBCFE8",         # Pink-200
        "cover_stripe_color": "#7C3AED",   # Purple stripe
        "subtitle_color": "#6B21A8",       # Purple-800
        # Bento Grid Card styling
        "bento": {
            "card_bg": "#FDF4FF",
            "border_color": "#EC4899",
            "metric_color": "#7C3AED",
            "label_color": "#6B21A8",
            "title_color": "#1E1B4B",
        },
        # Modern Table styling
        "table_header_bg": "#7C3AED",
        "table_header_text": "#FFFFFF",
        "table_row_alt": "#FCE7F3",
        "table_border": "#FBCFE8",
        "heading_font": "Helvetica-Bold",
        "body_font": "Helvetica",
        "devanagari_font": "NotoSansDevanagari",
        "devanagari_bold_font": "NotoSansDevanagari-Bold",
        "font_family_name": "Georgia",
        "spacing": {
            "margin": 54,
            "title_size": 32,
            "heading_size": 20,
            "subheading_size": 14,
            "body_size": 11,
            "bullet_size": 11,
            "line_spacing": 15,
            "paragraph_space": 10,
        },
    },
}


def hex_to_rgb(hex_code: str) -> Tuple[int, int, int]:
    """Convert hex color string (#RRGGBB) to (R, G, B) integer tuple.

    Args:
        hex_code: Color string in hex format (e.g., '#1E40AF').

    Returns:
        Tuple of integers (R, G, B) between 0 and 255.
    """
    clean_hex = hex_code.strip().lstrip("#")
    if len(clean_hex) == 3:
        clean_hex = "".join([c * 2 for c in clean_hex])
    if len(clean_hex) != 6:
        return (0, 0, 0)
    return (
        int(clean_hex[0:2], 16),
        int(clean_hex[2:4], 16),
        int(clean_hex[4:6], 16),
    )


def get_theme(theme_name: str | None) -> Dict[str, Any]:
    """Retrieve theme dictionary with graceful fallback to 'clean_light'.

    Args:
        theme_name: Key of the theme ('clean_light', 'dark_pro', 'colourful').

    Returns:
        Theme configuration dictionary.
    """
    if not theme_name or theme_name not in THEMES:
        return THEMES["clean_light"]
    return THEMES[theme_name]
