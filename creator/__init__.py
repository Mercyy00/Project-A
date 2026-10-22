"""JARVIS Document Creator Module.

Author: Vidhita (Document Engineer)
Role: Document Generation (PDF, Word, PowerPoint, Charts, Executive Reports)
"""

from creator.themes import THEMES, get_theme, contains_devanagari, register_devanagari_fonts
from creator.hello_docs import generate_hello_docs
from creator.pdf_maker import make_pdf
from creator.docx_maker import make_docx
from creator.pptx_maker import make_pptx
from creator.chart_maker import generate_chart
from creator.report_maker import generate_executive_report
from creator.tools import (
    CreatePdfTool,
    CreateDocxTool,
    CreatePptxTool,
    CreateChartTool,
    GenerateReportTool,
    create_pdf,
    create_docx,
    create_pptx,
    create_chart,
    generate_report,
    TOOLS,
)

__all__ = [
    "THEMES",
    "get_theme",
    "contains_devanagari",
    "register_devanagari_fonts",
    "generate_hello_docs",
    "make_pdf",
    "make_docx",
    "make_pptx",
    "generate_chart",
    "generate_executive_report",
    "CreatePdfTool",
    "CreateDocxTool",
    "CreatePptxTool",
    "CreateChartTool",
    "GenerateReportTool",
    "create_pdf",
    "create_docx",
    "create_pptx",
    "create_chart",
    "generate_report",
    "TOOLS",
]
