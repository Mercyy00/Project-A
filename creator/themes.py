"""Themes configuration for JARVIS Document Creator (Claude-Quality Elevation).

Author: Document Engineer
Module: creator.themes

Defines theme palettes, typography, bento-grid card styles, executive cover page
geometry, and comprehensive font embedding (TrueType and Google Web Fonts) for
PDF, DOCX, PPTX, and HTML Website / Web Artifact generators.

Integrated with Anthropic's Claude Skills (Theme Factory, Frontend Design, PPTX & DOCX guidelines):
- 'clean_light': Crisp corporate design, navy/slate palette, clear structure.
- 'dark_pro': High-contrast dark theme, slate/cyan palette, modern tech aesthetic.
- 'colourful': Vibrant expressive theme, purple/coral/warm palette, creative tone.
- 'tech_innovation': Electric blue, neon cyan, dark charcoal, cutting-edge tech.
- 'ocean_depths': Deep maritime navy, teal, seafoam, calm executive tone.
- 'forest_moss': Forest green, moss, cream, organic and sustainability focus.
- 'midnight_executive': Executive midnight navy, ice blue, pearl white.
- 'warm_terracotta': Earthy terracotta, sand, sage green, human-centered editorial.
- 'modern_minimalist': Pure charcoal, crisp bone white, subtle slate borders.
- 'sunset_boulevard': Rich plum, sunset rose, warm golden accents.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Fonts directory
FONTS_DIR: Path = Path(__file__).resolve().parent / "fonts"
DEVANAGARI_REGULAR: Path = FONTS_DIR / "NotoSansDevanagari-Regular.ttf"
DEVANAGARI_BOLD: Path = FONTS_DIR / "NotoSansDevanagari-Bold.ttf"

_fonts_registered: bool = False
_registered_font_names: List[str] = []


def register_all_fonts() -> List[str]:
    """Register all available TrueType fonts in creator/fonts/ into ReportLab.

    Prevents tofu / missing character glitches, supports multilingual documents
    (Hindi, Marathi, English), and enables executive typography (Georgia, Calibri,
    Segoe UI, Bahnschrift, Consolas, Trebuchet, Verdana, Arial).

    Returns:
        List[str]: Names of successfully registered fonts.
    """
    global _fonts_registered, _registered_font_names
    if _fonts_registered:
        return _registered_font_names

    registered: List[str] = []
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        if FONTS_DIR.exists():
            for ttf_path in sorted(FONTS_DIR.glob("*.ttf")):
                font_name = ttf_path.stem
                try:
                    pdfmetrics.registerFont(TTFont(font_name, str(ttf_path)))
                    registered.append(font_name)
                except Exception:
                    pass

        # Standard aliases for Devanagari backward compatibility
        if DEVANAGARI_REGULAR.exists():
            try:
                pdfmetrics.registerFont(TTFont("NotoSansDevanagari", str(DEVANAGARI_REGULAR)))
                registered.append("NotoSansDevanagari")
            except Exception:
                pass
        if DEVANAGARI_BOLD.exists():
            try:
                pdfmetrics.registerFont(TTFont("NotoSansDevanagari-Bold", str(DEVANAGARI_BOLD)))
                registered.append("NotoSansDevanagari-Bold")
            except Exception:
                pass

        # Windows system Devanagari fallback if needed
        if "NotoSansDevanagari" not in registered:
            win_nirmala = Path("C:/Windows/Fonts/Nirmala.ttf")
            if win_nirmala.exists():
                try:
                    pdfmetrics.registerFont(TTFont("NotoSansDevanagari", str(win_nirmala)))
                    pdfmetrics.registerFont(TTFont("NotoSansDevanagari-Bold", str(win_nirmala)))
                    registered.extend(["NotoSansDevanagari", "NotoSansDevanagari-Bold"])
                except Exception:
                    pass

        _registered_font_names = registered
        _fonts_registered = True
        return registered
    except Exception:
        return registered


def register_devanagari_fonts() -> bool:
    """Backward-compatible wrapper to register Devanagari and system fonts.

    Returns:
        bool: True if at least one font was registered, False otherwise.
    """
    names = register_all_fonts()
    return len(names) > 0


def contains_devanagari(text: Any) -> bool:
    """Detect whether a string contains Devanagari characters (Hindi or Marathi).

    Args:
        text: Input string or value to test.

    Returns:
        bool: True if any character falls in the Devanagari Unicode block (U+0900 - U+097F).
    """
    if not text:
        return False
    s = str(text)
    return any("\u0900" <= ch <= "\u097f" for ch in s)


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
        "bento": {
            "card_bg": "#F8FAFC",
            "border_color": "#3B82F6",
            "metric_color": "#1E40AF",
            "label_color": "#64748B",
            "title_color": "#0F172A",
        },
        "table_header_bg": "#1E40AF",
        "table_header_text": "#FFFFFF",
        "table_row_alt": "#F1F5F9",
        "table_border": "#E2E8F0",
        "heading_font": "Helvetica-Bold",
        "body_font": "Helvetica",
        "devanagari_font": "NotoSansDevanagari",
        "devanagari_bold_font": "NotoSansDevanagari-Bold",
        "font_family_name": "Arial",
        "web_font_import": "https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&family=Noto+Sans+Devanagari:wght@400;600;700&display=swap",
        "web_font_family": "'Plus Jakarta Sans', 'Noto Sans Devanagari', -apple-system, sans-serif",
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
        "bento": {
            "card_bg": "#1E293B",
            "border_color": "#38BDF8",
            "metric_color": "#38BDF8",
            "label_color": "#94A3B8",
            "title_color": "#F8FAFC",
        },
        "table_header_bg": "#0284C7",      # Sky-600
        "table_header_text": "#FFFFFF",
        "table_row_alt": "#1E293B",
        "table_border": "#334155",
        "heading_font": "Helvetica-Bold",
        "body_font": "Helvetica",
        "devanagari_font": "NotoSansDevanagari",
        "devanagari_bold_font": "NotoSansDevanagari-Bold",
        "font_family_name": "Calibri",
        "web_font_import": "https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700;800&family=JetBrains+Mono:wght@400;600&family=Noto+Sans+Devanagari:wght@400;600;700&display=swap",
        "web_font_family": "'Outfit', 'Noto Sans Devanagari', -apple-system, sans-serif",
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
        "bento": {
            "card_bg": "#FDF4FF",
            "border_color": "#EC4899",
            "metric_color": "#7C3AED",
            "label_color": "#6B21A8",
            "title_color": "#1E1B4B",
        },
        "table_header_bg": "#7C3AED",
        "table_header_text": "#FFFFFF",
        "table_row_alt": "#FCE7F3",
        "table_border": "#FBCFE8",
        "heading_font": "Helvetica-Bold",
        "body_font": "Helvetica",
        "devanagari_font": "NotoSansDevanagari",
        "devanagari_bold_font": "NotoSansDevanagari-Bold",
        "font_family_name": "Georgia",
        "web_font_import": "https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,600;0,800;1,400&family=Plus+Jakarta+Sans:wght@400;600&family=Noto+Sans+Devanagari:wght@400;600&display=swap",
        "web_font_family": "'Plus Jakarta Sans', 'Noto Sans Devanagari', sans-serif",
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
    # --- Claude / Anthropic Theme Factory & Skill Additions ---
    "tech_innovation": {
        "name": "tech_innovation",
        "description": "High-impact tech aesthetic with electric blue, cyan highlights, and deep charcoal.",
        "bg_color": "#111827",             # Dark Charcoal
        "text_color": "#F9FAFB",           # Crisp White
        "primary_color": "#0066FF",        # Electric Blue
        "secondary_color": "#06B6D4",      # Bright Cyan
        "accent_color": "#10B981",         # Emerald Green
        "card_bg": "#1F2937",              # Slate Gray Card
        "border_color": "#374151",         # Divider border
        "cover_stripe_color": "#0066FF",
        "subtitle_color": "#9CA3AF",
        "bento": {
            "card_bg": "#1F2937",
            "border_color": "#0066FF",
            "metric_color": "#06B6D4",
            "label_color": "#9CA3AF",
            "title_color": "#FFFFFF",
        },
        "table_header_bg": "#0066FF",
        "table_header_text": "#FFFFFF",
        "table_row_alt": "#1F2937",
        "table_border": "#374151",
        "heading_font": "Helvetica-Bold",
        "body_font": "Helvetica",
        "devanagari_font": "NotoSansDevanagari",
        "devanagari_bold_font": "NotoSansDevanagari-Bold",
        "font_family_name": "Segoe UI",
        "web_font_import": "https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=JetBrains+Mono:wght@400;600&family=Plus+Jakarta+Sans:wght@400;600&family=Noto+Sans+Devanagari:wght@400;600&display=swap",
        "web_font_family": "'Plus Jakarta Sans', 'Space Grotesk', -apple-system, sans-serif",
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
    "ocean_depths": {
        "name": "ocean_depths",
        "description": "Calm, trustworthy maritime aesthetic with deep navy, teal, seafoam, and cream.",
        "bg_color": "#F0FDF4",             # Crisp seafoam-tinted light bg
        "text_color": "#132A3E",           # Deep maritime slate
        "primary_color": "#0E7490",        # Deep Cyan / Teal
        "secondary_color": "#0284C7",      # Sky blue
        "accent_color": "#14B8A6",         # Seafoam accent
        "card_bg": "#FFFFFF",              # Clean card surface
        "border_color": "#BAE6FD",         # Ice blue border
        "cover_stripe_color": "#0E7490",
        "subtitle_color": "#475569",
        "bento": {
            "card_bg": "#E0F2FE",
            "border_color": "#0284C7",
            "metric_color": "#0E7490",
            "label_color": "#475569",
            "title_color": "#132A3E",
        },
        "table_header_bg": "#0E7490",
        "table_header_text": "#FFFFFF",
        "table_row_alt": "#F0F9FF",
        "table_border": "#BAE6FD",
        "heading_font": "Helvetica-Bold",
        "body_font": "Helvetica",
        "devanagari_font": "NotoSansDevanagari",
        "devanagari_bold_font": "NotoSansDevanagari-Bold",
        "font_family_name": "Calibri",
        "web_font_import": "https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700&family=Noto+Sans+Devanagari:wght@400;600;700&display=swap",
        "web_font_family": "'Outfit', 'Noto Sans Devanagari', sans-serif",
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
    "forest_moss": {
        "name": "forest_moss",
        "description": "Organic, grounded palette of deep forest green, moss, and warm cream.",
        "bg_color": "#FDFBF7",             # Warm linen cream
        "text_color": "#14281D",           # Deep evergreen
        "primary_color": "#2C5F2D",        # Forest Green
        "secondary_color": "#65A30D",      # Moss Lime
        "accent_color": "#D97706",         # Warm amber
        "card_bg": "#F4F7F2",              # Soft sage card
        "border_color": "#CBD5C0",         # Muted moss border
        "cover_stripe_color": "#2C5F2D",
        "subtitle_color": "#4B5563",
        "bento": {
            "card_bg": "#F4F7F2",
            "border_color": "#65A30D",
            "metric_color": "#2C5F2D",
            "label_color": "#4B5563",
            "title_color": "#14281D",
        },
        "table_header_bg": "#2C5F2D",
        "table_header_text": "#FFFFFF",
        "table_row_alt": "#F2F6EF",
        "table_border": "#CBD5C0",
        "heading_font": "Helvetica-Bold",
        "body_font": "Helvetica",
        "devanagari_font": "NotoSansDevanagari",
        "devanagari_bold_font": "NotoSansDevanagari-Bold",
        "font_family_name": "Georgia",
        "web_font_import": "https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700&family=Noto+Sans+Devanagari:wght@400;600&display=swap",
        "web_font_family": "'Plus Jakarta Sans', 'Noto Sans Devanagari', sans-serif",
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
    "midnight_executive": {
        "name": "midnight_executive",
        "description": "Executive high-contrast authority with midnight navy, ice blue, and pearl white.",
        "bg_color": "#0B1120",             # Midnight Navy
        "text_color": "#F8FAFC",           # Pearl White
        "primary_color": "#3B82F6",        # Royal Blue
        "secondary_color": "#60A5FA",      # Ice Blue
        "accent_color": "#E2E8F0",         # Clean Platinum
        "card_bg": "#1E293B",              # Navy Slate
        "border_color": "#334155",         # Slate Border
        "cover_stripe_color": "#3B82F6",
        "subtitle_color": "#94A3B8",
        "bento": {
            "card_bg": "#1E293B",
            "border_color": "#60A5FA",
            "metric_color": "#60A5FA",
            "label_color": "#94A3B8",
            "title_color": "#FFFFFF",
        },
        "table_header_bg": "#1D4ED8",
        "table_header_text": "#FFFFFF",
        "table_row_alt": "#1E293B",
        "table_border": "#334155",
        "heading_font": "Helvetica-Bold",
        "body_font": "Helvetica",
        "devanagari_font": "NotoSansDevanagari",
        "devanagari_bold_font": "NotoSansDevanagari-Bold",
        "font_family_name": "Segoe UI",
        "web_font_import": "https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&family=Noto+Sans+Devanagari:wght@400;600;700&display=swap",
        "web_font_family": "'Plus Jakarta Sans', 'Noto Sans Devanagari', sans-serif",
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
    "warm_terracotta": {
        "name": "warm_terracotta",
        "description": "Warm, tactile editorial style with terracotta clay, warm sand, and sage.",
        "bg_color": "#FCF9F5",             # Warm Sand Paper
        "text_color": "#292524",           # Charcoal Warm
        "primary_color": "#C2410C",        # Terracotta Rust
        "secondary_color": "#B45309",      # Warm Ochre
        "accent_color": "#4D7C0F",         # Sage Green
        "card_bg": "#F5EFE6",              # Sand Card
        "border_color": "#E7DFD5",         # Sand Border
        "cover_stripe_color": "#C2410C",
        "subtitle_color": "#78716C",
        "bento": {
            "card_bg": "#F5EFE6",
            "border_color": "#C2410C",
            "metric_color": "#C2410C",
            "label_color": "#78716C",
            "title_color": "#292524",
        },
        "table_header_bg": "#C2410C",
        "table_header_text": "#FFFFFF",
        "table_row_alt": "#F5EFE6",
        "table_border": "#E7DFD5",
        "heading_font": "Helvetica-Bold",
        "body_font": "Helvetica",
        "devanagari_font": "NotoSansDevanagari",
        "devanagari_bold_font": "NotoSansDevanagari-Bold",
        "font_family_name": "Georgia",
        "web_font_import": "https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Plus+Jakarta+Sans:wght@400;600&family=Noto+Sans+Devanagari:wght@400;600&display=swap",
        "web_font_family": "'Plus Jakarta Sans', 'Playfair Display', 'Noto Sans Devanagari', serif",
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
    "modern_minimalist": {
        "name": "modern_minimalist",
        "description": "Ultra-clean Swiss typographic editorial with pure charcoal, crisp white, and subtle slate lines.",
        "bg_color": "#FFFFFF",             # Pure White
        "text_color": "#0F172A",           # Deep Slate
        "primary_color": "#0F172A",        # Pure Charcoal
        "secondary_color": "#475569",      # Medium Slate
        "accent_color": "#0284C7",         # Precision Blue
        "card_bg": "#F8FAFC",              # Clean Off-white
        "border_color": "#E2E8F0",         # Hairline Border
        "cover_stripe_color": "#0F172A",
        "subtitle_color": "#64748B",
        "bento": {
            "card_bg": "#F8FAFC",
            "border_color": "#0F172A",
            "metric_color": "#0F172A",
            "label_color": "#64748B",
            "title_color": "#0F172A",
        },
        "table_header_bg": "#0F172A",
        "table_header_text": "#FFFFFF",
        "table_row_alt": "#F8FAFC",
        "table_border": "#E2E8F0",
        "heading_font": "Helvetica-Bold",
        "body_font": "Helvetica",
        "devanagari_font": "NotoSansDevanagari",
        "devanagari_bold_font": "NotoSansDevanagari-Bold",
        "font_family_name": "Arial",
        "web_font_import": "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Noto+Sans+Devanagari:wght@400;600;700&display=swap",
        "web_font_family": "'Inter', 'Noto Sans Devanagari', -apple-system, sans-serif",
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
    "sunset_boulevard": {
        "name": "sunset_boulevard",
        "description": "Atmospheric luxury palette of deep plum, sunset rose, and glowing amber.",
        "bg_color": "#0A0512",             # Deep Plum Black
        "text_color": "#FDF4FF",           # Rose Ivory
        "primary_color": "#E11D48",        # Sunset Rose
        "secondary_color": "#A855F7",      # Neon Purple
        "accent_color": "#F59E0B",         # Warm Amber
        "card_bg": "#180C26",              # Dark Violet Card
        "border_color": "#3B185F",         # Plum Border
        "cover_stripe_color": "#E11D48",
        "subtitle_color": "#D8B4FE",
        "bento": {
            "card_bg": "#180C26",
            "border_color": "#E11D48",
            "metric_color": "#F59E0B",
            "label_color": "#D8B4FE",
            "title_color": "#FFFFFF",
        },
        "table_header_bg": "#E11D48",
        "table_header_text": "#FFFFFF",
        "table_row_alt": "#180C26",
        "table_border": "#3B185F",
        "heading_font": "Helvetica-Bold",
        "body_font": "Helvetica",
        "devanagari_font": "NotoSansDevanagari",
        "devanagari_bold_font": "NotoSansDevanagari-Bold",
        "font_family_name": "Georgia",
        "web_font_import": "https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700;800&family=Noto+Sans+Devanagari:wght@400;600&display=swap",
        "web_font_family": "'Outfit', 'Noto Sans Devanagari', sans-serif",
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

# Aliases for flexible naming
THEME_ALIASES: Dict[str, str] = {
    "tech-innovation": "tech_innovation",
    "techinnovation": "tech_innovation",
    "ocean-depths": "ocean_depths",
    "oceandepths": "ocean_depths",
    "ocean": "ocean_depths",
    "forest-moss": "forest_moss",
    "forest_canopy": "forest_moss",
    "forest-canopy": "forest_moss",
    "forest": "forest_moss",
    "midnight-executive": "midnight_executive",
    "midnightexecutive": "midnight_executive",
    "midnight": "midnight_executive",
    "warm-terracotta": "warm_terracotta",
    "warmterracotta": "warm_terracotta",
    "terracotta": "warm_terracotta",
    "modern-minimalist": "modern_minimalist",
    "modernminimalist": "modern_minimalist",
    "minimalist": "modern_minimalist",
    "sunset-boulevard": "sunset_boulevard",
    "sunsetboulevard": "sunset_boulevard",
    "sunset": "sunset_boulevard",
    "clean-light": "clean_light",
    "dark-pro": "dark_pro",
    "dark": "dark_pro",
    "light": "clean_light",
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
        theme_name: Key or alias of the theme.

    Returns:
        Theme configuration dictionary.
    """
    if not theme_name:
        return THEMES["clean_light"]

    clean_key = theme_name.strip().lower().replace(" ", "_")
    if clean_key in THEMES:
        return THEMES[clean_key]
    if clean_key in THEME_ALIASES:
        return THEMES[THEME_ALIASES[clean_key]]

    return THEMES["clean_light"]
