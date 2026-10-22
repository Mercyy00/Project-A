"""Tests for JARVIS Document Creator (Days 1, 2, and 3 - Elevated).

Author: Vidhita (Document Engineer)
Module: tests.test_creator

Verifies:
- Day 1: Hello documents (hello.pdf, hello.docx, hello.pptx)
- Day 2: Themed 3-page PDF generation across all themes ('clean_light', 'dark_pro', 'colourful')
- Day 3: Themed Word DOCX and 6-slide PowerPoint PPTX across all themes
- D1.1: Document tools (CreatePdfTool, CreateDocxTool, CreatePptxTool) in creator/tools.py and TOOL_REGISTRY
- D1.2: Claude-quality themes, executive cover pages, bento grid metrics, and Devanagari font embedding
- D1.3: Auto-open document feature (auto_open=True / False)
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Dict, List

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Safe console encoding for Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import docx
from pptx import Presentation
import pytest

from creator.docx_maker import make_docx
from creator.hello_docs import generate_hello_docs
from creator.pdf_maker import make_pdf
from creator.pptx_maker import make_pptx
from creator.themes import THEMES, contains_devanagari, get_theme
from creator.outline import create_document, generate_outline
from creator.tools import (
    CreateDocxTool,
    CreatePdfTool,
    CreatePptxTool,
    CreateDocumentTool,
    TOOLS,
    create_docx,
    create_pdf,
    create_pptx,
    create_document_tool,
)
from tools.base import ToolResult
from tools.registry import TOOL_REGISTRY, execute_tool


def _count_pdf_pages(file_path: str) -> int:
    """Helper to count the number of pages in a PDF file."""
    with open(file_path, "rb") as f:
        content = f.read()
    pages = re.findall(rb"/Type\s*/Page\b", content)
    return len(pages)


@pytest.fixture
def sample_sections() -> List[Dict[str, Any]]:
    """Fixture providing comprehensive multi-section content."""
    return [
        {
            "heading": "1. Executive Summary",
            "text": "Project JARVIS introduces an autonomous multimodal assistant architecture engineered for desktop workflow automation.",
            "metrics": [
                {"label": "Response Latency", "value": "< 250ms"},
                {"label": "Document Fidelity", "value": "100% Binary"},
                {"label": "Uptime", "value": "99.99%"},
                {"label": "Memory Footprint", "value": "Low RAM"},
            ],
            "bullets": [
                "Real-time voice and text interaction loop.",
                "Automated high-quality document and presentation creation.",
                "Cross-channel communication via Telegram and WhatsApp.",
            ],
            "page_break_after": True,
        },
        {
            "heading": "2. Performance and Technical Metrics",
            "text": "The table below highlights the system benchmarks across key generation modules.",
            "bullets": [
                "Zero data leakage: credentials isolated strictly in local environment.",
                "Asynchronous processing pipeline ensuring low response latency.",
            ],
            "table": [
                ["Module", "Technology", "Target Latency", "Status"],
                ["PDF Engine", "ReportLab Platypus", "< 300 ms", "Operational"],
                ["DOCX Engine", "python-docx", "< 250 ms", "Operational"],
                ["PPTX Engine", "python-pptx (16:9)", "< 400 ms", "Operational"],
            ],
        },
    ]


@pytest.fixture
def sample_6_slide_sections() -> List[Dict[str, Any]]:
    """Fixture providing sections designed to produce at least a 6-slide deck."""
    return [
        {
            "heading": "1. Project Vision & Architecture",
            "text": "Autonomous assistant designed for modern desktop productivity.",
            "metrics": [
                {"label": "Modularity", "value": "4 Pairs"},
                {"label": "LLM Latency", "value": "Sub-sec"},
            ],
            "bullets": [
                "Modular decoupling across functional pairs.",
                "Zero external secret leaks via strict configuration boundaries.",
                "Direct programmatic generation of office document standards.",
            ],
        },
        {
            "heading": "2. Document Creator Suite",
            "text": "High-fidelity rendering across three core formats.",
            "bullets": [
                "Pixel-perfect PDF layout with cover pages and page counters.",
                "Standard-compliant Word documents with clean table borders.",
                "Presentation slides formatted in 16:9 widescreen layout.",
            ],
        },
        {
            "heading": "3. Theming & Aesthetics",
            "text": "Unified palette across all output media.",
            "bullets": [
                "Clean Light: crisp corporate styling with navy accents.",
                "Dark Pro: high-contrast dark mode for technical briefs.",
                "Colourful: vibrant palette with purple and coral tones.",
            ],
        },
        {
            "heading": "4. Verification & Milestones",
            "bullets": [
                "Day 1: Hello documents verified across PDF, DOCX, and PPTX.",
                "Day 2: Multi-page themed PDF maker with table styling.",
                "Day 3: Themed Word and 6-slide PowerPoint presentations.",
            ],
        },
    ]


# =====================================================================
# Day 1 Tests
# =====================================================================
def test_day1_hello_docs(tmp_path: Path) -> None:
    """Verify Day 1 hello docs generate valid non-empty files in all 3 formats."""
    out_dir = str(tmp_path / "day1")
    pdf_p, docx_p, pptx_p = generate_hello_docs(out_dir)

    for p in [pdf_p, docx_p, pptx_p]:
        file_obj = Path(p)
        assert file_obj.exists(), f"Day 1 file missing: {p}"
        assert file_obj.stat().st_size > 0, f"Day 1 file is empty: {p}"


# =====================================================================
# Day 2 Tests
# =====================================================================
@pytest.mark.parametrize("theme_name", ["clean_light", "dark_pro", "colourful"])
def test_day2_pdf_maker_3_pages(sample_sections: List[Dict[str, Any]], theme_name: str, tmp_path: Path) -> None:
    """Verify Day 2 acceptance test: 3-page PDF with cover, bullets, and table in all themes."""
    out_dir = str(tmp_path / "day2")
    pdf_path = make_pdf(
        title="JARVIS System Architecture",
        sections=sample_sections,
        theme=theme_name,
        out_dir=out_dir,
        auto_open=False,
    )

    pdf_file = Path(pdf_path)
    assert pdf_file.exists(), f"Generated PDF does not exist: {pdf_path}"
    assert pdf_file.stat().st_size > 500, f"Generated PDF is unexpectedly small: {pdf_path}"

    page_count = _count_pdf_pages(pdf_path)
    assert page_count >= 3, f"Expected at least 3 pages for Day 2 acceptance, found {page_count}"


def test_theme_fallback_pdf(sample_sections: List[Dict[str, Any]], tmp_path: Path) -> None:
    """Verify unknown theme safely falls back to clean_light in make_pdf."""
    out_dir = str(tmp_path / "day2_fallback")
    pdf_path = make_pdf(
        title="Fallback Theme Document",
        sections=sample_sections,
        theme="non_existent_theme",
        out_dir=out_dir,
        auto_open=False,
    )
    assert Path(pdf_path).exists()
    assert "clean_light" in pdf_path


# =====================================================================
# Day 3 Tests
# =====================================================================
@pytest.mark.parametrize("theme_name", ["clean_light", "dark_pro", "colourful"])
def test_day3_docx_maker(sample_sections: List[Dict[str, Any]], theme_name: str, tmp_path: Path) -> None:
    """Verify Day 3 Word document generation across all themes."""
    out_dir = str(tmp_path / "day3_docx")
    docx_path = make_docx(
        title="JARVIS System Specifications",
        sections=sample_sections,
        theme=theme_name,
        out_dir=out_dir,
        auto_open=False,
    )

    file_obj = Path(docx_path)
    assert file_obj.exists(), f"DOCX does not exist: {docx_path}"
    assert file_obj.stat().st_size > 1000, f"DOCX is unexpectedly small: {docx_path}"

    doc = docx.Document(docx_path)
    assert len(doc.paragraphs) > 0, "DOCX has no paragraphs"
    assert len(doc.tables) > 0, "DOCX has no tables"


@pytest.mark.parametrize("theme_name", ["clean_light", "dark_pro", "colourful"])
def test_day3_pptx_maker_6_slides(
    sample_6_slide_sections: List[Dict[str, Any]], theme_name: str, tmp_path: Path
) -> None:
    """Verify Day 3 acceptance test: 6-slide presentation deck in all themes."""
    out_dir = str(tmp_path / "day3_pptx")
    pptx_path = make_pptx(
        title="JARVIS Project Overview",
        sections=sample_6_slide_sections,
        theme=theme_name,
        out_dir=out_dir,
        auto_open=False,
    )

    file_obj = Path(pptx_path)
    assert file_obj.exists(), f"PPTX does not exist: {pptx_path}"
    assert file_obj.stat().st_size > 1000, f"PPTX is unexpectedly small: {pptx_path}"

    prs = Presentation(pptx_path)
    slide_count = len(prs.slides)
    assert slide_count >= 6, f"Expected at least 6 slides (Title + Content + Thank You), found {slide_count}"


def test_pptx_bullet_splitting(tmp_path: Path) -> None:
    """Verify that bullet lists with > 6 bullets are automatically split across slides."""
    out_dir = str(tmp_path / "day3_split")
    long_section = [
        {
            "heading": "Comprehensive Feature List",
            "bullets": [f"Feature item number {i}" for i in range(1, 14)],  # 13 bullets
        }
    ]
    pptx_path = make_pptx(
        title="Feature Breakdown",
        sections=long_section,
        theme="clean_light",
        out_dir=out_dir,
        auto_open=False,
    )
    prs = Presentation(pptx_path)
    # Expected: 1 Title + 3 Content slides (6 + 6 + 1) + 1 Thank you = 5 slides
    assert len(prs.slides) == 5, f"Expected 5 slides due to bullet splitting, got {len(prs.slides)}"


# =====================================================================
# D1.1: Document Tools & Registry Integration Tests
# =====================================================================
def test_tools_registered_in_central_registry() -> None:
    """Verify create_pdf, create_docx, and create_pptx are present in TOOL_REGISTRY."""
    assert "create_pdf" in TOOL_REGISTRY, "create_pdf not found in TOOL_REGISTRY"
    assert "create_docx" in TOOL_REGISTRY, "create_docx not found in TOOL_REGISTRY"
    assert "create_pptx" in TOOL_REGISTRY, "create_pptx not found in TOOL_REGISTRY"


def test_tool_schemas_conform_to_gemini_spec() -> None:
    """Verify all document tool schemas include title, sections, theme, and auto_open."""
    for tool_cls in [CreatePdfTool, CreateDocxTool, CreatePptxTool]:
        tool = tool_cls()
        schema = tool.get_schema()
        assert "name" in schema
        assert "parameters" in schema
        props = schema["parameters"]["properties"]
        assert "title" in props
        assert "sections" in props
        assert "theme" in props
        assert "auto_open" in props
        assert "title" in schema["parameters"]["required"]
        assert "sections" in schema["parameters"]["required"]


def test_execute_tool_create_pdf(tmp_path: Path) -> None:
    """Verify execute_tool('create_pdf', ...) returns success ToolResult with real binary PDF."""
    result: ToolResult = execute_tool(
        "create_pdf",
        {
            "title": "Quantum Computing Architecture",
            "sections": [
                {
                    "heading": "1. Qubit Coherence",
                    "text": "State-of-the-art superconducting qubits.",
                    "metrics": [
                        {"label": "Coherence Time", "value": "120 us"},
                        {"label": "Fidelity", "value": "99.9%"},
                    ],
                    "bullets": ["Transmon qubits", "Cryogenic dilution refrigerator"],
                }
            ],
            "theme": "dark_pro",
            "out_dir": str(tmp_path),
            "auto_open": False,
        },
    )
    assert result.success is True, f"create_pdf failed: {result.message}"
    assert result.data is not None
    file_path = result.data["file_path"]
    assert Path(file_path).exists()
    assert Path(file_path).stat().st_size > 1000  # Never corrupted 464 bytes!
    assert result.data["format"] == "pdf"


def test_execute_tool_create_docx(tmp_path: Path) -> None:
    """Verify execute_tool('create_docx', ...) returns success ToolResult with real binary DOCX."""
    result: ToolResult = execute_tool(
        "create_docx",
        {
            "title": "Autonomous Agent Protocols",
            "sections": [
                {
                    "heading": "1. Protocol Specifications",
                    "text": "Defines agent handshake and verification rules.",
                    "metrics": [
                        {"label": "Sync Speed", "value": "< 50ms"},
                        {"label": "Encryption", "value": "AES-256"},
                    ],
                    "bullets": ["Standard BaseTool contracts", "Strict folder boundaries"],
                }
            ],
            "theme": "clean_light",
            "out_dir": str(tmp_path),
            "auto_open": False,
        },
    )
    assert result.success is True, f"create_docx failed: {result.message}"
    file_path = result.data["file_path"]
    assert Path(file_path).exists()
    assert Path(file_path).stat().st_size > 1000
    assert result.data["format"] == "docx"


def test_execute_tool_create_pptx(tmp_path: Path) -> None:
    """Verify execute_tool('create_pptx', ...) returns success ToolResult with real binary PPTX."""
    result: ToolResult = execute_tool(
        "create_pptx",
        {
            "title": "JARVIS Executive Summary",
            "sections": [
                {
                    "heading": "1. Key Accomplishments",
                    "text": "Autonomous document creator suite.",
                    "metrics": [
                        {"label": "Formats", "value": "PDF/DOCX/PPTX"},
                        {"label": "Themes", "value": "3 Styles"},
                    ],
                    "bullets": ["ReportLab Platypus", "python-docx", "python-pptx 16:9"],
                }
            ],
            "theme": "colourful",
            "out_dir": str(tmp_path),
            "auto_open": False,
        },
    )
    assert result.success is True, f"create_pptx failed: {result.message}"
    file_path = result.data["file_path"]
    assert Path(file_path).exists()
    assert Path(file_path).stat().st_size > 1000
    assert result.data["format"] == "pptx"


def test_tools_handle_json_string_sections(tmp_path: Path) -> None:
    """Verify that when an LLM passes sections as a JSON string, it parses cleanly."""
    json_sections = json.dumps([
        {
            "heading": "LLM Generated Section",
            "text": "Parsed from a raw string input.",
            "bullets": ["Point A", "Point B"],
        }
    ])
    result = create_pdf(
        title="JSON String Parsing Test",
        sections=json_sections,
        theme="clean_light",
        out_dir=str(tmp_path),
        auto_open=False,
    )
    assert result.success is True
    assert Path(result.data["file_path"]).exists()


def test_tools_reject_empty_title() -> None:
    """Verify that passing an empty title returns a structured ToolResult failure."""
    result = create_pdf(title="", sections=[{"heading": "Test"}], auto_open=False)
    assert result.success is False
    assert "title cannot be empty" in result.message.lower()


# =====================================================================
# D1.2: Claude-Quality Themes & Devanagari Font Tests
# =====================================================================
def test_devanagari_marathi_hindi_pdf_generation(tmp_path: Path) -> None:
    """Verify that Marathi / Hindi text generates valid binary PDF with Noto Sans Devanagari."""
    marathi_sections = [
        {
            "heading": "१. प्रकल्प सारांश",
            "text": "प्रकल्प जार्विस हा एक स्वायत्त डेस्कटॉप सहाय्यक आहे.",
            "metrics": [
                {"label": "कार्यक्षमता", "value": "१००%"},
                {"label": "विलंब", "value": "< ३०० मिलीसेकंद"},
            ],
            "bullets": [
                "मराठी आणि हिंदी भाषेचे संपूर्ण समर्थन.",
                "देवनागरी फॉन्टचे अचूक रेंडरिंग.",
            ],
        }
    ]
    pdf_path = make_pdf(
        title="प्रकल्प जार्विस: दस्तऐवज चाचणी",
        sections=marathi_sections,
        theme="clean_light",
        out_dir=str(tmp_path),
        auto_open=False,
    )
    file_obj = Path(pdf_path)
    assert file_obj.exists()
    assert file_obj.stat().st_size > 5000  # Rich binary font data embedded!


def test_devanagari_marathi_hindi_docx_generation(tmp_path: Path) -> None:
    """Verify that Marathi / Hindi text generates valid binary Word document."""
    marathi_sections = [
        {
            "heading": "१. प्रकल्प तपशील",
            "text": "हा दस्तऐवज मायक्रोसॉफ्ट वर्ड स्वरूपात तयार करण्यात आला आहे.",
            "bullets": ["मराठी फॉन्ट", "स्वच्छ लेआउट"],
        }
    ]
    docx_path = make_docx(
        title="प्रकल्प जार्विस वर्ड",
        sections=marathi_sections,
        theme="clean_light",
        out_dir=str(tmp_path),
        auto_open=False,
    )
    file_obj = Path(docx_path)
    assert file_obj.exists()
    assert file_obj.stat().st_size > 10000


# =====================================================================
# D1.3: Auto-Open Document Tests
# =====================================================================
def test_auto_open_parameter_in_all_makers(tmp_path: Path) -> None:
    """Verify auto_open parameter is accepted without error across all makers."""
    sec = [{"heading": "Auto-Open Test", "text": "Testing auto-open flag execution."}]
    pdf_p = make_pdf("Auto Open PDF", sec, out_dir=str(tmp_path), auto_open=False)
    docx_p = make_docx("Auto Open DOCX", sec, out_dir=str(tmp_path), auto_open=False)
    pptx_p = make_pptx("Auto Open PPTX", sec, out_dir=str(tmp_path), auto_open=False)

    assert Path(pdf_p).exists()
    assert Path(docx_p).exists()
    assert Path(pptx_p).exists()


# =====================================================================
# Day 5 Tests: create_document & CreateDocumentTool (Multilingual)
# =====================================================================
def test_day5_create_document_pdf(tmp_path: Path) -> None:
    """Verify Day 5 create_document generates valid PDF on a topic."""
    out_file = create_document(
        topic="Solar Energy Innovations",
        kind="pdf",
        theme="clean_light",
        language="en",
        out_dir=str(tmp_path),
        auto_open=False,
    )
    assert Path(out_file).exists()
    assert Path(out_file).stat().st_size > 1000
    assert out_file.endswith(".pdf")


def test_day5_create_document_docx(tmp_path: Path) -> None:
    """Verify Day 5 create_document generates valid Word DOCX on a topic."""
    out_file = create_document(
        topic="Artificial Intelligence Architecture",
        kind="docx",
        theme="dark_pro",
        language="en",
        out_dir=str(tmp_path),
        auto_open=False,
    )
    assert Path(out_file).exists()
    assert Path(out_file).stat().st_size > 1000
    assert out_file.endswith(".docx")


def test_day5_create_document_pptx(tmp_path: Path) -> None:
    """Verify Day 5 create_document generates valid PowerPoint presentation on a topic."""
    out_file = create_document(
        topic="Autonomous Desktop Agents",
        kind="pptx",
        theme="colourful",
        language="en",
        out_dir=str(tmp_path),
        auto_open=False,
    )
    assert Path(out_file).exists()
    assert Path(out_file).stat().st_size > 1000
    assert out_file.endswith(".pptx")


def test_day5_create_document_hindi(tmp_path: Path) -> None:
    """Verify Day 5 Hindi document generation with native Devanagari script."""
    out_file = create_document(
        topic="सौर ऊर्जा",
        kind="pdf",
        theme="clean_light",
        language="hi",
        out_dir=str(tmp_path),
        auto_open=False,
    )
    assert Path(out_file).exists()
    assert Path(out_file).stat().st_size > 5000  # Embedded Devanagari font data
    assert out_file.endswith(".pdf")


def test_day5_create_document_marathi(tmp_path: Path) -> None:
    """Verify Day 5 Marathi document generation with native Devanagari script."""
    out_file = create_document(
        topic="प्रकल्प नियोजन आणि व्यवस्थापन",
        kind="docx",
        theme="dark_pro",
        language="mr",
        out_dir=str(tmp_path),
        auto_open=False,
    )
    assert Path(out_file).exists()
    assert Path(out_file).stat().st_size > 1000
    assert out_file.endswith(".docx")


def test_day5_create_document_tool_schema() -> None:
    """Verify CreateDocumentTool conforms to BaseTool and exports OpenAPI schema."""
    tool = CreateDocumentTool()
    schema = tool.get_schema()
    assert schema["name"] == "create_document"
    assert "parameters" in schema
    assert "topic" in schema["parameters"]["properties"]
    assert "topic" in schema["parameters"]["required"]
    assert "kind" in schema["parameters"]["properties"]
    assert "language" in schema["parameters"]["properties"]


def test_day5_create_document_tool_execution(tmp_path: Path) -> None:
    """Verify executing CreateDocumentTool via TOOL_REGISTRY succeeds."""
    res = execute_tool(
        "create_document",
        {
            "topic": "Quantum Computing Future",
            "kind": "pdf",
            "theme": "clean_light",
            "language": "en",
            "out_dir": str(tmp_path),
            "auto_open": False,
        },
    )
    assert res.success is True
    assert "successfully created" in res.message.lower()
    assert Path(res.data["file_path"]).exists()


def test_day5_create_document_tool_in_registry() -> None:
    """Verify create_document is auto-registered in TOOL_REGISTRY."""
    assert "create_document" in TOOL_REGISTRY
    assert isinstance(TOOL_REGISTRY["create_document"], CreateDocumentTool)


# =====================================================================
# Runnable Standalone Verification Script
# =====================================================================
def run_verification() -> bool:
    """Execute all acceptance verification tests and display structured summary."""
    print("=" * 75)
    print("      JARVIS CREATOR MODULE - DAYS 1, 2, 3 & TOOLS ACCEPTANCE VERIFICATION")
    print("=" * 75)

    workspace_dir = Path("workspace")
    workspace_dir.mkdir(parents=True, exist_ok=True)

    test_sections = [
        {
            "heading": "1. Architecture and Design Goals",
            "text": "JARVIS Pair D module provides rich programmatic document outputs with dynamic themes.",
            "metrics": [
                {"label": "PDF Engine", "value": "ReportLab Platypus"},
                {"label": "Word Engine", "value": "python-docx"},
                {"label": "Deck Engine", "value": "python-pptx (16:9)"},
                {"label": "Font Support", "value": "Noto Sans Devanagari"},
            ],
            "bullets": [
                "Full support for ReportLab Platypus, python-docx, and python-pptx.",
                "Independent thematic styling for light, dark, and colourful palettes.",
                "Strict boundary isolation adhering to project guidelines.",
            ],
            "page_break_after": True,
        },
        {
            "heading": "2. Production Metrics & Deliverables",
            "text": "All required deliverables for Days 1 through 3 and Tools are fully operational.",
            "bullets": [
                "Day 1: Hello PDF, DOCX, and PPTX generator.",
                "Day 2: Themed 3-page PDF with cover, bullets, and table.",
                "Day 3: Themed Word DOCX and 6-slide PowerPoint decks.",
                "Day 3 Elevation: Claude-quality themes, bento grid cards, Devanagari fonts, and auto_open.",
            ],
            "table": [
                ["Deliverable", "Technology", "Status", "Target"],
                ["hello_docs.py", "ReportLab / docx / pptx", "PASS", "Day 1"],
                ["themes.py", "THEMES dict & palettes", "PASS", "Day 2"],
                ["pdf_maker.py", "Platypus + NumberedCanvas", "PASS", "Day 2"],
                ["docx_maker.py", "python-docx + borders", "PASS", "Day 3"],
                ["pptx_maker.py", "python-pptx 16:9 + 6-slides", "PASS", "Day 3"],
                ["tools.py", "BaseTool + Central Registry", "PASS", "Day 3/4"],
            ],
        },
    ]

    six_slide_sections = [
        {
            "heading": "1. Introduction & Context",
            "text": "Overview of JARVIS autonomous document generation system.",
            "metrics": [
                {"label": "Lead Engineer", "value": "Vidhita"},
                {"label": "Pair Module", "value": "Pair D"},
            ],
            "bullets": [
                "Engineered by Vidhita (Document Engineer).",
                "Built for desktop assistant workflow.",
            ],
        },
        {
            "heading": "2. Themes Engine",
            "text": "Supports three distinct visual styles.",
            "bullets": [
                "Clean Light: Royal blue and slate with high legibility.",
                "Dark Pro: Charcoal and cyan for modern technical presentations.",
                "Colourful: Violet and coral for expressive decks.",
            ],
        },
        {
            "heading": "3. Formatting Capabilities",
            "text": "Adheres to strict presentation typography standards.",
            "bullets": [
                "Titles are at least 28 pt across all slides.",
                "Body text and bullets are at least 18 pt.",
                "Lists exceeding 6 bullets are automatically chunked.",
            ],
        },
        {
            "heading": "4. Quality Verification",
            "bullets": [
                "All functions include strict type hints and docstrings.",
                "Comprehensive unit and acceptance tests included.",
                "Automated error handling with fallback defaults.",
            ],
        },
    ]

    try:
        # 1. Day 1 Verification
        print("\n[DAY 1] Verifying Hello Docs Generation...")
        h_pdf, h_docx, h_pptx = generate_hello_docs(str(workspace_dir))
        for p in [h_pdf, h_docx, h_pptx]:
            assert Path(p).exists() and Path(p).stat().st_size > 0
        print("  [PASS] Day 1 Hello Docs passed.")

        # 2. Day 2 Verification (3-page PDF across all 3 themes)
        print("\n[DAY 2] Verifying Themed 3-Page PDFs...")
        for theme in ["clean_light", "dark_pro", "colourful"]:
            pdf_out = make_pdf(
                title="JARVIS System Report",
                sections=test_sections,
                theme=theme,
                out_dir=str(workspace_dir),
                auto_open=False,
            )
            pages = _count_pdf_pages(pdf_out)
            assert pages >= 3, f"Expected >= 3 pages in {theme}, got {pages}"
            print(f"  [PASS] PDF ({theme}): {pdf_out} [{pages} pages, {Path(pdf_out).stat().st_size} bytes]")

        # 3. Day 3 Verification (Word DOCX across all 3 themes)
        print("\n[DAY 3] Verifying Themed Word Documents...")
        for theme in ["clean_light", "dark_pro", "colourful"]:
            docx_out = make_docx(
                title="JARVIS Specification Document",
                sections=test_sections,
                theme=theme,
                out_dir=str(workspace_dir),
                auto_open=False,
            )
            doc = docx.Document(docx_out)
            assert len(doc.paragraphs) > 0 and len(doc.tables) > 0
            print(f"  [PASS] DOCX ({theme}): {docx_out} [{Path(docx_out).stat().st_size} bytes]")

        # 4. Day 3 Verification (6-slide PPTX across all 3 themes)
        print("\n[DAY 3] Verifying Themed 6-Slide PowerPoint Decks...")
        for theme in ["clean_light", "dark_pro", "colourful"]:
            pptx_out = make_pptx(
                title="JARVIS Project Deck",
                sections=six_slide_sections,
                theme=theme,
                out_dir=str(workspace_dir),
                auto_open=False,
            )
            prs = Presentation(pptx_out)
            slides = len(prs.slides)
            assert slides >= 6, f"Expected >= 6 slides in {theme}, got {slides}"
            print(f"  [PASS] PPTX ({theme}): {pptx_out} [{slides} slides, {Path(pptx_out).stat().st_size} bytes]")

        # 5. D1.1: Document Tools Registration & Execution
        print("\n[D1.1] Verifying Tools Registration and Execution in TOOL_REGISTRY...")
        for t_name in ["create_pdf", "create_docx", "create_pptx"]:
            assert t_name in TOOL_REGISTRY, f"Tool '{t_name}' missing in TOOL_REGISTRY"
            res = execute_tool(
                t_name,
                {
                    "title": f"JARVIS {t_name.upper()} Test",
                    "sections": test_sections,
                    "theme": "clean_light",
                    "out_dir": str(workspace_dir),
                    "auto_open": False,
                },
            )
            assert res.success is True, f"{t_name} execution failed: {res.message}"
            assert res.data["bytes"] > 1000, f"{t_name} produced invalid file size: {res.data['bytes']} bytes"
            print(f"  [PASS] {t_name}: {res.data['file_path']} ({res.data['bytes']} bytes)")

        # 6. D1.2: Claude-Quality Devanagari Multilingual Verification
        print("\n[D1.2] Verifying Devanagari (Marathi / Hindi) Font Embedding...")
        marathi_sec = [
            {
                "heading": "१. प्रकल्प उद्दिष्टे आणि प्रगती",
                "text": "हा दस्तऐवज मराठी आणि हिंदी भाषेतील देवनागरी फॉन्ट तपासणीसाठी तयार केला आहे.",
                "metrics": [
                    {"label": "अचूकता", "value": "१००%"},
                    {"label": "वेळ", "value": "< २५० मिलीसेकंद"},
                ],
                "bullets": ["देवनागरी फॉन्ट योग्य प्रकारे रेंडर होतो.", "कोणतीही अक्षरे तुटलेली नाहीत."],
            }
        ]
        dev_res = execute_tool(
            "create_pdf",
            {
                "title": "प्रकल्प जार्विस: मराठी दस्तऐवज",
                "sections": marathi_sec,
                "theme": "clean_light",
                "out_dir": str(workspace_dir),
                "auto_open": False,
            },
        )
        assert dev_res.success is True
        print(f"  [PASS] Devanagari PDF: {dev_res.data['file_path']} ({dev_res.data['bytes']} bytes)")

        print("\n" + "=" * 75)
        print("[SUCCESS] ALL ACCEPTANCE TESTS FOR DAYS 1, 2, 3 & D1.1-D1.3 PASSED!")
        print("=" * 75)
        return True

    except Exception as exc:
        print(f"\n[FAIL] Verification encountered an error: {exc}", file=sys.stderr)
        return False


if __name__ == "__main__":
    success = run_verification()
    sys.exit(0 if success else 1)
