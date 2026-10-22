# JARVIS Document Creator Engine

**Engineer:** Vidhita (Document Engineer)  
**Pair:** Pair D (Documents + Messaging)  
**Branch:** `feature/vidhita-creator`  
**Milestone:** Day 1 to Day 3 Completed (Elevated Claude-Quality Engine)

---

## 1. Overview

The `creator` package is Project JARVIS's autonomous document generation engine. It provides high-fidelity, programmatic document rendering across three standard productivity formats:
- **PDF Documents** (`.pdf`) via ReportLab Platypus
- **Word Documents** (`.docx`) via python-docx
- **PowerPoint Decks** (`.pptx`) in 16:9 widescreen format via python-pptx

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
  - Automatic registration into `TOOL_REGISTRY` so Jarvis executes real binary generators instead of falling back to raw markdown `write_file`.
  - Canonical exports: `TOOLS = [CreatePdfTool(), CreateDocxTool(), CreatePptxTool()]`.
- **Claude-Quality Document Themes & Styling (Task D1.2)**:
  - **Executive Cover Page**: Full-bleed accent stripe, document title, subtitle, and structured metadata card (Author: Vidhita • Pair D, Theme, Engine, Status).
  - **Bento Grid Cards**: 2-column key metric callout cards with colored borders, card background shading, bold numerals, and descriptive labels.
  - **Modern Tables**: Bold header row with theme fill, alternating row fills (`card_bg` and `table_row_alt`), and clean light borders.
  - **Devanagari Font Embedding**: TrueType Noto Sans Devanagari (`creator/fonts/NotoSansDevanagari-Regular.ttf` & `Bold`) registered in ReportLab and embedded in Word/PPTX, ensuring flawless Marathi and Hindi rendering without square-box corruption.
- **Auto-Open Document Feature (Task D1.3)**:
  - Optional `auto_open: bool = True` argument on all makers and tools.
  - Calls `os.startfile(output_path)` immediately after creation on Windows, opening the document in Adobe Acrobat, Microsoft Word, or PowerPoint.

---

## 3. Themes Reference

| Theme | Background | Text | Primary Accent | Vibe |
|---|---|---|---|---|
| `clean_light` | `#FFFFFF` | `#1E293B` | `#1E40AF` (Royal Blue) | Crisp, corporate, clean |
| `dark_pro` | `#0F172A` | `#F8FAFC` | `#38BDF8` (Cyan / Sky) | Modern dark mode, tech brief |
| `colourful` | `#FFFDF7` | `#1E1B4B` | `#7C3AED` (Violet / Coral) | Expressive, vibrant, creative |

---

## 4. How to Run & Verify

### Run Automated Acceptance Tests
```powershell
python tests/test_creator.py
```

### Run with Pytest
```powershell
pytest tests/test_creator.py -v
```

### Direct Tool Execution Example
```python
from tools.registry import execute_tool

# Generate PDF with Bento Grid Metrics and Auto-Open
result = execute_tool("create_pdf", {
    "title": "Autonomous AI Engine Report",
    "sections": [
        {
            "heading": "1. Executive Summary",
            "text": "Autonomous document creator suite engineered for Project JARVIS.",
            "metrics": [
                {"label": "Engine Latency", "value": "< 250ms"},
                {"label": "Document Fidelity", "value": "100% Binary"},
                {"label": "Multilingual Font", "value": "Noto Sans Devanagari"},
                {"label": "Coverage", "value": "PDF, DOCX, PPTX"}
            ],
            "bullets": ["ReportLab Platypus", "Executive Cover Page", "Bento Grid Cards"]
        }
    ],
    "theme": "clean_light",
    "auto_open": True
})

print("Status:", result.success)
print("File:", result.data["file_path"])
```
