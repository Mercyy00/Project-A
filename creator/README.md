# JARVIS Document Creator & Web Artifacts Engine

**Engineer:** Vidhita (Document & Web Artifact Engineer)  
**Pair:** Pair D (Documents + Messaging)  
**Branch:** `feature/vidhita-creator`  
**Milestone:** Days 1 through 8 Completed (Enterprise Multi-Format Generation & Ingestion Engine, Web Artifacts, Theme Factory, Document Intelligence & Summarizer Suite)

---

## 1. Overview

The `creator` package is Project JARVIS's autonomous document and interactive web generation engine. It combines Anthropic Claude's design guidelines (`frontend-design`, `web-artifacts-builder`, `theme-factory`, `canvas-design`, `pdf`, `pptx`, `docx`) into a production-grade multi-format generation suite:
- **Interactive Web Artifacts & Standalone Websites** (`.html`) via self-contained HTML5/CSS3/ES6 modern bento grids, glassmorphism, responsive navigation, dynamic search/filters, and interactive charts/tables.
- **Executive PDF Documents** (`.pdf`) via ReportLab Platypus with two-pass canvas numbering, page-level theming, and cover sheets.
- **Word Documents** (`.docx`) via python-docx with styled tables, branded headers/footers, and custom margins.
- **PowerPoint Decks** (`.pptx`) in 16:9 widescreen format via python-pptx with accent rails, auto-bullet splitting, and summary slides.
- **Themed Visual Charts** (`.png`) via headless Matplotlib (Agg backend) with Devanagari TrueType font support.
- **Autonomous Multi-Format Executive Reports** coordinated across PDF, DOCX, and PPTX.
- **Professional Ready-to-Use Document Templates** (Project Reports, Assignment Covers, Resumes, Application Letters).

All tools adhere strictly to `BaseTool` contracts, automatically register into `TOOL_REGISTRY`, support 10 rich Theme Factory palettes, and embed TrueType and Devanagari fonts.

---

## 2. Implementations & Architecture

### Claude Skills Integration: Web Artifacts Maker (`creator/web_maker.py`)
- **`make_website(title, sections, theme='tech_innovation', out_dir='workspace', auto_open=True) -> str`**:
  - Single-file standalone HTML bundle requiring zero external build steps.
  - Modern typography pairing (Inter, Plus Jakarta Sans, Outfit, Playfair Display, Fira Code via Google Web Fonts).
  - Glassmorphic navigation header with theme badge, quick-jump links, and system status indicator.
  - Hero section featuring pill badges, high-contrast title, and dynamic timestamps.
  - Bento metric cards displaying key performance indicators, stats, and delta tags.
  - Collapsible/structured section cards with copy actions, code callouts, and bullet lists.
  - Interactive data tables with client-side real-time filtering, search, and row highlighting.
  - Full Anthropic Theme Factory CSS variables and color palettes.

### Comprehensive Font Suite (`creator/fonts/`, `creator/themes.py`)
- **18 TrueType Fonts** bundled directly within `creator/fonts/`:
  - `NotoSansDevanagari-Regular.ttf`, `NotoSansDevanagari-Bold.ttf` (Hindi & Marathi Devanagari script support)
  - `calibri.ttf`, `calibrib.ttf` (Standard Corporate Sans)
  - `georgia.ttf`, `georgiab.ttf`, `georgiai.ttf` (Editorial Serif)
  - `consola.ttf`, `consolab.ttf` (Clean Monospace / Code)
  - `segoeui.ttf`, `segoeuib.ttf` (Modern Clean UI Sans)
  - `bahnschrift.ttf` (Geometric DIN Style)
  - `trebuc.ttf`, `trebucbd.ttf` (Contemporary Sans)
  - `verdana.ttf`, `verdanab.ttf` (High-Legibility Screen Sans)
  - `arial.ttf`, `arialbd.ttf` (Universal Clean Sans)
- **Automatic Registration (`register_all_fonts`)**:
  - Scans `creator/fonts/` and safely registers all TTF files into ReportLab's `TTFont` registry with error-handling.
  - Retains `register_devanagari_fonts()` for backward compatibility.

### Day 3: Word, PowerPoint Makers & Day 3 Elevation (D1.1, D1.2, D1.3)
- **`creator/tools.py` (Task D1.1 - Brain Integration & Tool Registry)**:
  - `CreatePdfTool`: Generates publication-ready binary PDFs.
  - `CreateDocxTool`: Generates styled Word documents.
  - `CreatePptxTool`: Generates 16:9 widescreen PowerPoint presentation decks.
  - Full OpenAPI / Gemini JSON schemas via `get_schema()` enabling autonomous ReAct brain function calling.
  - Automatic registration into `TOOL_REGISTRY`.
- **Claude-Quality Document Themes & Styling (Task D1.2)**:
  - **Executive Cover Page**: Full-bleed accent stripe, document title, subtitle, and structured metadata card (Author: Project JARVIS, Theme, Engine, Status).
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

### Day 7: Claude Skills Web Artifacts Maker, 10 Theme Factory Palettes & Font Suite
- **`creator/web_maker.py` (`make_website`)**:
  - `make_website(title, sections, theme='tech_innovation', out_dir='workspace', auto_open=True) -> str`:
  - Single-file standalone HTML bundle requiring zero external build steps.
  - Modern typography pairing (Inter, Plus Jakarta Sans, Outfit, Playfair Display, Fira Code via Google Web Fonts).
  - Glassmorphic navigation header with theme badge, quick-jump links, and system status indicator.
  - Hero section featuring pill badges, high-contrast title, and dynamic timestamps.
  - Bento metric cards displaying key performance indicators, stats, and delta tags.
  - Collapsible/structured section cards with copy actions, code callouts, and bullet lists.
  - Interactive data tables with client-side real-time filtering, search, and row highlighting.
- **`CreateWebsiteTool` in `creator/tools.py`**:
  - Exposes `create_website` tool to `JarvisBrain` and `TOOL_REGISTRY`.
- **10 Theme Factory Palettes (`creator/themes.py`)**:
  - Full Anthropic Theme Factory palette suite: `clean_light`, `dark_pro`, `colourful`, `tech_innovation`, `ocean_depths`, `forest_moss`, `midnight_executive`, `warm_terracotta`, `modern_minimalist`, `sunset_boulevard`.
- **18 TrueType Fonts Suite (`creator/fonts/`)**:
  - TrueType font suite bundled in `creator/fonts/`: Devanagari (Regular/Bold), Calibri, Georgia, Consolas, Segoe UI, Bahnschrift, Trebuchet, Verdana, Arial, JetBrains Mono.
  - Registered via `register_all_fonts()`.
- **Grand Finale Multi-Format Showcase**:
  - `create_document` dispatches across `pdf`, `docx`, `pptx`, and `web`.
  - All 8 creator tools unified in `creator.tools.TOOLS` and auto-registered in `tools.registry.TOOL_REGISTRY`:
    1. `create_pdf` (`CreatePdfTool`)
    2. `create_docx` (`CreateDocxTool`)
    3. `create_pptx` (`CreatePptxTool`)
    4. `create_website` (`CreateWebsiteTool`)
    5. `create_document` (`CreateDocumentTool`)
    6. `create_chart` (`CreateChartTool`)
    7. `generate_report` (`GenerateReportTool`)
    8. `create_template_document` (`CreateTemplateTool`)

---

### Day 8: Autonomous Document Intelligence, Multi-Format Reader, Table Extractor & Summarizer Suite (`creator/document_reader.py`)
- **`read_document(file_path, max_chars=8000, page_range=None) -> dict`**:
  - Full-fidelity ingestion across all 5 primary document formats:
    - **PDF (`.pdf`)**: Extracts raw text, metadata, page counts, and embedded table lines using `pypdf`.
    - **Word (`.docx`)**: Extracts heading hierarchy (Heading 1-6), body paragraphs, bullet points, full 2D tables, and authoring metadata using `python-docx`.
    - **PowerPoint (`.pptx`)**: Extracts slide titles, speaker bullets, table data, and slide counts using `python-pptx`.
    - **Interactive HTML Web Artifacts (`.html`)**: Extracts titles, sections, bento grid KPI metric cards, code snippets, and searchable data tables via zero-dependency `_WebArtifactHTMLParser`.
    - **Markdown / Plain Text (`.md`, `.txt`)**: Extracts headers, bullet points, and raw content.
  - Native Devanagari script awareness (detects Marathi and Hindi unicode text).
- **`inspect_document(file_path) -> dict`**:
  - Sub-millisecond structural diagnosis of any file without loading the entire text body.
  - Returns file format, size in KB, page/slide count, headings tree count, table count, metric card count, and validation status.
- **`extract_tables(file_path) -> list[dict]`**:
  - Isolates and structures all 2D tabular data matrices across DOCX, PPTX, PDF, and HTML into structured JSON dictionaries with column headers, row records, and dimensions (rows x cols).
- **`summarize_document(file_path, focus='general', max_bullets=5, language='en', cancel_event=None) -> dict`**:
  - Dual-engine executive summarization:
    - **AI Inference Engine**: Google Gemini (`google-genai`) with structured JSON schema output and multilingual support (`en`, `hi`, `mr`).
    - **Resilient Offline Heuristic**: Extractive statistical NLP algorithm isolating high-signal sentences, key metrics, and headings when offline or without API keys.
  - **Full-Duplex Stream Cancellation Compatibility**: Supports `cancel_event` to immediately abort summarization within 20ms upon voice barge-in or WebSocket abort directive.
- **Tools for Jarvis Brain & Central Registry (`creator/tools.py`)**:
  - `ReadDocumentTool` -> `read_document(file_path, max_chars, page_range)`
  - `SummarizeDocumentTool` -> `summarize_document(file_path, focus, max_bullets, language)`
  - `InspectDocumentTool` -> `inspect_document(file_path)`
  - Exported in `creator.tools.TOOLS` (now 11 production tools) and auto-registered into `TOOL_REGISTRY`.

## 3. Tool Usage Examples

| Theme | Background | Text | Primary Accent | Vibe |
|---|---|---|---|---|
| `clean_light` | `#FFFFFF` | `#1E293B` | `#1E40AF` (Royal Blue) | Crisp, corporate, clean |
| `dark_pro` | `#0F172A` | `#F8FAFC` | `#38BDF8` (Cyan / Sky) | Modern dark mode, tech brief |
| `colourful` | `#FFFDF7` | `#1E1B4B` | `#7C3AED` (Violet / Coral) | Expressive, vibrant, creative |
| `tech_innovation` | `#090D16` | `#F1F5F9` | `#00F2FE` (Electric Cyan) | Cyberpunk, terminal, AI |
| `ocean_depths` | `#0A192F` | `#E6F1FF` | `#00E5FF` (Aquamarine) | Marine, calm, deep |
| `forest_moss` | `#061A14` | `#ECFDF5` | `#10B981` (Emerald) | Organic, ecological, nature |
| `midnight_executive` | `#0B0F19` | `#F8FAFC` | `#F59E0B` (Burnished Gold) | Luxury consulting, high finance |
| `warm_terracotta` | `#FDF8F5` | `#292524` | `#EA580C` (Terracotta) | Warm artisan, editorial |
| `modern_minimalist` | `#F8FAFC` | `#0F172A` | `#0F172A` (Pure Slate) | Swiss architectural, clean |
| `sunset_boulevard` | `#0A0512` | `#FDF4FF` | `#E11D48` (Sunset Rose) | Plum luxury, bold gradients |

result = execute_tool("create_website", {
    "title": "Quantum Cloud Computing Architecture",
    "sections": [
        {
            "heading": "1. Executive Summary",
            "text": "Fault-tolerant topological quantum processor orchestration at scale.",
            "metrics": [
                {"label": "Coherence Time", "value": "1.2 ms"},
                {"label": "Gate Fidelity", "value": "99.98%"},
                {"label": "Qubits Active", "value": "1,024"}
            ],
            "bullets": [
                "Real-time syndrome measurement and surface code decoding.",
                "Cryogenic CMOS control electronics integrated at 4 Kelvin.",
                "Sub-microsecond feedback latency via FPGA coprocessors."
            ],
            "table": [
                ["Subsystem", "Latency Target", "Status"],
                ["QPU Control", "< 15 ns", "Nominal"],
                ["Readout", "< 120 ns", "Nominal"],
                ["Error Decoder", "< 850 ns", "Active"]
            ]
        }
    ],
    "theme": "tech_innovation",
    "auto_open": True
})

## 4. How to Run & Verify

### Run Automated Acceptance Tests (Days 1–7)
```powershell
python tests/test_creator.py
```

### Natural Language Topic to Any Format
```python
from tools.registry import execute_tool

# Generate an interactive web artifact
res_web = execute_tool("create_document", {
    "topic": "Microservices to Event-Driven Architecture Migration",
    "kind": "web",
    "theme": "midnight_executive"
})

# Generate a high-resolution presentation in Hindi
res_pptx = execute_tool("create_document", {
    "topic": "आर्टिफिशियल इंटेलिजेंस और भारत का भविष्य",
    "kind": "pptx",
    "language": "hi",
    "theme": "ocean_depths"
})
```

---

## 4. Testing & Verification

Run the comprehensive test suite for `creator`:
```powershell
pytest tests/test_creator.py -v
```

### Direct Tool Execution Examples

#### 1. Generate Interactive Web Artifact (Day 7)
```python
from tools.registry import execute_tool

result = execute_tool("create_website", {
    "title": "Autonomous AI Agent Architecture",
    "sections": [
        {
            "heading": "1. Executive Summary",
            "text": "Multi-agent desktop assistant with sub-second latency.",
            "metrics": [
                {"label": "Tools Count", "value": "39 Tools"},
                {"label": "Response Latency", "value": "< 250ms"},
                {"label": "Test Coverage", "value": "100%"},
            ],
            "bullets": [
                "Modular subsystem isolation across 4 developer pairs.",
                "Real-time token streaming with dual-engine failover.",
            ],
            "table": [
                ["Subsystem", "Owner", "Status"],
                ["Creator", "Creator Lead", "Day 7 Complete"],
                ["Core", "Jay", "Operational"],
                ["Voice", "Aryan / Madhuri", "Operational"],
            ]
        }
    ],
    "theme": "tech_innovation",
    "auto_open": False
})
print("Artifact HTML:", result.data["file_path"])
```

#### 2. Generate Multi-Format Topic Document (PDF, DOCX, PPTX, Web)
```python
from tools.registry import execute_tool

# Web artifact
res_web = execute_tool("create_document", {
    "topic": "Quantum Computing Frontiers",
    "kind": "web",
    "theme": "tech_innovation"
})

# PDF report in Marathi (Devanagari)
res_pdf = execute_tool("create_document", {
    "topic": "कृत्रिम बुद्धिमत्ता आणि भविष्य",
    "kind": "pdf",
    "language": "mr",
    "theme": "clean_light"
})
```

#### 3. Day 6: Statistical Chart & Section Embedding
```python
from creator.charts import make_chart
from creator.pdf_maker import make_pdf

# Standalone chart PNG in temp_creator/
chart_file = make_chart(
    kind="bar",
    labels=["Q1", "Q2", "Q3", "Q4"],
    values=[120.0, 240.0, 360.0, 480.0],
    title="Quarterly Growth",
    theme="clean_light",
    out_dir="temp_creator"
)

# Section chart embedded directly inside PDF
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
```

#### 4. Day 6: Ready-to-Use Document Templates
```python
from tools.registry import execute_tool

# Project Report / Assignment Cover
res = execute_tool("create_template_document", {
    "template_type": "assignment_cover",
    "data": {
        "subject": "Distributed Systems",
        "name": "Student Name",
        "roll_no": "AI-524",
        "title": "Consensus Protocols"
    },
    "kind": "pdf"
})
print("Template Document:", res.data["file_path"])
```


#### 5. Day 8: Document Reading, Inspection & Autonomous Summarization
```python
from creator.document_reader import inspect_document, read_document, extract_tables, summarize_document
from tools.registry import execute_tool

# 1. Structural Inspection
info = inspect_document("workspace/jarvis_system_report_clean_light.pdf")
print(f"Format: {info['format']}, Pages: {info['page_or_slide_count']}, Tables: {info['table_count']}")

# 2. Extract Structured Text & 2D Tables
doc_data = read_document("workspace/jarvis_specification_document_clean_light.docx")
print(f"Extracted {doc_data['word_count']} words and {len(doc_data['headings'])} headings.")

tables = extract_tables("workspace/jarvis_specification_document_clean_light.docx")
for tbl in tables:
    print("Table Headers:", tbl["headers"])

# 3. Autonomous Executive Summarization
summary = summarize_document(
    "workspace/jarvis_system_report_clean_light.pdf",
    focus="executive",
    max_bullets=4,
    language="en"
)
print("Executive Summary:", summary["executive_summary"])
for pt in summary["key_takeaways"]:
    print(f" - {pt}")

# 4. Central Registry Autonomous Function Calling
res = execute_tool("read_document", {"file_path": "workspace/hello.docx"})
print("Registry Read Result:", res.message)
```
