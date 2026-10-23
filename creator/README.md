# JARVIS Document Creator Engine

**Engineer:** Vidhita (Document Engineer)  
**Pair:** Pair D (Documents + Messaging)  
**Branch:** `feature/vidhita-creator`  
**Milestone:** Days 1 through 6 Completed (Production Multi-Format Executive Engine & Templates)

---

## 1. Overview

The `creator` package is Project JARVIS's autonomous document and visual intelligence engine. It provides high-fidelity, programmatic document rendering across three standard productivity formats plus rich visual analytics:
- **PDF Documents** (`.pdf`) via ReportLab Platypus
- **Word Documents** (`.docx`) via python-docx
- **PowerPoint Decks** (`.pptx`) in 16:9 widescreen format via python-pptx
- **Themed Visual Charts** (`.png`) via headless Matplotlib (Agg backend)
- **Autonomous Multi-Format Executive Reports** coordinated across PDF, DOCX, and PPTX
- **Professional Ready-to-Use Document Templates** (Project Reports, Assignment Covers, Resumes, Application Letters)

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

### Day 4: High-Fidelity Themed Charts & Document Tools for Brain (`creator/chart_maker.py`)
- **`creator/chart_maker.py`**:
  - `generate_chart(chart_type, data, title, theme, out_dir, ...)`:
  - 5 core chart types: `bar`, `line`, `pie`, `donut`, `horizontal_bar`.
  - Themed palette rotation matching `clean_light`, `dark_pro`, `colourful`.
  - High-resolution 200 DPI PNG, headless Agg backend (zero GUI popups).
  - TrueType Noto Sans Devanagari font rendering for Marathi and Hindi labels.
- **`CreateChartTool` in `creator/tools.py`**:
  - Exposes `create_chart` tool to `JarvisBrain` and `TOOL_REGISTRY`.

### Day 5: AI Outline to Document & Multiformat Executive Report Generator
- **`creator/outline.py` (`create_document`)**:
  - `create_document(topic, kind='pdf', theme='clean_light', language='en', out_dir='workspace', auto_open=True) -> str`:
  - Requests 4-6 section structured JSON outline via Google Gemini (`google-genai` using `GEMINI_API_KEY` and `GEMINI_MODEL`) with automatic retry and Groq LPU / offline fallback.
  - Seamless support for English (`en`), Hindi (`hi`), and Marathi (`mr`).
  - Native Devanagari TrueType font embedding (`NotoSansDevanagari-Regular.ttf` and `Bold.ttf`) in ReportLab, python-docx, and python-pptx preventing square-box font corruption.
- **`CreateDocumentTool` in `creator/tools.py`**:
  - Exposed in `creator/tools.py` and exported in `TOOLS` for central tool discovery.
- **`creator/report_maker.py` (`generate_executive_report`)**:
  - Produces a synchronized executive report package across **PDF**, **Word (DOCX)**, and **PowerPoint (PPTX)** simultaneously.
  - Automatically synthesizes Bento KPI metrics cards, executes themed chart generation from configs, and structures executive summary and analytical tables.
- **`GenerateReportTool` in `creator/tools.py`**:
  - Exposes `generate_report` tool to `JarvisBrain` and `TOOL_REGISTRY`.

### Day 6: Charts, Cover Pages, and Document Templates (`creator/charts.py`, `creator/templates.py`)
- **`creator/charts.py` (`make_chart`)**:
  - `make_chart(kind, labels, values, title, theme, out_dir='temp_creator') -> str`:
  - Visual analytics generator saving crisp PNGs into `temp_creator/`.
  - Supports `bar`, `line`, `pie`, `donut`, and `horizontal_bar`.
  - Applies active theme colors (`clean_light`, `dark_pro`, `colourful`) and Devanagari TrueType font rendering.
- **Section Chart Integration**:
  - Allows section dictionaries across `make_pdf`, `make_docx`, and `make_pptx` to include `'chart': {'kind': ..., 'labels': [...], 'values': [...], 'title': ...}`.
  - Automatically renders and embeds high-DPI chart images centered into documents.
- **Cover Page & Header/Footer Customization**:
  - `cover_page: bool = True` toggle allows suppressing cover page for single-page letters and compact resumes.
  - `header_text: str` and `footer_text: str` support custom running headers and footers.
- **`creator/templates.py` (Ready-to-Use Professional Templates)**:
  - `project_report(title, author, chapters, theme, out_dir, kind)`: Full academic and technical project reports.
  - `assignment_cover(subject, name, roll_no, title, theme, out_dir, kind)`: Academic assignment cover sheet with declaration and evaluation rubrics.
  - `resume(data, theme, out_dir, kind)`: Modern curriculum vitae with profile, skills, experience, and education.
  - `application_letter(data, theme, out_dir, kind)`: Formal business and job application letters.
- **`CreateTemplateTool` in `creator/tools.py`**:
  - Exposes `create_template_document` tool to `JarvisBrain` and `TOOL_REGISTRY`.

---

## 3. Themes Reference

| Theme | Background | Text | Primary Accent | Vibe |
|---|---|---|---|---|
| `clean_light` | `#FFFFFF` | `#1E293B` | `#1E40AF` (Royal Blue) | Crisp, corporate, clean |
| `dark_pro` | `#0F172A` | `#F8FAFC` | `#38BDF8` (Cyan / Sky) | Modern dark mode, tech brief |
| `colourful` | `#FFFDF7` | `#1E1B4B` | `#7C3AED` (Violet / Coral) | Expressive, vibrant, creative |

---

## 4. How to Run & Verify

### Run Automated Acceptance Tests (Days 1–6)
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

#### 3. Day 6: Statistical Chart & Section Embedding
```python
from creator.charts import make_chart
from creator.pdf_maker import make_pdf

# 1. Standalone chart PNG in temp_creator/
chart_file = make_chart(
    kind="bar",
    labels=["Q1", "Q2", "Q3", "Q4"],
    values=[120.0, 240.0, 360.0, 480.0],
    title="Quarterly Growth",
    theme="clean_light",
    out_dir="temp_creator"
)

# 2. Section chart embedded directly inside PDF
doc_file = make_pdf(
    title="Quarterly Analytics",
    sections=[{
        "heading": "Performance Trajectory",
        "text": "Detailed telemetry distribution.",
        "chart": {
            "kind": "bar",
            "labels": ["Core", "Voice", "Vision", "Creator"],
            "values": [35, 25, 20, 20],
            "title": "Subsystem Allocations"
        }
    }],
    theme="clean_light"
)
print("PDF with Embedded Chart:", doc_file)
```

#### 4. Day 6: Document Templates & Tool Execution
```python
from creator.templates import project_report, assignment_cover, resume, application_letter
from tools.registry import execute_tool

# Project Report
report_path = project_report(
    title="Project JARVIS Architecture",
    author="Vidhita (Document Engineer)",
    chapters=[{"heading": "Design Patterns", "text": "Modular isolation and ReAct tool calling."}],
    theme="clean_light",
    kind="pdf"
)

# Autonomous tool execution via brain
res = execute_tool("create_template_document", {
    "template_type": "assignment_cover",
    "data": {
        "subject": "Distributed Systems",
        "name": "Vidhita Shitole",
        "roll_no": "AI-524",
        "title": "Consensus Protocols"
    },
    "kind": "pdf"
})
print("Template Document:", res.data["file_path"])
```
