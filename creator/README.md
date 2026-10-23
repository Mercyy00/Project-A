# JARVIS Document Creator & Web Artifacts Engine

**Engineer:** Vidhita (Document & Web Artifact Engineer)  
**Pair:** Pair D (Documents + Messaging)  
**Branch:** `feature/vidhita-creator`  
**Milestone:** Enterprise Multi-Format Engine (Claude Skills Integrated)

---

## 1. Overview

The `creator` package is Project JARVIS's autonomous document and interactive web generation engine. It combines Anthropic Claude's design guidelines (`frontend-design`, `web-artifacts-builder`, `theme-factory`, `canvas-design`, `pdf`, `pptx`, `docx`) into a production-grade multi-format generation suite:
- **Interactive Web Artifacts & Standalone Websites** (`.html`) via self-contained HTML5/CSS3/ES6 modern bento grids, glassmorphism, responsive navigation, dynamic search/filters, and interactive charts/tables.
- **Executive PDF Documents** (`.pdf`) via ReportLab Platypus with two-pass canvas numbering, page-level theming, and cover sheets.
- **Word Documents** (`.docx`) via python-docx with styled tables, branded headers/footers, and custom margins.
- **PowerPoint Decks** (`.pptx`) in 16:9 widescreen format via python-pptx with accent rails, auto-bullet splitting, and summary slides.

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

### Theme Factory Engine (`creator/themes.py`)
10 Anthropic Theme Factory and modern themes available across all 4 document formats:
1. `clean_light` — Crisp, executive corporate palette (Royal Blue `#1E40AF` on Pure White `#FFFFFF`).
2. `dark_pro` — High-tech dark mode (Sky Blue `#38BDF8` on Slate `#0F172A`).
3. `colourful` — Expressive and creative (Violet `#7C3AED` on Warm Cream `#FFFDF7`).
4. `tech_innovation` — Cyberpunk / AI terminal (Electric Cyan `#00F2FE` & Neon Purple on Obsidian `#090D16`).
5. `ocean_depths` — Marine executive tone (Aquamarine `#00E5FF` on Deep Abyss `#0A192F`).
6. `forest_moss` — Organic editorial design (Emerald & Sage `#10B981` on Pine Deep `#061A14`).
7. `midnight_executive` — Luxury consulting style (Burnished Gold `#F59E0B` on Midnight `#0B0F19`).
8. `warm_terracotta` — Artisan warm aesthetic (Terracotta `#EA580C` & Amber on Cream `#FDF8F5`).
9. `modern_minimalist` — Swiss typographic aesthetic (Pure Slate `#0F172A` on Off-White `#F8FAFC`).
10. `sunset_boulevard` — Bold gradient palette (Warm Rose `#F43F5E` & Orange on Charcoal `#18181B`).

### Outline Engine & Multi-Format Dispatcher (`creator/outline.py`)
- **`create_document(topic, kind='web', theme='tech_innovation', language='en', out_dir='workspace', auto_open=True) -> str`**:
  - Generates multi-section structured outlines using Google Gemini (`google-genai`), Groq LPU fallback, or offline algorithmic templates.
  - Dispatches seamlessly to:
    - `kind="web"` / `"html"` / `"website"` / `"artifact"` -> `make_website`
    - `kind="pdf"` -> `make_pdf`
    - `kind="docx"` -> `make_docx`
    - `kind="pptx"` -> `make_pptx`
  - Multilingual support for English (`en`), Hindi (`hi`), and Marathi (`mr`).

### Brain Tools Integration (`creator/tools.py`)
All tools are exported in `creator.tools.TOOLS` and auto-registered in `tools.registry.TOOL_REGISTRY`:
- **`CreateWebsiteTool`** (`create_website`): Direct programmatic website generation.
- **`CreateDocumentTool`** (`create_document`): AI-driven outline + multi-format document generation (`pdf`, `docx`, `pptx`, `web`).
- **`CreatePdfTool`** (`create_pdf`): Direct programmatic PDF rendering.
- **`CreateDocxTool`** (`create_docx`): Direct programmatic Word document rendering.
- **`CreatePptxTool`** (`create_pptx`): Direct programmatic PowerPoint slide deck rendering.

---

## 3. Tool Usage Examples

### Autonomous Web Artifact Creation
```python
from tools.registry import execute_tool

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

print("Success:", result.success)
print("Artifact Path:", result.data["file_path"])
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

All 35 tests pass across unit rendering, schema verification, multilingual font rendering, Theme Factory definitions, and tool registry execution.
