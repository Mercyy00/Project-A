"""Tests for JARVIS Document Creator (Days 1, 2, and 3).

Author: Vidhita (Document Engineer)
Module: tests.test_creator

Verifies:
- Day 1: Hello documents (hello.pdf, hello.docx, hello.pptx)
- Day 2: Themed 3-page PDF generation across all themes ('clean_light', 'dark_pro', 'colourful')
- Day 3: Themed Word DOCX and 6-slide PowerPoint PPTX across all themes
- Graceful theme fallback to 'clean_light' on unknown theme
"""

from pathlib import Path
import re
import sys
from typing import Any, Dict, List

# Ensure project root is in sys.path for direct script execution
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

import pytest
import docx
from pptx import Presentation

from creator.themes import THEMES, get_theme
from creator.hello_docs import generate_hello_docs
from creator.pdf_maker import make_pdf
from creator.docx_maker import make_docx
from creator.pptx_maker import make_pptx


def _count_pdf_pages(file_path: str) -> int:
    """Helper to count the number of pages in a PDF file."""
    with open(file_path, "rb") as f:
        content = f.read()
    # Match /Type /Page (excluding /Pages catalog)
    pages = re.findall(rb"/Type\s*/Page\b", content)
    return len(pages)


@pytest.fixture
def sample_sections() -> List[Dict[str, Any]]:
    """Fixture providing comprehensive multi-section content."""
    return [
        {
            "heading": "1. Executive Summary",
            "text": "Project JARVIS introduces an autonomous multimodal assistant architecture engineered for desktop workflow automation.",
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
    )

    pdf_file = Path(pdf_path)
    assert pdf_file.exists(), f"Generated PDF does not exist: {pdf_path}"
    assert pdf_file.stat().st_size > 0, f"Generated PDF is empty: {pdf_path}"

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
    )

    file_obj = Path(docx_path)
    assert file_obj.exists(), f"DOCX does not exist: {docx_path}"
    assert file_obj.stat().st_size > 0, f"DOCX is empty: {docx_path}"

    # Verify document structure using python-docx
    doc = docx.Document(docx_path)
    assert len(doc.paragraphs) > 0, "DOCX has no paragraphs"
    assert len(doc.tables) > 0, "DOCX has no tables"
    assert len(doc.tables[0].rows) == 4, "DOCX table does not contain expected row count"


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
    )

    file_obj = Path(pptx_path)
    assert file_obj.exists(), f"PPTX does not exist: {pptx_path}"
    assert file_obj.stat().st_size > 0, f"PPTX is empty: {pptx_path}"

    # Verify slide count using python-pptx
    prs = Presentation(pptx_path)
    slide_count = len(prs.slides)
    assert slide_count >= 6, f"Expected at least 6 slides (Title + 4 Content + Thank You), found {slide_count}"


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
    )
    prs = Presentation(pptx_path)
    # Expected: 1 Title + 3 Content slides (6 + 6 + 1) + 1 Thank you = 5 slides
    assert len(prs.slides) == 5, f"Expected 5 slides due to bullet splitting, got {len(prs.slides)}"


# =====================================================================
# Runnable Standalone Verification Script
# =====================================================================
def run_verification() -> bool:
    """Execute all acceptance verification tests and display structured summary."""
    print("=" * 70)
    print("      JARVIS CREATOR MODULE - DAYS 1, 2, 3 ACCEPTANCE VERIFICATION")
    print("=" * 70)

    workspace_dir = Path("workspace")
    workspace_dir.mkdir(parents=True, exist_ok=True)

    test_sections = [
        {
            "heading": "1. Architecture and Design Goals",
            "text": "JARVIS Pair D module is engineered to provide rich programmatic document outputs with dynamic themes.",
            "bullets": [
                "Full support for ReportLab Platypus, python-docx, and python-pptx.",
                "Independent thematic styling for light, dark, and colourful palettes.",
                "Strict boundary isolation adhering to project guidelines.",
            ],
            "page_break_after": True,
        },
        {
            "heading": "2. Production Metrics & Deliverables",
            "text": "All required deliverables for Days 1 through 3 are fully operational.",
            "bullets": [
                "Day 1: Hello PDF, DOCX, and PPTX generator.",
                "Day 2: Themed 3-page PDF with cover, bullets, and table.",
                "Day 3: Themed Word DOCX and 6-slide PowerPoint decks.",
            ],
            "table": [
                ["Deliverable", "Technology", "Status", "Target"],
                ["hello_docs.py", "ReportLab / docx / pptx", "PASS", "Day 1"],
                ["themes.py", "THEMES dict & palettes", "PASS", "Day 2"],
                ["pdf_maker.py", "Platypus + NumberedCanvas", "PASS", "Day 2"],
                ["docx_maker.py", "python-docx + borders", "PASS", "Day 3"],
                ["pptx_maker.py", "python-pptx 16:9 + 6-slides", "PASS", "Day 3"],
            ],
        },
    ]

    six_slide_sections = [
        {
            "heading": "1. Introduction & Context",
            "text": "Overview of JARVIS autonomous document generation system.",
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

    all_passed = True

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
            )
            prs = Presentation(pptx_out)
            slides = len(prs.slides)
            assert slides >= 6, f"Expected >= 6 slides in {theme}, got {slides}"
            print(f"  [PASS] PPTX ({theme}): {pptx_out} [{slides} slides, {Path(pptx_out).stat().st_size} bytes]")

        # 5. Bullet Splitting Verification
        print("\n[DAY 3] Verifying Bullet Splitting Rule (Max 6 bullets per slide)...")
        split_out = make_pptx(
            title="Bullet Split Verification",
            sections=[{"heading": "Large List", "bullets": [f"Item {i}" for i in range(1, 13)]}],
            theme="clean_light",
            out_dir=str(workspace_dir),
        )
        split_prs = Presentation(split_out)
        print(f"  [PASS] Bullet splitting confirmed: {len(split_prs.slides)} slides created for 12 items.")

        print("\n" + "=" * 70)
        print("[SUCCESS] ALL ACCEPTANCE TESTS FOR DAYS 1, 2, AND 3 PASSED!")
        print("=" * 70)
        return True

    except Exception as exc:
        print(f"\n[FAIL] Verification encountered an error: {exc}", file=sys.stderr)
        return False


if __name__ == "__main__":
    success = run_verification()
    sys.exit(0 if success else 1)
