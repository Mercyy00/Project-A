"""
Web Scraping and Web Research Report Tools for Project JARVIS.
Author: Abhijit & Vidhita (Pair C & D integration)

Conforms strictly to BaseTool specification and ARCHITECTURE.md:
1. WebScrapeTool: Fetches clean text, headings, and data tables from any web URL without ads or scripts.
2. WebResearchReportTool: Conducts autonomous web research on topic X, scrapes authoritative pages,
   synthesizes insights with formal citations, and compiles an executive PDF report with sources.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from tools.base import BaseTool, ToolResult
from creator.report_builder import extract_clean_page, research_and_build_report

logger = logging.getLogger(__name__)


class WebScrapeTool(BaseTool):
    """Tool for fetching and extracting clean text and tables from any webpage."""

    name: str = "scrape_webpage"
    description: str = (
        "Fetches a webpage URL and extracts clean, readable article text, headings, "
        "and structured data tables without scripts, navigation bars, or advertisements."
    )

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The HTTP or HTTPS URL of the webpage to scrape."
                    }
                },
                "required": ["url"]
            }
        }

    def run(self, url: str = "", **kwargs: Any) -> ToolResult:
        if not url or not str(url).strip():
            return ToolResult(
                success=False,
                data=None,
                message="Parameter 'url' is required to scrape a webpage."
            )

        clean_url = str(url).strip()
        if not clean_url.startswith("http://") and not clean_url.startswith("https://"):
            clean_url = "https://" + clean_url

        try:
            data = extract_clean_page(clean_url)
            if data.get("status") == "success" and data.get("text"):
                tables_count = len(data.get("tables", []))
                msg = (
                    f"Successfully scraped '{data.get('title', clean_url)}'. "
                    f"Extracted {len(data['text'])} characters of text and {tables_count} data tables."
                )
                return ToolResult(success=True, data=data, message=msg)
            else:
                return ToolResult(
                    success=False,
                    data=None,
                    message=f"Could not retrieve readable text from '{clean_url}'."
                )
        except Exception as exc:
            logger.exception("WebScrapeTool failed: %s", exc)
            return ToolResult(
                success=False,
                data=None,
                message=f"Failed to scrape webpage: {exc}"
            )


class WebResearchReportTool(BaseTool):
    """Tool for researching a topic on the live web and compiling an executive PDF with citations."""

    name: str = "research_and_report"
    description: str = (
        "Researches any topic on the live web, scrapes authoritative sources, summarizes key findings, "
        "attributes citations ([1], [2]...), and compiles a publication-ready PDF or Word report with sources."
    )

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Topic or query to research (e.g. 'Quantum Computing in 2026', 'AI Healthcare Trends')."
                    },
                    "format": {
                        "type": "string",
                        "enum": ["pdf", "docx", "both"],
                        "description": "Target report document format ('pdf', 'docx', or 'both'; default: 'pdf')."
                    },
                    "max_sources": {
                        "type": "integer",
                        "description": "Number of web sources to scrape and cite (default: 5)."
                    },
                    "auto_open": {
                        "type": "boolean",
                        "description": "Whether to automatically open the generated report in Windows (default: True)."
                    }
                },
                "required": ["topic"]
            }
        }

    def run(
        self,
        topic: str = "",
        format: str = "pdf",
        max_sources: int = 5,
        auto_open: bool = True,
        **kwargs: Any
    ) -> ToolResult:
        if not topic or not str(topic).strip():
            return ToolResult(
                success=False,
                data=None,
                message="Parameter 'topic' is required to conduct web research."
            )

        try:
            res = research_and_build_report(
                topic=str(topic).strip(),
                format=format,
                max_sources=max_sources,
                auto_open=auto_open
            )
            return ToolResult(
                success=res.get("success", False),
                data=res,
                message=res.get("message", "Web research report compiled successfully.")
            )
        except Exception as exc:
            logger.exception("WebResearchReportTool failed: %s", exc)
            return ToolResult(
                success=False,
                data=None,
                message=f"Failed to compile research report: {exc}"
            )
