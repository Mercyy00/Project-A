# JARVIS Document Creator Engine

**Engineer:** Vidhita (Document Engineer)  
**Pair:** Pair D (Documents + Messaging)  
**Branch:** `feature/vidhita-creator`  
**Milestone:** Day 1 to Day 3 Completed

---

## 1. Overview

The `creator` package is Project JARVIS's autonomous document generation engine. It provides high-fidelity, programmatic document rendering across three standard productivity formats:
- **PDF Documents** (`.pdf`) via ReportLab Platypus
- **Word Documents** (`.docx`) via python-docx
- **PowerPoint Decks** (`.pptx`) in 16:9 widescreen format via python-pptx

---

## 2. Daily Implementations

### Day 1: Setup + Hello Documents (`creator/hello_docs.py`)
- Creates `workspace/hello.pdf` (ReportLab), `workspace/hello.docx` (python-docx), and `workspace/hello.pptx` (python-pptx).
- Each document has the title `'Hello from JARVIS'` and one line of text.
- Automatically creates the `workspace/` output directory if missing and prints full resolved paths.
- Wrapped in try/except with strict Python 3.11+ type hints and docstrings.

### Day 2: Theming Engine & Themed PDF Maker (`creator/themes.py`, `creator/pdf_maker.py`)
- **`creator/themes.py`**:
  - `THEMES` dictionary defining `'clean_light'`, `'dark_pro'`, and `'colourful'`.
  - Defines background colors, text colors, primary/secondary/accent tones, card and table styling, typography (ReportLab built-in fonts), and spacing metrics.
  - `get_theme(theme_name)` safely falls back to `'clean_light'` for unknown themes.
- **`creator/pdf_maker.py`**:
  - `make_pdf(title, sections, theme='clean_light', out_dir='workspace') -> str`
  - ReportLab Platypus architecture with cover title, headings, paragraphs, bullet lists, and styled data tables.
  - Custom `NumberedCanvas` two-pass rendering for dynamic page footers (`"Page X of Y"`) and document title tracking.
  - Page-level background painting matching the selected theme.
  - Builds 3-page PDFs adhering to Day 2 acceptance criteria.

### Day 3: Word and PowerPoint Makers (`creator/docx_maker.py`, `creator/pptx_maker.py`)
- **`creator/docx_maker.py`**:
  - `make_docx(title, sections, theme='clean_light', out_dir='workspace') -> str`
  - Standard Word document formatting with custom margins, header/footer branding, styled Heading 1 section titles, paragraphs, bullet lists, and tables with light borders and alternating row shading.
- **`creator/pptx_maker.py`**:
  - `make_pptx(title, sections, theme='clean_light', out_dir='workspace') -> str`
  - 16:9 widescreen presentation slides (`13.333" x 7.5"`).
  - Title slide with accent bar and metadata.
  - Section slides with automatic bullet splitting: **at most 6 bullets per slide** (longer lists automatically chunked across subsequent slides).
  - Closing `'Thank you'` slide.
  - Strict typography constraints: **Titles >= 28 pt**, **Body/bullets >= 18 pt**.
  - Consistent theme palette and contrast applied to all slide elements.

---

## 3. Themes Reference

| Theme | Background | Text | Primary Accent | Vibe |
|---|---|---|---|---|
| `clean_light` | `#FFFFFF` | `#1E293B` | `#1E40AF` (Royal Blue) | Crisp, corporate, clean |
| `dark_pro` | `#0F172A` | `#F8FAFC` | `#38BDF8` (Cyan / Sky) | Modern dark mode, tech brief |
| `colourful` | `#FFFDF7` | `#1E1B4B` | `#7C3AED` (Violet / Coral) | Expressive, vibrant, creative |

---

## 4. How to Run & Verify

### Run Acceptance Tests
To run the automated verification script:
```powershell
python tests/test_creator.py
```

### Run with Pytest
```powershell
pytest tests/test_creator.py -v
```

### Direct Script Usage Examples
```python
from creator import make_pdf, make_docx, make_pptx

sections = [
    {
        "heading": "Introduction",
        "text": "Autonomous document engine powered by JARVIS.",
        "bullets": ["High speed", "Clean formatting", "Multi-theme support"],
        "table": [
            ["Metric", "Value"],
            ["Accuracy", "100%"],
            ["Latency", "< 400ms"]
        ]
    }
]

# Generate PDF
pdf_path = make_pdf("Project Report", sections, theme="dark_pro")

# Generate Word DOCX
docx_path = make_docx("Project Report", sections, theme="clean_light")

# Generate 16:9 PowerPoint Deck
pptx_path = make_pptx("Project Report", sections, theme="colourful")
```
