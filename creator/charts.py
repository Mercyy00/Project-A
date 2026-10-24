"""JARVIS Themed Chart Generator (Day 6 Deliverable).

Author: Document Engineer
Role: High-fidelity statistical visualisations with Matplotlib,
      theme palettes, and Devanagari typography.
"""

from datetime import datetime
import logging
import os
from pathlib import Path
import re
from typing import Any, List, Optional

import matplotlib

# Set non-interactive Agg backend before pyplot import to avoid GUI thread issues
matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt

from creator.themes import THEMES, contains_devanagari, get_theme

logger = logging.getLogger(__name__)

# Fonts directory configuration
FONTS_DIR = Path(__file__).parent / "fonts"
DEVANAGARI_FONT_REGULAR = FONTS_DIR / "NotoSansDevanagari-Regular.ttf"
DEVANAGARI_FONT_BOLD = FONTS_DIR / "NotoSansDevanagari-Bold.ttf"


def _get_font_prop(bold: bool = False) -> Optional[fm.FontProperties]:
    """Return FontProperties for Devanagari font if installed."""
    try:
        target = DEVANAGARI_FONT_BOLD if bold else DEVANAGARI_FONT_REGULAR
        if target.exists():
            return fm.FontProperties(fname=str(target))
    except Exception as exc:
        logger.debug("Failed to load Devanagari font property: %s", exc)
    return None


def _sanitize_title(title: str) -> str:
    """Sanitize chart title for a clean filesystem filename."""
    clean = re.sub(r'[\\/*?:"<>|]', "", title)
    clean = clean.strip().replace(" ", "_").lower()
    return clean[:40] or "chart"


def make_chart(
    kind: str,
    labels: List[str],
    values: List[float],
    title: str = "Chart",
    theme: str = "clean_light",
    out_dir: str = "temp_creator",
) -> str:
    """Generate a clean statistical chart PNG with matplotlib matching theme colours.

    Implements Day 6 specification:
    - Supports kind: 'bar', 'line', 'pie' (plus 'donut', 'horizontal_bar')
    - Applies active theme colors (background, text, grid, accent palette)
    - Supports Hindi and Marathi Devanagari typography
    - Saves clean high-DPI PNG into temp_creator/
    - Thread-safe headless rendering with zero GUI popups

    Args:
        kind: Chart type ('bar', 'line', 'pie', 'donut', 'horizontal_bar').
        labels: Category labels (list of strings).
        values: Numeric values corresponding to labels (list of floats or ints).
        title: Title of the chart.
        theme: Theme name ('clean_light', 'dark_pro', 'colourful').
        out_dir: Directory where the PNG file is written (defaults to 'temp_creator').

    Returns:
        str: Absolute filesystem path to the saved PNG chart.
    """
    try:
        # Validate inputs
        if not labels or not values:
            labels = ["Item A", "Item B", "Item C"]
            values = [10.0, 20.0, 30.0]

        # Convert values to float safely
        clean_values: List[float] = []
        for v in values:
            try:
                clean_values.append(float(v))
            except (ValueError, TypeError):
                clean_values.append(0.0)

        # Match label count with value count
        min_len = min(len(labels), len(clean_values))
        labels = [str(l) for l in labels[:min_len]]
        clean_values = clean_values[:min_len]

        # Resolve Theme Configuration
        theme_cfg = get_theme(theme)
        bg_color = theme_cfg.get("bg_color", "#FFFFFF")
        text_color = theme_cfg.get("text_color", "#1E293B")
        palette = theme_cfg.get("chart_palette", ["#1E40AF", "#3B82F6", "#60A5FA", "#93C5FD", "#BFDBFE"])
        border_col = theme_cfg.get("border_color", "#E2E8F0")

        # Check for Devanagari text in title or labels
        has_devanagari = contains_devanagari(title) or any(contains_devanagari(lbl) for lbl in labels)
        dev_font = _get_font_prop(bold=False) if has_devanagari else None
        dev_font_bold = _get_font_prop(bold=True) if has_devanagari else None

        # Ensure output directory exists
        target_dir = Path(out_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        # Create Matplotlib Figure
        fig, ax = plt.subplots(figsize=(7.5, 4.2), dpi=200)
        fig.patch.set_facecolor(bg_color)
        ax.set_facecolor(bg_color)

        chart_kind = (kind or "bar").strip().lower()

        # -------------------------------------------------------------
        # 1. Bar Chart
        # -------------------------------------------------------------
        if chart_kind == "bar":
            bar_colors = [palette[i % len(palette)] for i in range(len(labels))]
            bars = ax.bar(labels, clean_values, color=bar_colors, width=0.55, edgecolor=bg_color, linewidth=1.2)
            ax.set_axisbelow(True)
            ax.yaxis.grid(True, linestyle="--", alpha=0.35, color=border_col)
            ax.xaxis.grid(False)

            # Bar Value Annotations
            max_val = max(clean_values) if clean_values else 1.0
            offset = max_val * 0.02
            for bar, val in zip(bars, clean_values):
                h = bar.get_height()
                val_text = f"{val:g}"
                ax.annotate(
                    val_text,
                    xy=(bar.get_x() + bar.get_width() / 2, h + offset),
                    xytext=(0, 2),
                    textcoords="offset points",
                    ha="center",
                    va="bottom",
                    fontsize=8.5,
                    fontweight="semibold",
                    color=text_color,
                    fontproperties=dev_font,
                )

        # -------------------------------------------------------------
        # 2. Line Chart
        # -------------------------------------------------------------
        elif chart_kind == "line":
            line_color = palette[0]
            ax.plot(
                labels,
                clean_values,
                color=line_color,
                marker="o",
                markersize=6,
                linewidth=2.5,
                markeredgecolor=bg_color,
                markeredgewidth=1.5,
            )
            ax.fill_between(labels, clean_values, color=line_color, alpha=0.15)
            ax.set_axisbelow(True)
            ax.yaxis.grid(True, linestyle="--", alpha=0.35, color=border_col)
            ax.xaxis.grid(True, linestyle=":", alpha=0.2, color=border_col)

            for x_coord, val in zip(labels, clean_values):
                ax.annotate(
                    f"{val:g}",
                    xy=(x_coord, val),
                    xytext=(0, 6),
                    textcoords="offset points",
                    ha="center",
                    fontsize=8.5,
                    fontweight="semibold",
                    color=text_color,
                    fontproperties=dev_font,
                )

        # -------------------------------------------------------------
        # 3. Pie / Donut Chart
        # -------------------------------------------------------------
        elif chart_kind in ("pie", "donut"):
            pie_colors = [palette[i % len(palette)] for i in range(len(labels))]
            wedge_props = {"edgecolor": bg_color, "linewidth": 2}
            if chart_kind == "donut":
                wedge_props["width"] = 0.42

            wedges, texts, autotexts = ax.pie(
                clean_values,
                labels=labels,
                autopct="%1.1f%%",
                startangle=140,
                colors=pie_colors,
                wedgeprops=wedge_props,
                pctdistance=0.75 if chart_kind == "donut" else 0.6,
            )

            for t in texts:
                t.set_color(text_color)
                t.set_fontsize(9)
                if dev_font:
                    t.set_fontproperties(dev_font)

            for at in autotexts:
                at.set_color("#FFFFFF" if theme == "dark_pro" else text_color)
                at.set_fontsize(8.5)
                at.set_weight("bold")

        # -------------------------------------------------------------
        # 4. Horizontal Bar Chart
        # -------------------------------------------------------------
        elif chart_kind == "horizontal_bar":
            bar_colors = [palette[i % len(palette)] for i in range(len(labels))]
            y_pos = range(len(labels))
            bars = ax.barh(y_pos, clean_values, color=bar_colors, height=0.55, edgecolor=bg_color, linewidth=1.2)
            ax.set_yticks(y_pos)
            ax.set_yticklabels(labels)
            ax.set_axisbelow(True)
            ax.xaxis.grid(True, linestyle="--", alpha=0.35, color=border_col)
            ax.yaxis.grid(False)

            max_val = max(clean_values) if clean_values else 1.0
            offset = max_val * 0.02
            for bar, val in zip(bars, clean_values):
                w = bar.get_width()
                ax.annotate(
                    f"{val:g}",
                    xy=(w + offset, bar.get_y() + bar.get_height() / 2),
                    xytext=(3, 0),
                    textcoords="offset points",
                    ha="left",
                    va="center",
                    fontsize=8.5,
                    fontweight="semibold",
                    color=text_color,
                    fontproperties=dev_font,
                )

        else:
            # Fallback to standard vertical bar
            bar_colors = [palette[i % len(palette)] for i in range(len(labels))]
            ax.bar(labels, clean_values, color=bar_colors, width=0.55)
            ax.yaxis.grid(True, linestyle="--", alpha=0.35, color=border_col)

        # Style Spines, Ticks and Axes
        if chart_kind not in ("pie", "donut"):
            for spine in ax.spines.values():
                spine.set_color(border_col)
                spine.set_linewidth(0.8)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.tick_params(axis="both", colors=text_color, labelsize=9)

            if dev_font:
                for tick_label in ax.get_xticklabels() + ax.get_yticklabels():
                    tick_label.set_fontproperties(dev_font)

        # Title styling
        if title:
            if dev_font_bold:
                ax.set_title(title, fontproperties=dev_font_bold, fontsize=12, pad=14, color=text_color)
            else:
                ax.set_title(title, fontsize=12, fontweight="bold", pad=14, color=text_color)

        plt.tight_layout()

        # Build clean filename and save
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:19]
        safe_title = _sanitize_title(title)
        filename = f"{safe_title}_{chart_kind}_{timestamp}.png"
        output_path = target_dir / filename

        fig.savefig(str(output_path), facecolor=fig.get_facecolor(), edgecolor="none", dpi=200)
        plt.close(fig)

        logger.info("Successfully generated Day 6 chart at: %s", output_path)
        return str(output_path.resolve())

    except Exception as exc:
        logger.error("make_chart failed: %s", exc, exc_info=True)
        try:
            plt.close("all")
        except Exception:
            pass
        raise
