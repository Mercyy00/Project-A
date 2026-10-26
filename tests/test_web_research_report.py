"""
Unit and Integration Tests for Web Research to Report (Tasks 23, 26).
Verifies webpage scraping (noise removal, headings, tables), research synthesis
with formal citation indexing ([1], [2]), and WebResearchReportTool execution.
"""

from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch

from creator.report_builder import (
    extract_clean_page,
    conduct_web_research,
    synthesize_research_sections,
    research_and_build_report,
)
from tools.web_tools import WebScrapeTool, WebResearchReportTool


class TestWebScraping:
    """Test webpage scraping, noise extraction, and table parsing."""

    def test_extract_clean_page(self):
        sample_html = """
        <html>
            <head><title>Quantum Computing Breakthrough</title></head>
            <body>
                <header><nav>Home | Contact | Ads</nav></header>
                <script>console.log("analytics track");</script>
                <h1>Quantum Supremacy in 2026</h1>
                <p>Superconducting qubits have reached 99.9% gate fidelity in multi-qubit systems.</p>
                <p>This milestone enables fault-tolerant quantum algorithms for molecular modeling.</p>
                <table>
                    <tr><th>Qubit Type</th><th>Fidelity</th></tr>
                    <tr><td>Superconducting</td><td>99.9%</td></tr>
                    <tr><td>Trapped Ion</td><td>99.8%</td></tr>
                </table>
                <footer>Copyright 2026 TechCorp</footer>
            </body>
        </html>
        """
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = sample_html.encode("utf-8")

        with patch("requests.get", return_value=mock_resp):
            data = extract_clean_page("https://example.com/quantum")
            assert data["status"] == "success"
            assert "Quantum Computing Breakthrough" in data["title"]
            assert "99.9% gate fidelity" in data["text"]
            assert "analytics track" not in data["text"]
            assert len(data["headings"]) >= 1
            assert len(data["tables"]) == 1
            assert data["tables"][0]["headers"] == ["Qubit Type", "Fidelity"]
            assert len(data["tables"][0]["rows"]) == 2


class TestResearchSynthesisAndReportBuilder:
    """Test synthesis of multi-source research into citations and PDF report."""

    def test_synthesize_research_sections_with_citations(self):
        mock_research = {
            "topic": "Clean Energy Storage",
            "sources": [
                {
                    "source_id": 1,
                    "title": "Solid State Batteries",
                    "url": "https://energy.org/solid-state",
                    "snippet": "Solid state batteries offer 2x higher volumetric energy density.",
                    "text": "Detailed findings on lithium metal anodes and solid electrolytes.",
                    "retrieved_at": "2026-10-26",
                    "tables": [],
                },
                {
                    "source_id": 2,
                    "title": "Flow Batteries for Grid",
                    "url": "https://grid.com/flow",
                    "snippet": "Vanadium redox flow systems provide 10+ hours storage duration.",
                    "text": "Grid scale installations exceed 100MWh globally.",
                    "retrieved_at": "2026-10-26",
                    "tables": [],
                }
            ]
        }

        summary, sections, metrics, chart_configs = synthesize_research_sections(
            topic="Clean Energy Storage",
            research_data=mock_research
        )

        assert "Clean Energy Storage" in summary
        assert len(sections) >= 3

        # Verify citation attribution [1] and [2]
        sources_section = next((s for s in sections if s["heading"] == "Sources & Bibliography"), None)
        assert sources_section is not None
        bullets = "\n".join(sources_section["bullets"])
        assert "[1]" in bullets
        assert "[2]" in bullets
        assert "https://energy.org/solid-state" in bullets

    def test_research_and_build_report_flow(self):
        mock_research_data = {
            "topic": "Neural Interfaces",
            "sources": [
                {
                    "source_id": 1,
                    "title": "Biocompatible Electrodes",
                    "url": "https://neuro.org/electrodes",
                    "snippet": "Flexible polymer arrays reduce glial scar formation.",
                    "text": "Chronic implantation tests show high signal-to-noise ratio over 2 years.",
                    "retrieved_at": "2026-10-26",
                    "tables": [],
                }
            ]
        }

        with patch("creator.report_builder.conduct_web_research", return_value=mock_research_data):
            report_info = research_and_build_report(
                topic="Neural Interfaces",
                format="pdf",
                max_sources=2,
                auto_open=False,
            )
            assert report_info["success"] is True
            assert report_info["topic"] == "Neural Interfaces"
            pdf_path = report_info.get("primary_file")
            assert pdf_path is not None
            assert Path(pdf_path).is_file()
            assert Path(pdf_path).stat().st_size > 0


class TestWebTools:
    """Test WebScrapeTool and WebResearchReportTool."""

    def test_web_scrape_tool(self):
        tool = WebScrapeTool()
        mock_page = {
            "url": "https://example.com",
            "title": "Test Page",
            "text": "This is informative scraped text from example.com.",
            "headings": ["Test Heading"],
            "tables": [],
            "status": "success",
        }
        with patch("tools.web_tools.extract_clean_page", return_value=mock_page):
            res = tool.run(url="https://example.com")
            assert res.success is True
            assert "Successfully scraped" in res.message
            assert res.data["title"] == "Test Page"

    def test_web_research_report_tool(self):
        tool = WebResearchReportTool()
        mock_report_result = {
            "success": True,
            "topic": "AI Semiconductors",
            "primary_file": "workspace/AI_Semiconductors_Report.pdf",
            "sources_count": 3,
            "message": "Successfully compiled executive research report for 'AI Semiconductors' with 3 sources."
        }
        with patch("tools.web_tools.research_and_build_report", return_value=mock_report_result):
            res = tool.run(topic="AI Semiconductors", format="pdf", max_sources=3, auto_open=False)
            assert res.success is True
            assert "executive research report" in res.message.lower()
            assert res.data["sources_count"] == 3
