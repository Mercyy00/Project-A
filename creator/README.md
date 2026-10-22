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

### Day 3: Word and PowerPoint Makers (`creator/docx_maker.py`, `creator/pptx_maker.py`)
- **`creator/docx_maker.py`**:
  - `make_docx(title, sections, theme='clean_light', out_dir='workspace') -> str`
  - Word documents with custom margins, header/footer branding, styled Heading 1 titles, paragraphs, bullet lists, and tables with light borders and alternating row shading.
- **`creator/pptx_maker.py`**:
  - `make_pptx(title, sections, theme='clean_light', out_dir='workspace') -> str`
  - 16:9 widescreen presentation slides with accent bar, metadata, closing 'Thank you' slide, and auto-bullet splitting (max 6 bullets per slide).

### Day 4: Document Tools for the Brain (`creator/tools.py`)
- **`CreatePdfTool`**, **`CreateDocxTool`**, and **`CreatePptxTool`**:
  - Conforms strictly to `BaseTool` specification in `tools/base.py`.
  - `get_schema()` exports full OpenAPI / Gemini JSON parameter definitions.
  - Automatically registered into central `TOOL_REGISTRY` so Jarvis Brain can autonomously invoke document generators.

### Day 5: AI Outline to Document & Hindi/Marathi Devanagari Fonts (`creator/outline.py`)
- **`creator/outline.py` (`create_document`)**:
  - `create_document(topic, kind='pdf', theme='clean_light', language='en', out_dir='workspace', auto_open=True) -> str`
  - Requests 4-6 section structured JSON outline via Google Gemini (`google-genai` using `GEMINI_API_KEY` and `GEMINI_MODEL`) with automatic retry and Groq LPU / offline fallback.
  - Seamless support for English (`en`), Hindi (`hi`), and Marathi (`mr`).
  - Native Devanagari TrueType font embedding (`NotoSansDevanagari-Regular.ttf` and `Bold.ttf`) in ReportLab, python-docx, and python-pptx preventing square-box font corruption.
- **`CreateDocumentTool`**:
  - Exposed in `creator/tools.py` and exported in `TOOLS` for central tool discovery.
  - Enables voice/chat directives like: *"Make a presentation about solar energy in Marathi"* to work seamlessly end-to-end.

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
