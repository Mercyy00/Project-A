"""Claude-Quality Web Artifacts & Modern Website Generator.

Author: Document Engineer
Module: creator.web_maker

Implements Anthropic Claude Skills principles:
- 'frontend-design': Distinctive visual identity, opinionated palettes, intentional
  typography hierarchy, responsive layouts, restraint against 'AI slop' defaults.
- 'web-artifacts-builder': Self-contained, single-file HTML/CSS/JS artifacts that run
  instantly in modern web browsers without external build pipelines.
- 'theme-factory': Cohesive color systems across dark, light, and vibrant aesthetic palettes.
- Multilingual Devanagari typography support for English, Hindi, and Marathi.
"""

from __future__ import annotations

import html
import json
import logging
import os
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional
import webbrowser

from creator.themes import (
    THEMES,
    contains_devanagari,
    get_theme,
    hex_to_rgb,
)

logger = logging.getLogger(__name__)


def _sanitize_slug(title: str, max_words: int = 6) -> str:
    """Generate safe, clean filesystem filename slug from a title."""
    clean = re.sub(r"[^\w\s-]", "", title.lower())
    words = clean.split()[:max_words]
    slug = "_".join(words)
    return slug if slug else "artifact"


def make_website(
    title: str,
    sections: List[Dict[str, Any]],
    theme: str = "clean_light",
    out_dir: str = "workspace",
    auto_open: bool = True,
    filename: Optional[str] = None,
    hero_tagline: Optional[str] = None,
    language: str = "en",
    **kwargs: Any,
) -> str:
    """Generate a self-contained, publication-grade responsive website artifact.

    Args:
        title: Main title of the website/artifact.
        sections: List of section dicts containing 'heading', 'text', 'bullets', 'metrics', or 'table'.
        theme: Theme name ('clean_light', 'dark_pro', 'colourful', 'tech_innovation', 'ocean_depths', etc.).
        out_dir: Output directory (defaults to 'workspace').
        auto_open: Whether to automatically launch the file in default browser (default: True).
        filename: Optional custom filename (defaults to '<slug>.html').
        hero_tagline: Optional introductory tagline displayed in hero banner.
        language: Content language ('en', 'hi', 'mr').

    Returns:
        str: Absolute filesystem path to the created HTML file.
    """
    clean_title = (title or "Project Showcase").strip()
    theme_cfg = get_theme(theme)

    # Resolve output directory
    target_dir = Path(out_dir).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    if filename:
        clean_name = filename if filename.endswith(".html") else f"{filename}.html"
    else:
        slug = _sanitize_slug(clean_title)
        theme_suffix = theme_cfg.get("name", "clean_light")
        clean_name = f"{slug}_{theme_suffix}.html"

    out_path = target_dir / clean_name

    # Check Devanagari content
    has_devanagari = contains_devanagari(clean_title) or any(
        contains_devanagari(s.get("heading")) or contains_devanagari(s.get("text"))
        for s in sections if isinstance(s, dict)
    )

    # Extract theme colors
    bg_hex = theme_cfg.get("bg_color", "#FFFFFF")
    text_hex = theme_cfg.get("text_color", "#1E293B")
    primary_hex = theme_cfg.get("primary_color", "#1E40AF")
    secondary_hex = theme_cfg.get("secondary_color", "#3B82F6")
    accent_hex = theme_cfg.get("accent_color", "#0D9488")
    card_bg_hex = theme_cfg.get("card_bg", "#F8FAFC")
    border_hex = theme_cfg.get("border_color", "#CBD5E1")
    subtitle_hex = theme_cfg.get("subtitle_color", "#64748B")

    r_p, g_p, b_p = hex_to_rgb(primary_hex)
    r_a, g_a, b_a = hex_to_rgb(accent_hex)
    r_bg, g_bg, b_bg = hex_to_rgb(bg_hex)

    # Determine if theme is dark
    is_dark = (r_bg * 0.299 + g_bg * 0.587 + b_bg * 0.114) < 128

    web_font_import = theme_cfg.get(
        "web_font_import",
        "https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&family=Noto+Sans+Devanagari:wght@400;600;700&display=swap",
    )
    web_font_family = theme_cfg.get(
        "web_font_family",
        "'Plus Jakarta Sans', 'Noto Sans Devanagari', -apple-system, sans-serif",
    )

    # Aggregate metric cards from all sections
    all_metrics: List[Dict[str, str]] = []
    for s in sections:
        if isinstance(s, dict) and "metrics" in s and isinstance(s["metrics"], list):
            for m in s["metrics"]:
                if isinstance(m, dict) and "label" in m and "value" in m:
                    all_metrics.append({"label": str(m["label"]), "value": str(m["value"])})

    tagline = hero_tagline or (
        sections[0].get("text", "An autonomous, highly sophisticated intelligence artifact.")
        if sections and isinstance(sections[0], dict)
        else "Engineered for clarity, speed, and real-time execution."
    )

    # Build Navigation Links
    nav_items_html = []
    for idx, sec in enumerate(sections):
        if isinstance(sec, dict) and "heading" in sec:
            heading = sec["heading"]
            sec_id = f"sec-{idx + 1}"
            nav_items_html.append(f'<a href="#{sec_id}" class="nav-link">{html.escape(heading)}</a>')

    nav_links_markup = "\n".join(nav_items_html)

    # Build Bento Metric Cards HTML
    metrics_markup = ""
    if all_metrics:
        cards_html = []
        for idx, m in enumerate(all_metrics[:4]):
            val = html.escape(m["value"])
            lbl = html.escape(m["label"])
            cards_html.append(f"""
            <div class="metric-card">
                <div class="metric-badge">0{idx + 1}</div>
                <div class="metric-value">{val}</div>
                <div class="metric-label">{lbl}</div>
                <div class="metric-glow"></div>
            </div>
            """)
        metrics_markup = f"""
        <div class="metrics-grid">
            {''.join(cards_html)}
        </div>
        """

    # Build Content Sections HTML
    sections_markup_list = []
    for idx, sec in enumerate(sections):
        if not isinstance(sec, dict):
            continue

        sec_id = f"sec-{idx + 1}"
        heading = html.escape(str(sec.get("heading", f"Section {idx + 1}")))
        text_content = html.escape(str(sec.get("text", "")))

        bullets_html = ""
        bullets = sec.get("bullets", [])
        if bullets and isinstance(bullets, list):
            items = []
            for b in bullets:
                b_str = html.escape(str(b))
                items.append(f"""
                <li class="bullet-item">
                    <span class="bullet-bullet">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                            <polyline points="20 6 9 17 4 12"></polyline>
                        </svg>
                    </span>
                    <span class="bullet-text">{b_str}</span>
                </li>
                """)
            bullets_html = f'<ul class="bullet-list">{"".join(items)}</ul>'

        table_html = ""
        table_data = sec.get("table", [])
        if table_data and isinstance(table_data, list) and len(table_data) > 0:
            header_row = table_data[0]
            body_rows = table_data[1:] if len(table_data) > 1 else []

            th_cells = "".join(f"<th>{html.escape(str(c))}</th>" for c in header_row)
            tr_rows = []
            for r in body_rows:
                tds = "".join(f"<td>{html.escape(str(c))}</td>" for c in r)
                tr_rows.append(f"<tr>{tds}</tr>")

            table_id = f"tbl-{idx + 1}"
            table_html = f"""
            <div class="table-container">
                <div class="table-toolbar">
                    <span class="table-badge">Data Table</span>
                    <input type="text" class="table-search" placeholder="Filter rows..." onkeyup="filterTable('{table_id}', this.value)" />
                </div>
                <div class="table-scroll">
                    <table id="{table_id}" class="data-table">
                        <thead><tr>{th_cells}</tr></thead>
                        <tbody>{''.join(tr_rows)}</tbody>
                    </table>
                </div>
            </div>
            """

        sections_markup_list.append(f"""
        <section id="{sec_id}" class="content-section">
            <div class="section-header">
                <span class="section-number">0{idx + 1}</span>
                <h2 class="section-title">{heading}</h2>
            </div>
            {f'<p class="section-body">{text_content}</p>' if text_content else ''}
            {bullets_html}
            {table_html}
        </section>
        """)

    body_sections_markup = "\n".join(sections_markup_list)

    # Complete HTML Document
    html_content = f"""<!DOCTYPE html>
<html lang="{html.escape(language)}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(clean_title)} — J.A.R.V.I.S. Artifact</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="{web_font_import}" rel="stylesheet">
    <style>
        :root {{
            --bg: {bg_hex};
            --text: {text_hex};
            --primary: {primary_hex};
            --secondary: {secondary_hex};
            --accent: {accent_hex};
            --card-bg: {card_bg_hex};
            --border: {border_hex};
            --subtitle: {subtitle_hex};
            --primary-rgb: {r_p}, {g_p}, {b_p};
            --accent-rgb: {r_a}, {g_a}, {b_a};
            --font-main: {web_font_family};
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            background-color: var(--bg);
            color: var(--text);
            font-family: var(--font-main);
            line-height: 1.65;
            -webkit-font-smoothing: antialiased;
            overflow-x: hidden;
            scroll-behavior: smooth;
        }}

        /* Subtle radial ambient glow */
        .ambient-glow {{
            position: fixed;
            top: -200px;
            right: -200px;
            width: 600px;
            height: 600px;
            background: radial-gradient(circle, rgba(var(--primary-rgb), 0.12) 0%, rgba(var(--primary-rgb), 0) 70%);
            pointer-events: none;
            z-index: 0;
        }}

        /* Navigation */
        .navbar {{
            position: sticky;
            top: 0;
            z-index: 100;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 1rem 2rem;
            background: rgba({r_bg}, {g_bg}, {b_bg}, 0.85);
            backdrop-filter: blur(16px);
            border-bottom: 1px solid var(--border);
        }}

        .brand {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
            font-weight: 700;
            font-size: 1.1rem;
            letter-spacing: -0.02em;
            color: var(--primary);
            text-decoration: none;
        }}

        .brand-icon {{
            width: 28px;
            height: 28px;
            border-radius: 8px;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            display: flex;
            align-items: center;
            justify-content: center;
            color: #fff;
            box-shadow: 0 4px 12px rgba(var(--primary-rgb), 0.3);
        }}

        .nav-links {{
            display: flex;
            gap: 1.5rem;
            align-items: center;
        }}

        .nav-link {{
            color: var(--subtitle);
            text-decoration: none;
            font-size: 0.9rem;
            font-weight: 500;
            transition: color 0.2s ease;
        }}

        .nav-link:hover {{
            color: var(--primary);
        }}

        .cta-btn {{
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem 1.25rem;
            background: var(--primary);
            color: #ffffff !important;
            border-radius: 9999px;
            font-size: 0.875rem;
            font-weight: 600;
            text-decoration: none;
            box-shadow: 0 4px 14px rgba(var(--primary-rgb), 0.35);
            transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.2s ease;
        }}

        .cta-btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(var(--primary-rgb), 0.45);
        }}

        /* Container */
        .container {{
            max-width: 1080px;
            margin: 0 auto;
            padding: 3rem 1.5rem 6rem;
            position: relative;
            z-index: 1;
        }}

        /* Hero */
        .hero {{
            padding: 4rem 0 3rem;
            text-align: left;
            position: relative;
        }}

        .hero-pill {{
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.35rem 0.85rem;
            background: rgba(var(--primary-rgb), 0.08);
            border: 1px solid rgba(var(--primary-rgb), 0.2);
            color: var(--primary);
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 1.5rem;
        }}

        .live-dot {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--accent);
            box-shadow: 0 0 10px var(--accent);
            animation: pulse 2s infinite;
        }}

        @keyframes pulse {{
            0%, 100% {{ transform: scale(1); opacity: 1; }}
            50% {{ transform: scale(1.4); opacity: 0.6; }}
        }}

        .hero-title {{
            font-size: clamp(2.25rem, 5vw, 3.75rem);
            font-weight: 800;
            letter-spacing: -0.035em;
            line-height: 1.15;
            color: var(--text);
            margin-bottom: 1.25rem;
        }}

        .hero-tagline {{
            font-size: clamp(1.1rem, 2vw, 1.35rem);
            color: var(--subtitle);
            max-width: 720px;
            line-height: 1.6;
            margin-bottom: 2rem;
        }}

        /* Bento Metrics Grid */
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 1.25rem;
            margin: 2.5rem 0 4rem;
        }}

        .metric-card {{
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 1.5rem;
            position: relative;
            overflow: hidden;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.03);
            transition: transform 0.25s ease, border-color 0.25s ease;
        }}

        .metric-card:hover {{
            transform: translateY(-3px);
            border-color: var(--primary);
        }}

        .metric-badge {{
            font-size: 0.75rem;
            font-weight: 700;
            color: var(--subtitle);
            letter-spacing: 0.05em;
            margin-bottom: 0.75rem;
        }}

        .metric-value {{
            font-size: 2.25rem;
            font-weight: 800;
            color: var(--primary);
            letter-spacing: -0.03em;
            line-height: 1.1;
            margin-bottom: 0.35rem;
        }}

        .metric-label {{
            font-size: 0.85rem;
            color: var(--subtitle);
            font-weight: 500;
        }}

        /* Content Sections */
        .content-section {{
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 2.5rem;
            margin-bottom: 2rem;
            box-shadow: 0 8px 30px rgba(0, 0, 0, 0.02);
            position: relative;
        }}

        .section-header {{
            display: flex;
            align-items: baseline;
            gap: 0.75rem;
            margin-bottom: 1.25rem;
            border-bottom: 1px solid var(--border);
            padding-bottom: 1rem;
        }}

        .section-number {{
            font-size: 1rem;
            font-weight: 800;
            color: var(--accent);
            font-family: monospace;
        }}

        .section-title {{
            font-size: 1.6rem;
            font-weight: 700;
            color: var(--text);
            letter-spacing: -0.02em;
        }}

        .section-body {{
            font-size: 1.05rem;
            color: var(--text);
            line-height: 1.75;
            margin-bottom: 1.5rem;
        }}

        /* Bullet Points */
        .bullet-list {{
            list-style: none;
            display: flex;
            flex-direction: column;
            gap: 0.85rem;
            margin-top: 1rem;
        }}

        .bullet-item {{
            display: flex;
            align-items: flex-start;
            gap: 0.75rem;
        }}

        .bullet-bullet {{
            display: flex;
            align-items: center;
            justify-content: center;
            width: 22px;
            height: 22px;
            border-radius: 6px;
            background: rgba(var(--primary-rgb), 0.1);
            color: var(--primary);
            flex-shrink: 0;
            margin-top: 3px;
        }}

        .bullet-text {{
            font-size: 1rem;
            color: var(--text);
        }}

        /* Data Tables */
        .table-container {{
            margin-top: 1.5rem;
            border: 1px solid var(--border);
            border-radius: 12px;
            overflow: hidden;
            background: var(--bg);
        }}

        .table-toolbar {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0.75rem 1rem;
            background: var(--card-bg);
            border-bottom: 1px solid var(--border);
        }}

        .table-badge {{
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--primary);
        }}

        .table-search {{
            padding: 0.35rem 0.75rem;
            font-size: 0.85rem;
            border: 1px solid var(--border);
            border-radius: 6px;
            background: var(--bg);
            color: var(--text);
            outline: none;
            font-family: inherit;
        }}

        .table-search:focus {{
            border-color: var(--primary);
        }}

        .table-scroll {{
            overflow-x: auto;
        }}

        .data-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.925rem;
            text-align: left;
        }}

        .data-table th {{
            background: var(--primary);
            color: #ffffff;
            font-weight: 600;
            padding: 0.75rem 1rem;
            letter-spacing: 0.02em;
        }}

        .data-table td {{
            padding: 0.75rem 1rem;
            border-bottom: 1px solid var(--border);
            color: var(--text);
        }}

        .data-table tbody tr:nth-child(even) {{
            background: rgba(var(--primary-rgb), 0.03);
        }}

        .data-table tbody tr:hover {{
            background: rgba(var(--primary-rgb), 0.07);
        }}

        /* Footer */
        .footer {{
            margin-top: 5rem;
            border-top: 1px solid var(--border);
            padding: 2rem 0;
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            justify-content: space-between;
            color: var(--subtitle);
            font-size: 0.875rem;
        }}

        .footer-brand {{
            font-weight: 600;
            color: var(--text);
        }}

        .footer-tag {{
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            padding: 0.25rem 0.65rem;
            background: rgba(var(--primary-rgb), 0.08);
            border-radius: 6px;
            color: var(--primary);
            font-size: 0.75rem;
            font-weight: 600;
        }}

        /* Responsive */
        @media (max-width: 768px) {{
            .navbar {{
                padding: 1rem;
            }}
            .nav-links {{
                display: none;
            }}
            .content-section {{
                padding: 1.5rem;
            }}
            .hero-title {{
                font-size: 2.25rem;
            }}
        }}
    </style>
</head>
<body>
    <div class="ambient-glow"></div>

    <nav class="navbar">
        <a href="#" class="brand">
            <span class="brand-icon">⚡</span>
            <span>{html.escape(clean_title)}</span>
        </a>
        <div class="nav-links">
            {nav_links_markup}
            <a href="#sec-1" class="cta-btn">Explore Artifact</a>
        </div>
    </nav>

    <div class="container">
        <header class="hero">
            <div class="hero-pill">
                <span class="live-dot"></span>
                <span>Project J.A.R.V.I.S. • {html.escape(theme_cfg.get("name", "Artifact").upper())}</span>
            </div>
            <h1 class="hero-title">{html.escape(clean_title)}</h1>
            <p class="hero-tagline">{html.escape(tagline)}</p>
        </header>

        {metrics_markup}

        <main class="sections-wrapper">
            {body_sections_markup}
        </main>

        <footer class="footer">
            <div class="footer-brand">
                Generated with Claude Quality &amp; J.A.R.V.I.S. Core
            </div>
            <div class="footer-tag">
                <span>Theme: {html.escape(theme_cfg.get("name", "clean_light"))}</span>
            </div>
        </footer>
    </div>

    <script>
        // Interactive table search filtering
        function filterTable(tableId, query) {{
            const table = document.getElementById(tableId);
            if (!table) return;
            const rows = table.getElementsByTagName('tbody')[0].getElementsByTagName('tr');
            const cleanQuery = query.toLowerCase().trim();

            for (let i = 0; i < rows.length; i++) {{
                const text = rows[i].textContent.toLowerCase();
                rows[i].style.display = text.includes(cleanQuery) ? '' : 'none';
            }}
        }}
    </script>
</body>
</html>
"""

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    logger.info("Successfully generated Claude-quality website artifact at: %s", out_path)

    if auto_open:
        try:
            if os.name == "nt":
                os.startfile(str(out_path))
            else:
                webbrowser.open(f"file://{out_path}")
        except Exception as open_exc:
            logger.debug("Auto-open browser skipped: %s", open_exc)

    return str(out_path)
