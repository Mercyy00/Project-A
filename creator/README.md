# JARVIS Document Creator Engine

**Engineer:** Vidhita (Document Engineer)  
**Pair:** Pair D (Documents + Messaging)  
**Branch:** `feature/vidhita-creator`  
**Milestone:** Days 1 through 5 Completed (Production Multi-Format Executive Engine)

---

## 1. Overview

The `creator` package is Project JARVIS's autonomous document and visual intelligence engine. It provides high-fidelity, programmatic document rendering across three standard productivity formats plus rich visual analytics:
- **PDF Documents** (`.pdf`) via ReportLab Platypus
- **Word Documents** (`.docx`) via python-docx
- **PowerPoint Decks** (`.pptx`) in 16:9 widescreen format via python-pptx
- **Themed Visual Charts** (`.png`) via headless Matplotlib (Agg backend)
- **Autonomous Multi-Format Executive Reports** coordinated across PDF, DOCX, and PPTX

All tools adhere strictly to `BaseTool` contracts, automatically register into `TOOL_REGISTRY`, and prevent raw markdown corruption fallback.

---

## 2. Daily Implementations & Enhancements

### Day 1: Setup + Hello Documents (`creator/hello_docs.py`)
- Creates `workspace/hello.pdf` (ReportLab), `workspace/hello.docx` (python-docx), and `workspace/hello.pptx` (python-pptx).
- Each document has the title `'Hello from JARVIS'` and one line of text.
- Automatically creates the `workspace/` output directory if missing and prints full resolved paths.
- Wrapped in try/except with strict Python 3.11+ type hints and docstrings.

### Day 2: Theming Engine & Themed PDF Maker (`creator/themes.py`, `creator/pdf_maker.py`)
- **`creator/themes.py`**:
  - `THEMES` dictionary defining `'clean_light'`, `'dark_pro'`, and `'colourful'`.
  - Defines background colors, text colors, primary/secondary/accent tones, card and table styling, typography, and spacing metrics.
  - `get_theme(theme_name)` safely falls back to `'clean_light'` for unknown themes.
- **`creator/pdf_maker.py`**:
  - `make_pdf(title, sections, theme='clean_light', out_dir='workspace', auto_open=True) -> str`
  - ReportLab Platypus architecture with cover title, headings, paragraphs, bullet lists, and styled data tables.
  - Custom `NumberedCanvas` two-pass rendering for dynamic page footers (`"Page X of Y"`) and document title tracking.
  - Page-level background painting matching the selected theme.

### Day 3: Word, PowerPoint Makers & Day 3 Elevation (D1.1, D1.2, D1.3)
- **`creator/tools.py` (Task D1.1 - Brain Integration & Tool Registry)**:
  - `CreatePdfTool`: Generates publication-ready binary PDFs.
  - `CreateDocxTool`: Generates styled Word documents.
  - `CreatePptxTool`: Generates 16:9 widescreen PowerPoint presentation decks.
  - Full OpenAPI / Gemini JSON schemas via `get_schema()` enabling autonomous ReAct brain function calling.
  - Automatic registration into `TOOL_REGISTRY`.
- **Claude-Quality Document Themes & Styling (Task D1.2)**:
  - **Executive Cover Page**: Full-bleed accent stripe, document title, subtitle, and structured metadata card (Author: Vidhita • Pair D, Theme, Engine, Status).
  - **Bento Grid Cards**: 2-column key metric callout cards with colored borders, card background shading, bold numerals, and descriptive labels.
  - **Modern Tables**: Bold header row with theme fill, alternating row fills (`card_bg` and `table_row_alt`), and clean light borders.
  - **Devanagari Font Embedding**: TrueType Noto Sans Devanagari (`creator/fonts/NotoSansDevanagari-Regular.ttf` & `Bold`) registered in ReportLab and embedded in Word/PPTX, ensuring flawless Marathi and Hindi rendering without square-box corruption.
- **Auto-Open Document Feature (Task D1.3)**:
  - Optional `auto_open: bool = True` argument on all makers and tools.
  - Calls `os.startfile(output_path)` immediately after creation on Windows, opening the document in Adobe Acrobat, Microsoft Word, or PowerPoint.

### Day 4: High-Fidelity Themed Charts & Document Embedding (`creator/chart_maker.py`)
- **`creator/chart_maker.py`**:
  - `generate_chart(chart_type, data, title, theme, out_dir, ...) -> str`:
  - Supports 5 core chart types: `bar`, `line`, `pie`, `donut`, and `horizontal_bar`.
  - Themed palette rotation matching `clean_light`, `dark_pro`, and `colourful`.
  - High-resolution 200 DPI PNG output, headless Agg backend (zero GUI popups).
  - TrueType Noto Sans Devanagari font rendering for Marathi and Hindi chart titles and category labels.
- **Document Chart Embedding**:
  - `pdf_maker.py`: Automatically embeds generated charts or images centered within sections using ReportLab `Image`.
  - `docx_maker.py`: Embeds high-res chart images centered with custom margins.
  - `pptx_maker.py`: Automatically inserts dedicated 16:9 widescreen slides for data visualizations with custom header lines.
- **`CreateChartTool` in `creator/tools.py`**:
  - Exposes `create_chart` tool to `JarvisBrain` and `TOOL_REGISTRY`.

### Day 5: Autonomous Multi-Format Executive Report Generator (`creator/report_maker.py`)
- **`creator/report_maker.py`**:
  - `generate_executive_report(title, summary, sections, key_metrics, chart_configs, theme, formats, ...) -> Dict[str, str]`:
  - End-to-end autonomous executive intelligence generator.
  - Produces a synchronized executive report package across **PDF**, **Word (DOCX)**, and **PowerPoint (PPTX)** simultaneously.
  - Automatically synthesizes Bento KPI metrics cards, executes themed chart generation from configs, and structures executive summary and analytical tables.
  - Selective format generation (e.g. `formats=["pdf"]` or `formats=["pdf", "docx", "pptx"]`).
- **`GenerateReportTool` in `creator/tools.py`**:
  - Exposes `generate_report` tool to `JarvisBrain` and `TOOL_REGISTRY`.
  - Enables single-prompt autonomous executive report compilation.

---

## 3. Themes Reference

| Theme | Background | Text | Primary Accent | Vibe |
|---|---|---|---|---|
| `clean_light` | `#FFFFFF` | `#1E293B` | `#1E40AF` (Royal Blue) | Crisp, corporate, clean |
| `dark_pro` | `#0F172A` | `#F8FAFC` | `#38BDF8` (Cyan / Sky) | Modern dark mode, tech brief |
| `colourful` | `#FFFDF7` | `#1E1B4B` | `#7C3AED` (Violet / Coral) | Expressive, vibrant, creative |

---

## 4. How to Run & Verify

### Run Automated Acceptance Tests (Days 1–5)
```powershell
python tests/test_creator.py
```

### Run with Pytest
```powershell
pytest tests/test_creator.py -v
```

### Direct Tool Execution Examples

#### 1. Generate Themed Chart
```python
from tools.registry import execute_tool

result = execute_tool("create_chart", {
    "chart_type": "bar",
    "data": {"Q1": 120, "Q2": 260, "Q3": 390, "Q4": 520},
    "title": "Quarterly Revenue Growth",
    "theme": "clean_light"
})
print("Chart PNG:", result.data["file_path"])
```

#### 2. Generate Coordinated Multi-Format Executive Report
```python
from tools.registry import execute_tool

result = execute_tool("generate_report", {
    "title": "JARVIS Executive Intelligence Review",
    "summary": "Autonomous desktop assistant production metrics.",
    "key_metrics": [
        {"label": "Engine Latency", "value": "< 200ms"},
        {"label": "Document Accuracy", "value": "100%"},
    ],
    "chart_configs": [
        {"type": "donut", "data": {"PDF": 35, "DOCX": 35, "PPTX": 30}, "title": "Format Usage"}
    ],
    "theme": "clean_light",
    "formats": ["pdf", "docx", "pptx"],
    "auto_open": False
})
print("Report Files:", result.data["files"])
```
