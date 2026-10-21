"""Themes configuration for JARVIS Document Creator.

Author: Vidhita (Document Engineer)
Module: creator.themes

Defines theme palettes and typography for PDF, DOCX, and PPTX generators.
Includes:
- 'clean_light': Crisp modern design, navy/slate palette, clear structure.
- 'dark_pro': High-contrast dark theme, slate/cyan palette, modern tech aesthetic.
- 'colourful': Vibrant expressive theme, purple/coral/warm palette, creative tone.
"""

from typing import Any, Dict, Tuple


THEMES: Dict[str, Dict[str, Any]] = {
    "clean_light": {
        "name": "clean_light",
        "description": "Clean, crisp light theme with deep navy and royal blue accents.",
        "bg_color": "#FFFFFF",
        "text_color": "#1E293B",
        "primary_color": "#1E40AF",
        "secondary_color": "#3B82F6",
        "accent_color": "#0D9488",
        "card_bg": "#F8FAFC",
        "border_color": "#CBD5E1",
        "table_header_bg": "#1E40AF",
        "table_header_text": "#FFFFFF",
        "table_row_alt": "#F1F5F9",
        "heading_font": "Helvetica-Bold",
        "body_font": "Helvetica",
        "font_family_name": "Arial",
        "spacing": {
            "margin": 54,  # 0.75 in (54 pt)
            "title_size": 30,
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
        "bg_color": "#0F172A",
        "text_color": "#F8FAFC",
        "primary_color": "#38BDF8",
        "secondary_color": "#818CF8",
        "accent_color": "#34D399",
        "card_bg": "#1E293B",
        "border_color": "#334155",
        "table_header_bg": "#0284C7",
        "table_header_text": "#FFFFFF",
        "table_row_alt": "#1E293B",
        "heading_font": "Helvetica-Bold",
        "body_font": "Helvetica",
        "font_family_name": "Calibri",
        "spacing": {
            "margin": 54,
            "title_size": 30,
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
        "bg_color": "#FFFDF7",
        "text_color": "#1E1B4B",
        "primary_color": "#7C3AED",
        "secondary_color": "#EC4899",
        "accent_color": "#F59E0B",
        "card_bg": "#FDF4FF",
        "border_color": "#FBCFE8",
        "table_header_bg": "#7C3AED",
        "table_header_text": "#FFFFFF",
        "table_row_alt": "#FCE7F3",
        "heading_font": "Helvetica-Bold",
        "body_font": "Helvetica",
        "font_family_name": "Georgia",
        "spacing": {
            "margin": 54,
            "title_size": 30,
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
