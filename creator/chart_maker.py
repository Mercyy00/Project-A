"""Themed chart generation module for JARVIS Document Creator (Day 4 Deliverable).

Author: Vidhita (Document Engineer)
Pair: Pair D (Documents + Messaging)
Module: creator.chart_maker

Generates high-resolution, professionally styled charts (bar, line, pie/donut, horizontal_bar)
matching JARVIS document themes ('clean_light', 'dark_pro', 'colourful').
Outputs PNG images ready for embedding into PDF, DOCX, and PPTX documents.
Includes first-class Devanagari (Marathi & Hindi) typography support via Noto Sans Devanagari.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Sequence, Union

from creator.themes import THEMES, contains_devanagari, get_theme

logger = logging.getLogger(__name__)

# Fonts directory
FONTS_DIR = Path(__file__).resolve().parent / "fonts"
DEVANAGARI_REGULAR = FONTS_DIR / "NotoSansDevanagari-Regular.ttf"
DEVANAGARI_BOLD = FONTS_DIR / "NotoSansDevanagari-Bold.ttf"


def _sanitize_filename(name: str) -> str:
    """Sanitize title into a safe filesystem filename."""
    # Convert non-ascii or special chars
    clean = re.sub(r"[^\w\s-]", "", name, flags=re.UNICODE).strip().lower()
    clean = re.sub(r"[-\s]+", "_", clean)
    # If all characters were non-ASCII or stripped, generate safe fallback
    ascii_clean = clean.encode("ascii", "ignore").decode("ascii").strip("_")
    return ascii_clean or "chart"


def _get_font_prop(text: str, bold: bool = False) -> Any:
    """Return matplotlib FontProperties if text contains Devanagari."""
    if contains_devanagari(text):
        try:
            from matplotlib import font_manager
            f_path = DEVANAGARI_BOLD if bold else DEVANAGARI_REGULAR
            if f_path.exists():
                return font_manager.FontProperties(fname=str(f_path))
        except Exception as exc:
            logger.debug("Failed to load Devanagari font in matplotlib: %s", exc)
    return None


def generate_chart(
    chart_type: str,
    data: Dict[str, Any],
    title: str = "Analytics Chart",
    theme: str = "clean_light",
    out_dir: str = "workspace",
    filename: Optional[str] = None,
    width: float = 7.0,
    height: float = 4.2,
    dpi: int = 200,
) -> str:
    """Generate a themed chart image (PNG) and save to disk.

    Args:
        chart_type: Type of chart: 'bar', 'line', 'pie', 'donut', or 'horizontal_bar'.
        data: Chart data dictionary. Formats supported:
            - {'labels': ['Q1', 'Q2', 'Q3', 'Q4'], 'values': [120, 240, 310, 450]}
            - or mapping: {'Q1': 120, 'Q2': 240, 'Q3': 310, 'Q4': 450}
            - or list of dicts: [{'label': 'A', 'value': 10}, {'label': 'B', 'value': 20}]
        title: Title of the chart.
        theme: Theme name ('clean_light', 'dark_pro', 'colourful').
        out_dir: Output directory (defaults to 'workspace').
        filename: Optional output filename (auto-generated if omitted).
        width: Figure width in inches.
        height: Figure height in inches.
        dpi: Image resolution DPI (defaults to 200 for crisp publication).

    Returns:
        str: Absolute path to the generated PNG image.

    Raises:
        ValueError: If data is empty or invalid.
        RuntimeError: If chart generation fails.
    """
    try:
        import matplotlib
        # Enforce headless Agg backend to prevent GUI popups
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as err:
        raise RuntimeError(f"matplotlib is required for chart generation: {err}") from err

    theme_cfg = get_theme(theme)
    bg_color = theme_cfg.get("card_bg") or theme_cfg.get("bg_color", "#FFFFFF")
    text_color = theme_cfg.get("text_color", "#1E293B")
    primary_color = theme_cfg.get("primary_color", "#1E40AF")
    secondary_color = theme_cfg.get("secondary_color", "#3B82F6")
    accent_color = theme_cfg.get("accent_color", "#0D9488")
    border_color = theme_cfg.get("border_color", "#CBD5E1")

    # Extract labels and values safely
    labels: List[str] = []
    values: List[float] = []

    if isinstance(data, dict):
        if "labels" in data and "values" in data:
            labels = [str(lbl) for lbl in data["labels"]]
            values = [float(v) for v in data["values"]]
        else:
            for k, v in data.items():
                labels.append(str(k))
                try:
                    values.append(float(v))
                except (ValueError, TypeError):
                    values.append(0.0)
    elif isinstance(data, (list, tuple)):
        for idx, item in enumerate(data):
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                labels.append(str(item[0]))
                values.append(float(item[1]))
            elif isinstance(item, dict) and "label" in item and "value" in item:
                labels.append(str(item["label"]))
                values.append(float(item["value"]))
            else:
                labels.append(f"Item {idx + 1}")
                values.append(float(item) if isinstance(item, (int, float)) else 0.0)

    if not labels or not values:
        labels = ["Metric A", "Metric B", "Metric C"]
        values = [10.0, 25.0, 15.0]

    # Palette rotation
    palette = [
        primary_color,
        secondary_color,
        accent_color,
        theme_cfg.get("cover_stripe_color", primary_color),
        "#10B981",  # Emerald
        "#F59E0B",  # Amber
        "#8B5CF6",  # Violet
        "#EC4899",  # Pink
    ]

    out_folder = Path(out_dir).resolve()
    out_folder.mkdir(parents=True, exist_ok=True)

    if not filename:
        clean_title = _sanitize_filename(title)
        filename = f"{clean_title}_{theme_cfg['name']}.png"
    if not filename.endswith(".png"):
        filename = f"{filename}.png"

    out_file = out_folder / filename

    fig, ax = plt.subplots(figsize=(width, height), dpi=dpi)
    fig.patch.set_facecolor(bg_color)
    ax.set_facecolor(bg_color)

    norm_type = (chart_type or "bar").lower().strip()

    title_font_prop = _get_font_prop(title, bold=True)

    if norm_type in ("bar", "column"):
        bar_colors = [palette[i % len(palette)] for i in range(len(labels))]
        bars = ax.bar(labels, values, color=bar_colors, edgecolor=border_color, width=0.55, zorder=3)
        # Value callout labels on top of bars
        for bar in bars:
            h = bar.get_height()
            ax.annotate(
                f"{h:g}",
                xy=(bar.get_x() + bar.get_width() / 2, h),
                xytext=(0, 4),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=9,
                fontweight="bold",
                color=text_color,
            )
        ax.set_ylabel("Value", fontsize=10, fontweight="bold", color=text_color)

    elif norm_type in ("horizontal_bar", "barh"):
        bar_colors = [palette[i % len(palette)] for i in range(len(labels))]
        bars = ax.barh(labels, values, color=bar_colors, edgecolor=border_color, height=0.55, zorder=3)
        for bar in bars:
            w = bar.get_width()
            ax.annotate(
                f"{w:g}",
                xy=(w, bar.get_y() + bar.get_height() / 2),
                xytext=(5, 0),
                textcoords="offset points",
                ha="left",
                va="center",
                fontsize=9,
                fontweight="bold",
                color=text_color,
            )
        ax.set_xlabel("Value", fontsize=10, fontweight="bold", color=text_color)

    elif norm_type in ("line", "trend"):
        ax.plot(
            labels,
            values,
            color=primary_color,
            marker="o",
            markersize=6,
            linewidth=2.5,
            label="Metric Trend",
            zorder=4,
        )
        ax.fill_between(range(len(values)), values, color=primary_color, alpha=0.15, zorder=2)
        for i, val in enumerate(values):
            ax.annotate(
                f"{val:g}",
                xy=(i, val),
                xytext=(0, 6),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=9,
                fontweight="bold",
                color=text_color,
            )
        ax.set_ylabel("Value", fontsize=10, fontweight="bold", color=text_color)

    elif norm_type in ("pie", "donut"):
        pie_colors = [palette[i % len(palette)] for i in range(len(labels))]
        wedges, texts, autotexts = ax.pie(
            values,
            labels=labels,
            autopct="%1.1f%%",
            startangle=140,
            colors=pie_colors,
            wedgeprops={"edgecolor": bg_color, "linewidth": 2, "antialiased": True},
            pctdistance=0.75 if norm_type == "donut" else 0.6,
        )
        for t in texts:
            t.set_color(text_color)
            t.set_fontsize(10)
            t.set_fontweight("bold")
            dev_prop = _get_font_prop(t.get_text())
            if dev_prop:
                t.set_fontproperties(dev_prop)
        for at in autotexts:
            at.set_color("#FFFFFF" if theme != "clean_light" else "#1E293B")
            at.set_fontsize(9)
            at.set_fontweight("bold")

        if norm_type == "donut":
            centre_circle = plt.Circle((0, 0), 0.55, fc=bg_color)
            fig.gca().add_artist(centre_circle)

    else:
        # Fallback to bar chart
        bars = ax.bar(labels, values, color=primary_color, width=0.55, zorder=3)
        ax.set_ylabel("Value", fontsize=10, color=text_color)

    # Clean layout styling
    if norm_type not in ("pie", "donut"):
        ax.grid(True, linestyle="--", alpha=0.3, color=border_color, zorder=1)
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)
        ax.spines["left"].set_color(border_color)
        ax.spines["bottom"].set_color(border_color)
        ax.tick_params(colors=text_color, labelsize=9)

        # Devanagari tick labels if needed
        for label_obj in ax.get_xticklabels() + ax.get_yticklabels():
            dev_prop = _get_font_prop(label_obj.get_text())
            if dev_prop:
                label_obj.set_fontproperties(dev_prop)

    title_kwargs: Dict[str, Any] = {
        "fontsize": 13,
        "fontweight": "bold",
        "color": primary_color,
        "pad": 14,
    }
    if title_font_prop:
        title_kwargs["fontproperties"] = title_font_prop
        title_kwargs["fontsize"] = 14

    ax.set_title(title, **title_kwargs)

    plt.tight_layout()
    plt.savefig(str(out_file), dpi=dpi, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)

    resolved_path = str(out_file.resolve())
    logger.info("Chart generated successfully at %s (%s)", resolved_path, norm_type)
    return resolved_path
