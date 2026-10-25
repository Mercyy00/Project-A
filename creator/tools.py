"""Document generation tools for JARVIS ReAct Brain and Central Registry.

Author: Document Engineer
Module: creator.tools

Exposes CreatePdfTool, CreateDocxTool, and CreatePptxTool conforming strictly
to BaseTool and ARCHITECTURE.md interfaces. Automatically registers all tools
in TOOL_REGISTRY to prevent fallback to write_file (raw markdown corruption).
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from tools.base import BaseTool, ToolResult
from creator.chart_maker import generate_chart
from creator.docx_maker import make_docx
from creator.pdf_maker import make_pdf
from creator.pptx_maker import make_pptx
from creator.report_maker import generate_executive_report
from creator.web_maker import make_website
from creator.document_reader import (
    read_document as reader_read_document,
    inspect_document as reader_inspect_document,
    extract_tables as reader_extract_tables,
    summarize_document as reader_summarize_document,
)

logger = logging.getLogger(__name__)


def _normalize_out_dir(out_dir: Optional[str]) -> str:
    """Normalize output directory so 'desktop', 'Desktop', or '~/Desktop' maps to user desktop."""
    if not out_dir or not str(out_dir).strip():
        return "workspace"
    clean = str(out_dir).strip()
    norm_lower = clean.replace("\\", "/").lower()
    if norm_lower == "desktop" or norm_lower.startswith("desktop/") or "desktop" in norm_lower:
        return str(Path.home() / "Desktop")
    if norm_lower == "documents" or "documents" in norm_lower:
        return str(Path.home() / "Documents")
    if norm_lower == "downloads" or "downloads" in norm_lower:
        return str(Path.home() / "Downloads")
    return clean


def _normalize_single_section(item: Any, default_idx: int = 1) -> Dict[str, Any]:
    """Ensure a single section dictionary conforms strictly to expected schema."""
    if not isinstance(item, dict):
        return {"heading": f"Section {default_idx}", "text": str(item)}

    heading = (
        item.get("heading")
        or item.get("title")
        or item.get("header")
        or item.get("name")
        or item.get("section")
        or f"Section {default_idx}"
    )
    text = (
        item.get("text")
        or item.get("content")
        or item.get("body")
        or item.get("summary")
        or item.get("description")
        or ""
    )

    bullets = item.get("bullets") or item.get("points") or item.get("items")
    norm_bullets: List[str] = []
    if isinstance(bullets, str):
        norm_bullets = [b.strip("-*• 0123456789.") for b in bullets.splitlines() if b.strip()]
    elif isinstance(bullets, (list, tuple)):
        for b in bullets:
            if isinstance(b, dict):
                norm_bullets.append(str(b.get("text", b.get("point", b.get("value", str(b))))))
            else:
                norm_bullets.append(str(b))

    metrics = item.get("metrics") or item.get("bento_cards")
    norm_metrics: List[Dict[str, str]] = []
    if isinstance(metrics, dict):
        norm_metrics = [{"label": str(metrics.get("label", "Metric")), "value": str(metrics.get("value", ""))}]
    elif isinstance(metrics, (list, tuple)):
        for m in metrics:
            if isinstance(m, dict):
                norm_metrics.append({
                    "label": str(m.get("label", m.get("title", m.get("key", "Metric")))),
                    "value": str(m.get("value", m.get("val", ""))),
                })
            else:
                norm_metrics.append({"label": "Metric", "value": str(m)})

    table = item.get("table") or item.get("data")
    norm_table: Optional[List[List[str]]] = None
    if isinstance(table, (list, tuple)) and len(table) > 0:
        norm_table = []
        for row in table:
            if isinstance(row, (list, tuple)):
                norm_table.append([str(c) for c in row])
            elif isinstance(row, dict):
                norm_table.append([str(v) for v in row.values()])
            else:
                norm_table.append([str(row)])

    sec_out: Dict[str, Any] = {
        "heading": str(heading),
        "text": str(text),
    }
    if norm_bullets:
        sec_out["bullets"] = norm_bullets
    if norm_metrics:
        sec_out["metrics"] = norm_metrics
    if norm_table:
        sec_out["table"] = norm_table
    if item.get("page_break_after"):
        sec_out["page_break_after"] = True

    return sec_out


def _normalize_sections(sections: Union[str, List[Dict[str, Any]], Dict[str, Any], None]) -> List[Dict[str, Any]]:
    """Ensure sections input is safely parsed into a list of section dictionaries."""
    if sections is None:
        return [{"heading": "Overview", "text": "Generated document."}]

    if isinstance(sections, str):
        cleaned = sections.strip()
        try:
            parsed = json.loads(cleaned)
            return _normalize_sections(parsed)
        except Exception:
            # Fall back to splitting markdown headers if present
            if "\n#" in cleaned or cleaned.startswith("#"):
                md_sections = []
                cur_heading = "Overview"
                cur_lines = []
                for line in cleaned.splitlines():
                    if line.startswith("#"):
                        if cur_lines or cur_heading != "Overview":
                            md_sections.append({"heading": cur_heading, "text": "\n".join(cur_lines).strip()})
                            cur_lines = []
                        cur_heading = line.lstrip("#").strip()
                    else:
                        cur_lines.append(line)
                if cur_lines:
                    md_sections.append({"heading": cur_heading, "text": "\n".join(cur_lines).strip()})
                if md_sections:
                    return [_normalize_single_section(s, idx + 1) for idx, s in enumerate(md_sections)]

            return [{"heading": "Overview", "text": cleaned}]

    if isinstance(sections, dict):
        if "sections" in sections and isinstance(sections["sections"], (list, dict)):
            return _normalize_sections(sections["sections"])
        return [_normalize_single_section(sections, 1)]

    if isinstance(sections, (list, tuple)):
        normalized: List[Dict[str, Any]] = []
        for idx, item in enumerate(sections):
            normalized.append(_normalize_single_section(item, idx + 1))
        return normalized if normalized else [{"heading": "Overview", "text": "No content provided."}]

    return [{"heading": "Overview", "text": str(sections)}]


class CreatePdfTool(BaseTool):
    """Tool that generates publication-grade, themed PDF documents with ReportLab Platypus."""

    name: str = "create_pdf"
    description: str = (
        "Creates a professionally styled, publication-ready binary PDF document with an executive "
        "cover page, bento-grid metric callouts, section headings, paragraphs, bullet lists, and tables. "
        "Arguments: title (str), sections (list of dicts with 'heading', 'text', 'bullets', 'metrics', 'table'), "
        "theme (optional: 'clean_light', 'dark_pro', 'colourful'), auto_open (optional bool, default True)."
    )

    def run(
        self,
        title: str,
        sections: Any,
        theme: str = "clean_light",
        out_dir: str = "workspace",
        auto_open: bool = True,
        **kwargs: Any,
    ) -> ToolResult:
        """Executes PDF creation.

        Args:
            title: Title of the document.
            sections: List of section objects or JSON string.
            theme: Theme name ('clean_light', 'dark_pro', 'colourful').
            out_dir: Output directory (defaults to 'workspace').
            auto_open: Whether to automatically launch the document in Adobe Acrobat / default viewer.
            **kwargs: Extra arguments.

        Returns:
            ToolResult containing the generated file path and execution summary.
        """
        try:
            if not title or not str(title).strip():
                return ToolResult(
                    success=False,
                    data=None,
                    message="Document title cannot be empty.",
                )

            effective_dir = _normalize_out_dir(out_dir or kwargs.get("output_dir"))
            if "desktop" in str(title).lower() and effective_dir == "workspace":
                effective_dir = str(Path.home() / "Desktop")
            norm_sections = _normalize_sections(sections)
            pdf_path = make_pdf(
                title=str(title).strip(),
                sections=norm_sections,
                theme=theme,
                out_dir=effective_dir,
                auto_open=auto_open,
                author=kwargs.get("author"),
            )

            file_size = os.path.getsize(pdf_path) if os.path.exists(pdf_path) else 0

            return ToolResult(
                success=True,
                data={
                    "file_path": pdf_path,
                    "title": title,
                    "theme": theme,
                    "format": "pdf",
                    "bytes": file_size,
                    "auto_opened": auto_open,
                },
                message=f"PDF document '{title}' generated successfully ({file_size} bytes) at: {pdf_path}",
            )
        except Exception as exc:
            logger.exception("CreatePdfTool execution failed: %s", exc)
            return ToolResult(
                success=False,
                data=None,
                message=f"Failed to generate PDF document: {str(exc)}",
            )

    def get_schema(self) -> Dict[str, Any]:
        """Returns OpenAPI/Gemini schema definition for LLM tool calling."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "The title of the PDF document.",
                    },
                    "sections": {
                        "type": "array",
                        "description": "List of document sections with heading, text, bullets, metrics, or table.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "heading": {
                                    "type": "string",
                                    "description": "Section title.",
                                },
                                "text": {
                                    "type": "string",
                                    "description": "Body paragraph narrative for this section.",
                                },
                                "bullets": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Bullet points for this section.",
                                },
                                "metrics": {
                                    "type": "array",
                                    "description": "Key metric cards for Bento Grid (e.g. [{'label': 'Uptime', 'value': '99.9%'}]).",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "label": {"type": "string"},
                                            "value": {"type": "string"},
                                        },
                                        "required": ["label", "value"],
                                    },
                                },
                                "table": {
                                    "type": "array",
                                    "description": "2D array of rows for a data table (first row is header).",
                                    "items": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                    },
                                },
                            },
                            "required": ["heading"],
                        },
                    },
                    "theme": {
                        "type": "string",
                        "description": "Theme style: 'clean_light' (default), 'dark_pro', or 'colourful'.",
                        "enum": ["clean_light", "dark_pro", "colourful"],
                    },
                    "out_dir": {
                        "type": "string",
                        "description": "Target output directory. Use 'Desktop' to save directly to user's desktop, or 'workspace' (default).",
                    },
                    "auto_open": {
                        "type": "boolean",
                        "description": "Whether to automatically open the generated document in the desktop viewer (default: True).",
                    },
                },
                "required": ["title", "sections"],
            },
        }


class CreateDocxTool(BaseTool):
    """Tool that generates formatted Word (.docx) documents with python-docx."""

    name: str = "create_docx"
    description: str = (
        "Creates a formatted Word (.docx) document with executive cover page, bento metric callout "
        "cards, styled headings, paragraphs, bullet lists, and tables. "
        "Arguments: title (str), sections (list of dicts with 'heading', 'text', 'bullets', 'metrics', 'table'), "
        "theme (optional: 'clean_light', 'dark_pro', 'colourful'), auto_open (optional bool, default True)."
    )

    def run(
        self,
        title: str,
        sections: Any,
        theme: str = "clean_light",
        out_dir: str = "workspace",
        auto_open: bool = True,
        **kwargs: Any,
    ) -> ToolResult:
        """Executes Word document creation.

        Args:
            title: Title of the document.
            sections: List of section objects or JSON string.
            theme: Theme name ('clean_light', 'dark_pro', 'colourful').
            out_dir: Output directory (defaults to 'workspace').
            auto_open: Whether to automatically launch the document in Microsoft Word.
            **kwargs: Extra arguments.

        Returns:
            ToolResult containing the generated file path and execution summary.
        """
        try:
            if not title or not str(title).strip():
                return ToolResult(
                    success=False,
                    data=None,
                    message="Document title cannot be empty.",
                )

            effective_dir = _normalize_out_dir(out_dir or kwargs.get("output_dir"))
            if "desktop" in str(title).lower() and effective_dir == "workspace":
                effective_dir = str(Path.home() / "Desktop")
            norm_sections = _normalize_sections(sections)
            docx_path = make_docx(
                title=str(title).strip(),
                sections=norm_sections,
                theme=theme,
                out_dir=effective_dir,
                auto_open=auto_open,
                author=kwargs.get("author"),
            )

            file_size = os.path.getsize(docx_path) if os.path.exists(docx_path) else 0

            return ToolResult(
                success=True,
                data={
                    "file_path": docx_path,
                    "title": title,
                    "theme": theme,
                    "format": "docx",
                    "bytes": file_size,
                    "auto_opened": auto_open,
                },
                message=f"Word document '{title}' generated successfully ({file_size} bytes) at: {docx_path}",
            )
        except Exception as exc:
            logger.exception("CreateDocxTool execution failed: %s", exc)
            return ToolResult(
                success=False,
                data=None,
                message=f"Failed to generate Word document: {str(exc)}",
            )

    def get_schema(self) -> Dict[str, Any]:
        """Returns OpenAPI/Gemini schema definition for LLM tool calling."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "The title of the Word document.",
                    },
                    "sections": {
                        "type": "array",
                        "description": "List of document sections with heading, text, bullets, metrics, or table.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "heading": {
                                    "type": "string",
                                    "description": "Section title.",
                                },
                                "text": {
                                    "type": "string",
                                    "description": "Body paragraph narrative for this section.",
                                },
                                "bullets": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Bullet points for this section.",
                                },
                                "metrics": {
                                    "type": "array",
                                    "description": "Key metric cards for Bento Grid (e.g. [{'label': 'Uptime', 'value': '99.9%'}]).",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "label": {"type": "string"},
                                            "value": {"type": "string"},
                                        },
                                        "required": ["label", "value"],
                                    },
                                },
                                "table": {
                                    "type": "array",
                                    "description": "2D array of rows for a data table (first row is header).",
                                    "items": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                    },
                                },
                            },
                            "required": ["heading"],
                        },
                    },
                    "theme": {
                        "type": "string",
                        "description": "Theme style: 'clean_light' (default), 'dark_pro', or 'colourful'.",
                        "enum": ["clean_light", "dark_pro", "colourful"],
                    },
                    "out_dir": {
                        "type": "string",
                        "description": "Target output directory. Use 'Desktop' to save directly to user's desktop, or 'workspace' (default).",
                    },
                    "auto_open": {
                        "type": "boolean",
                        "description": "Whether to automatically open the generated document in Microsoft Word (default: True).",
                    },
                },
                "required": ["title", "sections"],
            },
        }


class CreatePptxTool(BaseTool):
    """Tool that generates widescreen 16:9 presentation slide decks with python-pptx."""

    name: str = "create_pptx"
    description: str = (
        "Creates a 16:9 widescreen PowerPoint presentation deck (.pptx) with title slide, section "
        "slides (max 6 bullets per slide, split automatically), bento metric card slides, tables, and thank you slide. "
        "Arguments: title (str), sections (list of dicts with 'heading', 'text', 'bullets', 'metrics', 'table'), "
        "theme (optional: 'clean_light', 'dark_pro', 'colourful'), auto_open (optional bool, default True)."
    )

    def run(
        self,
        title: str,
        sections: Any,
        theme: str = "clean_light",
        out_dir: str = "workspace",
        auto_open: bool = True,
        **kwargs: Any,
    ) -> ToolResult:
        """Executes presentation deck creation.

        Args:
            title: Presentation title.
            sections: List of section objects or JSON string.
            theme: Theme name ('clean_light', 'dark_pro', 'colourful').
            out_dir: Output directory (defaults to 'workspace').
            auto_open: Whether to automatically launch the document in PowerPoint.
            **kwargs: Extra arguments.

        Returns:
            ToolResult containing the generated file path and execution summary.
        """
        try:
            if not title or not str(title).strip():
                return ToolResult(
                    success=False,
                    data=None,
                    message="Presentation title cannot be empty.",
                )

            effective_dir = _normalize_out_dir(out_dir or kwargs.get("output_dir"))
            if "desktop" in str(title).lower() and effective_dir == "workspace":
                effective_dir = str(Path.home() / "Desktop")
            norm_sections = _normalize_sections(sections)
            pptx_path = make_pptx(
                title=str(title).strip(),
                sections=norm_sections,
                theme=theme,
                out_dir=effective_dir,
                auto_open=auto_open,
                author=kwargs.get("author"),
            )

            file_size = os.path.getsize(pptx_path) if os.path.exists(pptx_path) else 0

            return ToolResult(
                success=True,
                data={
                    "file_path": pptx_path,
                    "title": title,
                    "theme": theme,
                    "format": "pptx",
                    "bytes": file_size,
                    "auto_opened": auto_open,
                },
                message=f"PowerPoint deck '{title}' generated successfully ({file_size} bytes) at: {pptx_path}",
            )
        except Exception as exc:
            logger.exception("CreatePptxTool execution failed: %s", exc)
            return ToolResult(
                success=False,
                data=None,
                message=f"Failed to generate PowerPoint deck: {str(exc)}",
            )

    def get_schema(self) -> Dict[str, Any]:
        """Returns OpenAPI/Gemini schema definition for LLM tool calling."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "The title of the PowerPoint presentation deck.",
                    },
                    "sections": {
                        "type": "array",
                        "description": "List of slide sections with heading, text, bullets, metrics, or table.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "heading": {
                                    "type": "string",
                                    "description": "Slide section title.",
                                },
                                "text": {
                                    "type": "string",
                                    "description": "Introductory narrative on the slide.",
                                },
                                "bullets": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Slide bullet points (max 6 per slide; longer lists split automatically).",
                                },
                                "metrics": {
                                    "type": "array",
                                    "description": "Key metric cards for Bento Grid slide (e.g. [{'label': 'Speed', 'value': '< 300ms'}]).",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "label": {"type": "string"},
                                            "value": {"type": "string"},
                                        },
                                        "required": ["label", "value"],
                                    },
                                },
                                "table": {
                                    "type": "array",
                                    "description": "2D table to render on a dedicated data slide.",
                                    "items": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                    },
                                },
                            },
                            "required": ["heading"],
                        },
                    },
                    "theme": {
                        "type": "string",
                        "description": "Theme style: 'clean_light' (default), 'dark_pro', or 'colourful'.",
                        "enum": ["clean_light", "dark_pro", "colourful"],
                    },
                    "out_dir": {
                        "type": "string",
                        "description": "Target output directory. Use 'Desktop' to save directly to user's desktop, or 'workspace' (default).",
                    },
                    "auto_open": {
                        "type": "boolean",
                        "description": "Whether to automatically open the generated deck in PowerPoint (default: True).",
                    },
                },
                "required": ["title", "sections"],
            },
        }


class CreateChartTool(BaseTool):
    """Tool for creating themed high-resolution charts (bar, line, pie, donut, horizontal_bar)."""

    name = "create_chart"
    description = (
        "Generates a themed high-resolution chart (bar, line, pie, donut, horizontal_bar) "
        "matching JARVIS themes ('clean_light', 'dark_pro', 'colourful'). Saves as PNG image."
    )

    def run(
        self,
        chart_type: str = "bar",
        data: Optional[Any] = None,
        title: str = "Analytics Chart",
        theme: str = "clean_light",
        out_dir: str = "workspace",
        filename: Optional[str] = None,
        **kwargs: Any,
    ) -> ToolResult:
        """Execute chart creation tool."""
        try:
            if not title or not isinstance(title, str) or not title.strip():
                return ToolResult(
                    success=False,
                    data=None,
                    message="Chart generation requires a non-empty title string.",
                )

            chart_data = data or {"Metric A": 20, "Metric B": 35, "Metric C": 45}
            if isinstance(chart_data, str):
                try:
                    chart_data = json.loads(chart_data)
                except Exception:
                    chart_data = {"Value": 10}

            path = generate_chart(
                chart_type=chart_type,
                data=chart_data,
                title=title,
                theme=theme,
                out_dir=out_dir,
                filename=filename,
            )

            file_size = os.path.getsize(path) if os.path.exists(path) else 0

            return ToolResult(
                success=True,
                data={
                    "file_path": path,
                    "chart_type": chart_type,
                    "theme": theme,
                    "bytes": file_size,
                },
                message=f"Chart '{title}' successfully generated at {path} ({file_size} bytes).",
            )
        except Exception as e:
            logger.error("Failed to generate chart: %s", e, exc_info=True)
            return ToolResult(
                success=False,
                data=None,
                message=f"Chart generation failed: {str(e)}",
            )

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "chart_type": {
                        "type": "string",
                        "description": "Chart type: 'bar', 'line', 'pie', 'donut', or 'horizontal_bar'.",
                        "enum": ["bar", "line", "pie", "donut", "horizontal_bar"],
                    },
                    "data": {
                        "type": "object",
                        "description": "Data mapping categories to values, e.g. {'Q1': 100, 'Q2': 250}.",
                    },
                    "title": {
                        "type": "string",
                        "description": "Chart title.",
                    },
                    "theme": {
                        "type": "string",
                        "description": "Theme style: 'clean_light', 'dark_pro', or 'colourful'.",
                        "enum": ["clean_light", "dark_pro", "colourful"],
                    },
                    "filename": {
                        "type": "string",
                        "description": "Optional output PNG filename.",
                    },
                },
                "required": ["title", "data"],
            },
        }


class GenerateReportTool(BaseTool):
    """Tool for generating autonomous multi-format executive intelligence reports (PDF, Word, PPTX)."""

    name = "generate_report"
    description = (
        "Generates a synchronized executive intelligence report package across PDF, Word (DOCX), "
        "and PowerPoint (PPTX) with embedded charts, Bento KPI cards, and modern tables."
    )

    def run(
        self,
        title: str,
        summary: str = "",
        sections: Optional[Any] = None,
        key_metrics: Optional[Any] = None,
        chart_configs: Optional[Any] = None,
        theme: str = "clean_light",
        formats: Optional[Any] = None,
        out_dir: str = "workspace",
        auto_open: bool = False,
        **kwargs: Any,
    ) -> ToolResult:
        """Execute autonomous executive report generator."""
        try:
            if not title or not isinstance(title, str) or not title.strip():
                return ToolResult(
                    success=False,
                    data=None,
                    message="Report generation requires a non-empty title string.",
                )

            norm_sections = _normalize_sections(sections) if sections else []

            norm_metrics = key_metrics
            if isinstance(norm_metrics, str):
                try:
                    norm_metrics = json.loads(norm_metrics)
                except Exception:
                    norm_metrics = []

            norm_charts = chart_configs
            if isinstance(norm_charts, str):
                try:
                    norm_charts = json.loads(norm_charts)
                except Exception:
                    norm_charts = []

            norm_formats = formats
            if isinstance(norm_formats, str):
                try:
                    norm_formats = json.loads(norm_formats)
                except Exception:
                    norm_formats = [f.strip() for f in norm_formats.split(",") if f.strip()]

            output_map = generate_executive_report(
                title=title,
                summary=summary or "Autonomous executive report.",
                sections=norm_sections,
                key_metrics=norm_metrics,
                chart_configs=norm_charts,
                theme=theme,
                formats=norm_formats,
                out_dir=out_dir,
                auto_open=auto_open,
                author=kwargs.get("author"),
            )

            total_bytes = sum(os.path.getsize(p) for p in output_map.values() if os.path.exists(p))

            return ToolResult(
                success=True,
                data={
                    "files": output_map,
                    "formats": list(output_map.keys()),
                    "theme": theme,
                    "total_bytes": total_bytes,
                },
                message=f"Executive report '{title}' generated successfully in {len(output_map)} formats: {list(output_map.keys())}.",
            )
        except Exception as e:
            logger.error("Failed to generate report: %s", e, exc_info=True)
            return ToolResult(
                success=False,
                data=None,
                message=f"Report generation failed: {str(e)}",
            )

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Executive report title.",
                    },
                    "summary": {
                        "type": "string",
                        "description": "High-level executive summary narrative.",
                    },
                    "sections": {
                        "type": "array",
                        "description": "List of report sections with heading, text, bullets, and table data.",
                        "items": {"type": "object"},
                    },
                    "key_metrics": {
                        "type": "array",
                        "description": "Key KPI metrics for Bento grid cards (label, value).",
                        "items": {"type": "object"},
                    },
                    "chart_configs": {
                        "type": "array",
                        "description": "Chart configurations (type, title, data) to render and embed.",
                        "items": {"type": "object"},
                    },
                    "theme": {
                        "type": "string",
                        "description": "Theme style: 'clean_light', 'dark_pro', or 'colourful'.",
                        "enum": ["clean_light", "dark_pro", "colourful"],
                    },
                    "formats": {
                        "type": "array",
                        "description": "Target formats list: ['pdf', 'docx', 'pptx'].",
                        "items": {"type": "string"},
                    },
                    "auto_open": {
                        "type": "boolean",
                        "description": "Whether to auto-open the generated report.",
                    },
                },
                "required": ["title"],
            },
        }


# Convenience function wrappers
def create_pdf(title: str, sections: Any, theme: str = "clean_light", auto_open: bool = True, **kwargs: Any) -> ToolResult:
    """Convenience callable for CreatePdfTool."""
    return CreatePdfTool().run(title=title, sections=sections, theme=theme, auto_open=auto_open, **kwargs)


def create_docx(title: str, sections: Any, theme: str = "clean_light", auto_open: bool = True, **kwargs: Any) -> ToolResult:
    """Convenience callable for CreateDocxTool."""
    return CreateDocxTool().run(title=title, sections=sections, theme=theme, auto_open=auto_open, **kwargs)


def create_pptx(title: str, sections: Any, theme: str = "clean_light", auto_open: bool = True, **kwargs: Any) -> ToolResult:
    """Convenience callable for CreatePptxTool."""
    return CreatePptxTool().run(title=title, sections=sections, theme=theme, auto_open=auto_open, **kwargs)


def create_chart(chart_type: str = "bar", data: Any = None, title: str = "Analytics Chart", theme: str = "clean_light", **kwargs: Any) -> ToolResult:
    """Convenience callable for CreateChartTool."""
    return CreateChartTool().run(chart_type=chart_type, data=data, title=title, theme=theme, **kwargs)


def generate_report(title: str, summary: str = "", sections: Any = None, key_metrics: Any = None, chart_configs: Any = None, theme: str = "clean_light", **kwargs: Any) -> ToolResult:
    """Convenience callable for GenerateReportTool."""
    return GenerateReportTool().run(title=title, summary=summary, sections=sections, key_metrics=key_metrics, chart_configs=chart_configs, theme=theme, **kwargs)


class CreateDocumentTool(BaseTool):
    """Tool that autonomously designs and generates a full document or slide deck from a topic prompt."""

    name: str = "create_document"
    description: str = (
        "Generates a complete, professionally formatted PDF, Word document, PowerPoint slide deck, or HTML website "
        "from a single topic prompt. Formats 4-6 sections with headings, summaries, and bullet points. "
        "Supports English, Hindi, and Marathi in native Devanagari script. "
        "Arguments: topic (str, required), kind (optional: 'pdf', 'docx', 'pptx', 'web'), "
        "language (optional: 'en', 'hi', 'mr'), theme (optional: 'clean_light', 'dark_pro', 'colourful', 'tech_innovation'), "
        "auto_open (optional bool, default True)."
    )

    def run(
        self,
        topic: str,
        kind: str = "pdf",
        language: str = "en",
        theme: str = "clean_light",
        out_dir: str = "workspace",
        auto_open: bool = True,
        **kwargs: Any,
    ) -> ToolResult:
        """Execute document outline generation and binary rendering."""
        clean_topic = (topic or "").strip()
        if not clean_topic:
            return ToolResult(success=False, message="Document topic cannot be empty.")

        try:
            from creator.outline import create_document as make_full_document
            file_path = make_full_document(
                topic=clean_topic,
                kind=kind,
                theme=theme,
                language=language,
                out_dir=out_dir,
                auto_open=auto_open,
                author=kwargs.get("author"),
            )
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            fmt = Path(file_path).suffix.lstrip(".").lower()

            return ToolResult(
                success=True,
                message=f"Document '{clean_topic}' successfully created at: {file_path} ({file_size} bytes)",
                data={
                    "file_path": file_path,
                    "format": fmt,
                    "bytes": file_size,
                    "topic": clean_topic,
                    "language": language,
                    "theme": theme,
                },
            )
        except Exception as exc:
            logger.error("CreateDocumentTool execution failed: %s", exc, exc_info=True)
            return ToolResult(success=False, message=f"Failed to create document: {exc}")

    def get_schema(self) -> Dict[str, Any]:
        """Return OpenAPI / Gemini function calling schema for CreateDocumentTool."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Topic or theme of the document (e.g. 'Solar Energy', 'AI in Education', 'प्रकल्प नियोजन').",
                    },
                    "kind": {
                        "type": "string",
                        "description": "Document format to generate: 'pdf' (default), 'docx' (Word), 'pptx' (PowerPoint), or 'web' (HTML website).",
                        "enum": ["pdf", "docx", "pptx", "web"],
                    },
                    "language": {
                        "type": "string",
                        "description": "Content language: 'en' (English), 'hi' (Hindi), or 'mr' (Marathi). Default is 'en'.",
                        "enum": ["en", "hi", "mr"],
                    },
                    "theme": {
                        "type": "string",
                        "description": "Styling theme: 'clean_light' (default), 'dark_pro', or 'colourful'.",
                        "enum": ["clean_light", "dark_pro", "colourful"],
                    },
                    "auto_open": {
                        "type": "boolean",
                        "description": "Whether to automatically open the document upon creation (default: True).",
                    },
                },
                "required": ["topic"],
            },
        }


def create_document_tool(
    topic: str,
    kind: str = "pdf",
    language: str = "en",
    theme: str = "clean_light",
    auto_open: bool = True,
    **kwargs: Any,
) -> ToolResult:
    """Convenience callable for CreateDocumentTool."""
    return CreateDocumentTool().run(
        topic=topic, kind=kind, language=language, theme=theme, auto_open=auto_open, **kwargs
    )


class CreateWebsiteTool(BaseTool):
    """Tool that generates publication-grade, responsive website artifacts with Claude-level frontend design."""

    name: str = "create_website"
    description: str = (
        "Creates a responsive, beautifully styled, single-file HTML website or web dashboard artifact "
        "using Claude-quality design principles, custom color themes, bento metric grids, "
        "interactive data tables, and modern typography. "
        "Arguments: title (str), sections (list of dicts with 'heading', 'text', 'bullets', 'metrics', 'table'), "
        "theme (optional: 'clean_light', 'dark_pro', 'colourful', 'tech_innovation', 'ocean_depths', 'forest_moss', "
        "'midnight_executive', 'warm_terracotta', 'modern_minimalist', 'sunset_boulevard'), "
        "auto_open (optional bool, default True)."
    )

    def run(
        self,
        title: str,
        sections: Any,
        theme: str = "clean_light",
        out_dir: str = "workspace",
        auto_open: bool = True,
        filename: Optional[str] = None,
        hero_tagline: Optional[str] = None,
        language: str = "en",
        **kwargs: Any,
    ) -> ToolResult:
        """Executes website / web artifact creation."""
        clean_title = (title or "Website Artifact").strip()
        if not clean_title:
            return ToolResult(success=False, data=None, message="Title cannot be empty.")

        try:
            norm_sections = _normalize_sections(sections)
            out_file = make_website(
                title=clean_title,
                sections=norm_sections,
                theme=theme,
                out_dir=out_dir,
                auto_open=auto_open,
                author=kwargs.get("author"),
                filename=filename,
                hero_tagline=hero_tagline,
                language=language,
            )
            file_size = os.path.getsize(out_file) if os.path.exists(out_file) else 0

            return ToolResult(
                success=True,
                data={
                    "file_path": out_file,
                    "format": "html",
                    "bytes": file_size,
                    "title": clean_title,
                    "theme": theme,
                    "section_count": len(norm_sections),
                },
                message=f"Website artifact '{clean_title}' successfully generated at: {out_file} ({file_size} bytes)",
            )
        except Exception as exc:
            logger.error("CreateWebsiteTool execution failed: %s", exc, exc_info=True)
            return ToolResult(success=False, data=None, message=f"Failed to generate website artifact: {exc}")

    def get_schema(self) -> Dict[str, Any]:
        """Return OpenAPI / Gemini function calling schema for CreateWebsiteTool."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Website / Artifact title for hero section and navigation header.",
                    },
                    "sections": {
                        "type": "array",
                        "description": "List of structured sections containing headings, paragraphs, bullet points, metrics, and tables.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "heading": {
                                    "type": "string",
                                    "description": "Section heading.",
                                },
                                "text": {
                                    "type": "string",
                                    "description": "Body paragraph or summary text.",
                                },
                                "bullets": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Bullet points for key highlights.",
                                },
                                "metrics": {
                                    "type": "array",
                                    "description": "Key metric cards for Bento grid layout.",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "label": {"type": "string"},
                                            "value": {"type": "string"},
                                            "subtext": {"type": "string"},
                                        },
                                        "required": ["label", "value"],
                                    },
                                },
                                "table": {
                                    "type": "array",
                                    "description": "2D table array where the first inner array represents the column headers.",
                                    "items": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                    },
                                },
                            },
                            "required": ["heading"],
                        },
                    },
                    "theme": {
                        "type": "string",
                        "description": "Color theme: 'clean_light', 'dark_pro', 'colourful', 'tech_innovation', 'ocean_depths', 'forest_moss', 'midnight_executive', 'warm_terracotta', 'modern_minimalist', 'sunset_boulevard'.",
                    },
                    "out_dir": {
                        "type": "string",
                        "description": "Target output directory. Use 'Desktop' to save directly to user's desktop, or 'workspace' (default).",
                    },
                    "auto_open": {
                        "type": "boolean",
                        "description": "Whether to automatically launch the generated website in the default browser (default: True).",
                    },
                },
                "required": ["title", "sections"],
            },
        }


def create_website(title: str, sections: Any, theme: str = "clean_light", auto_open: bool = True, **kwargs: Any) -> ToolResult:
    """Convenience callable for CreateWebsiteTool."""
    return CreateWebsiteTool().run(title=title, sections=sections, theme=theme, auto_open=auto_open, **kwargs)


class CreateTemplateTool(BaseTool):
    """Tool that generates formatted documents from standard professional templates."""

    name: str = "create_template_document"
    description: str = (
        "Generates a complete document from pre-configured professional templates. "
        "Templates: 'project_report' (academic/technical report with chapters), "
        "'assignment_cover' (student submission cover sheet with declaration), "
        "'resume' (curriculum vitae with skills, experience, education), or "
        "'application_letter' (formal cover/application letter). "
        "Arguments: template_type (str, required: 'project_report', 'assignment_cover', 'resume', 'application_letter'), "
        "data (dict, required), theme (optional: 'clean_light', 'dark_pro', 'colourful'), "
        "kind (optional: 'pdf' or 'docx'), auto_open (optional bool, default False)."
    )

    def run(
        self,
        template_type: str,
        data: Dict[str, Any],
        theme: str = "clean_light",
        kind: str = "pdf",
        out_dir: str = "workspace",
        auto_open: bool = False,
        **kwargs: Any,
    ) -> ToolResult:
        """Execute template document generation."""
        ttype = (template_type or "").strip().lower()
        if not ttype:
            return ToolResult(success=False, message="template_type cannot be empty.")

        effective_dir = _normalize_out_dir(out_dir or kwargs.get("output_dir"))
        title_hint = str(data.get("title", "")) if isinstance(data, dict) else ""
        if "desktop" in title_hint.lower() and effective_dir == "workspace":
            effective_dir = str(Path.home() / "Desktop")

        try:
            import creator.templates as tpls

            if ttype in ("project_report", "report"):
                title = data.get("title", "Technical Project Report")
                author = data.get("author", "Lead Engineer")
                chapters = data.get("chapters", [])
                file_path = tpls.project_report(
                    title=title,
                    author=author,
                    chapters=chapters,
                    theme=theme,
                    out_dir=effective_dir,
                    kind=kind,
                    auto_open=auto_open,
                )
            elif ttype in ("assignment_cover", "assignment"):
                subject = data.get("subject", "Engineering Course")
                name = data.get("name", "Student")
                roll_no = data.get("roll_no", "001")
                title = data.get("title", "Assignment Submission")
                file_path = tpls.assignment_cover(
                    subject=subject,
                    name=name,
                    roll_no=roll_no,
                    title=title,
                    theme=theme,
                    out_dir=effective_dir,
                    kind=kind,
                    auto_open=auto_open,
                )
            elif ttype in ("resume", "cv"):
                file_path = tpls.resume(
                    data=data,
                    theme=theme,
                    out_dir=effective_dir,
                    kind=kind,
                    auto_open=auto_open,
                )
            elif ttype in ("application_letter", "cover_letter", "letter"):
                file_path = tpls.application_letter(
                    data=data,
                    theme=theme,
                    out_dir=effective_dir,
                    kind=kind,
                    auto_open=auto_open,
                )
            else:
                return ToolResult(
                    success=False,
                    message=f"Unknown template_type '{template_type}'. Supported: 'project_report', 'assignment_cover', 'resume', 'application_letter'.",
                )

            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            return ToolResult(
                success=True,
                message=f"Template document '{ttype}' successfully created at: {file_path} ({file_size} bytes)",
                data={
                    "file_path": file_path,
                    "template_type": ttype,
                    "format": Path(file_path).suffix.lstrip(".").lower(),
                    "bytes": file_size,
                    "theme": theme,
                },
            )
        except Exception as exc:
            logger.error("CreateTemplateTool execution failed: %s", exc, exc_info=True)
            return ToolResult(success=False, message=f"Failed to create template document: {exc}")

    def get_schema(self) -> Dict[str, Any]:
        """Return OpenAPI / Gemini function calling schema for CreateTemplateTool."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "template_type": {
                        "type": "string",
                        "description": "Template kind to build: 'project_report', 'assignment_cover', 'resume', or 'application_letter'.",
                        "enum": ["project_report", "assignment_cover", "resume", "application_letter"],
                    },
                    "data": {
                        "type": "object",
                        "description": "Content payload dictionary tailored for the chosen template.",
                    },
                    "theme": {
                        "type": "string",
                        "description": "Styling theme: 'clean_light', 'dark_pro', or 'colourful'.",
                        "enum": ["clean_light", "dark_pro", "colourful"],
                    },
                    "kind": {
                        "type": "string",
                        "description": "Output format: 'pdf' (default) or 'docx'.",
                        "enum": ["pdf", "docx"],
                    },
                    "out_dir": {
                        "type": "string",
                        "description": "Target output directory. Use 'Desktop' to save directly to user's desktop, or 'workspace' (default).",
                    },
                    "auto_open": {
                        "type": "boolean",
                        "description": "Whether to launch the document upon creation (default: False).",
                    },
                },
                "required": ["template_type", "data"],
            },
        }


def create_template_document(
    template_type: str,
    data: Dict[str, Any],
    theme: str = "clean_light",
    kind: str = "pdf",
    auto_open: bool = False,
    **kwargs: Any,
) -> ToolResult:
    """Convenience callable for CreateTemplateTool."""
    return CreateTemplateTool().run(
        template_type=template_type, data=data, theme=theme, kind=kind, auto_open=auto_open, **kwargs
    )




class ReadDocumentTool(BaseTool):
    """Tool to read, parse, and extract text, headings, tables and metadata from any document."""

    name: str = "read_document"
    description: str = (
        "Read, parse, and extract structured text, headings, tables, and metadata from any "
        "PDF, Word (.docx), PowerPoint (.pptx), HTML web artifact, or Markdown document."
    )

    def run(
        self,
        file_path: str,
        max_chars: int = 8000,
        page_range: Optional[List[int]] = None,
        **kwargs: Any,
    ) -> ToolResult:
        try:
            pages_tuple = (page_range[0], page_range[1]) if page_range and len(page_range) >= 2 else None
            data = reader_read_document(file_path=file_path, max_chars=max_chars, page_range=pages_tuple)
            return ToolResult(
                success=True,
                data=data,
                message=f"Successfully extracted {data['word_count']} words from {data['filename']} ({data['format'].upper()}).",
            )
        except Exception as exc:
            logger.error("Failed to read document '%s': %s", file_path, exc, exc_info=True)
            return ToolResult(
                success=False,
                error=str(exc),
                message=f"Failed to read document: {exc}",
            )

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "read_document",
                "description": "Read, parse, and extract structured text, headings, tables, and metadata from any PDF, Word (.docx), PowerPoint (.pptx), HTML web artifact, or Markdown document.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the document file to read.",
                        },
                        "max_chars": {
                            "type": "integer",
                            "description": "Maximum characters of text body to return (default: 8000).",
                        },
                        "page_range": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "Optional [start_page, end_page] for PDFs (e.g. [1, 3]).",
                        },
                    },
                    "required": ["file_path"],
                },
            },
        }


class SummarizeDocumentTool(BaseTool):
    """Tool to generate intelligent executive summaries and key takeaways from documents."""

    name: str = "summarize_document"
    description: str = (
        "Generate an intelligent executive summary, key takeaways, and metric highlights "
        "from an existing document (PDF, Word, PPTX, HTML)."
    )

    def run(
        self,
        file_path: str,
        focus: str = "general",
        max_bullets: int = 5,
        language: str = "en",
        **kwargs: Any,
    ) -> ToolResult:
        try:
            data = reader_summarize_document(
                file_path=file_path,
                focus=focus,
                max_bullets=max_bullets,
                language=language,
                cancel_event=kwargs.get("cancel_event"),
            )
            return ToolResult(
                success=True,
                data=data,
                message=f"Successfully generated executive summary for '{data['title']}' using {data['engine']} engine.",
            )
        except Exception as exc:
            logger.error("Failed to summarize document '%s': %s", file_path, exc, exc_info=True)
            return ToolResult(
                success=False,
                error=str(exc),
                message=f"Failed to summarize document: {exc}",
            )

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "summarize_document",
                "description": "Generate an intelligent executive summary, key takeaways, and metric highlights from an existing document (PDF, Word, PPTX, HTML).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the document to summarize.",
                        },
                        "focus": {
                            "type": "string",
                            "description": "Summary focus: 'general', 'technical', 'executive', or 'metrics'.",
                            "enum": ["general", "technical", "executive", "metrics"],
                        },
                        "max_bullets": {
                            "type": "integer",
                            "description": "Maximum key takeaways to extract (default: 5).",
                        },
                        "language": {
                            "type": "string",
                            "description": "Output language: 'en' (English), 'hi' (Hindi), or 'mr' (Marathi).",
                            "enum": ["en", "hi", "mr"],
                        },
                    },
                    "required": ["file_path"],
                },
            },
        }


class InspectDocumentTool(BaseTool):
    """Tool to inspect the structure and metadata of any document."""

    name: str = "inspect_document"
    description: str = (
        "Inspect the structure, page/slide count, headings tree, table count, and metadata "
        "of a document without loading the full text body."
    )

    def run(self, file_path: str, **kwargs: Any) -> ToolResult:
        try:
            data = reader_inspect_document(file_path=file_path)
            return ToolResult(
                success=True,
                data=data,
                message=f"Document '{data['filename']}' ({data['format'].upper()}): {data['page_or_slide_count']} pages/slides, {data['table_count']} tables, {data['word_count']} words.",
            )
        except Exception as exc:
            logger.error("Failed to inspect document '%s': %s", file_path, exc, exc_info=True)
            return ToolResult(
                success=False,
                error=str(exc),
                message=f"Failed to inspect document: {exc}",
            )

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "inspect_document",
                "description": "Inspect the structure, page/slide count, headings tree, table count, and metadata of a document without loading the full text body.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the document to inspect.",
                        },
                    },
                    "required": ["file_path"],
                },
            },
        }


def read_document_tool(file_path: str, max_chars: int = 8000, **kwargs: Any) -> ToolResult:
    """Convenience callable for ReadDocumentTool."""
    return ReadDocumentTool().run(file_path=file_path, max_chars=max_chars, **kwargs)


def summarize_document_tool(file_path: str, focus: str = "general", max_bullets: int = 5, language: str = "en", **kwargs: Any) -> ToolResult:
    """Convenience callable for SummarizeDocumentTool."""
    return SummarizeDocumentTool().run(file_path=file_path, focus=focus, max_bullets=max_bullets, language=language, **kwargs)


def inspect_document_tool(file_path: str, **kwargs: Any) -> ToolResult:
    """Convenience callable for InspectDocumentTool."""
    return InspectDocumentTool().run(file_path=file_path, **kwargs)


# Canonical exported tools list for Abhijit's registry auto-loader (Catch-Up Plan Section 4 & 7)
TOOLS: List[BaseTool] = [
    CreatePdfTool(),
    CreateDocxTool(),
    CreatePptxTool(),
    CreateWebsiteTool(),
    CreateChartTool(),
    CreateDocumentTool(),
    GenerateReportTool(),
    CreateTemplateTool(),
    ReadDocumentTool(),
    SummarizeDocumentTool(),
    InspectDocumentTool(),
]

# Auto-register all tools immediately into central registry
try:
    from tools.registry import register_tool

    for tool_instance in TOOLS:
        register_tool(tool_instance)
except Exception as _reg_exc:
    logger.debug("Registry auto-registration deferred: %s", _reg_exc)
