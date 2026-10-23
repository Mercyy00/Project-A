"""JARVIS Document Creator Module.

Author: Vidhita (Document Engineer)
Role: Document Generation (PDF, Word, PowerPoint, Charts, Executive Reports, Templates)
"""

from creator.themes import THEMES, get_theme, contains_devanagari, register_devanagari_fonts
from creator.hello_docs import generate_hello_docs
from creator.pdf_maker import make_pdf
from creator.docx_maker import make_docx
from creator.pptx_maker import make_pptx
from creator.chart_maker import generate_chart
from creator.charts import make_chart
from creator.report_maker import generate_executive_report
from creator.outline import create_document, generate_outline
from creator.templates import (
    project_report,
    assignment_cover,
    resume,
    application_letter,
)
from creator.tools import (
    CreatePdfTool,
    CreateDocxTool,
    CreatePptxTool,
    CreateChartTool,
    CreateDocumentTool,
    GenerateReportTool,
    CreateTemplateTool,
    create_pdf,
    create_docx,
    create_pptx,
    create_chart,
    create_document_tool,
    generate_report,
    create_template_document,
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
    "make_chart",
    "generate_executive_report",
    "create_document",
    "generate_outline",
    "project_report",
    "assignment_cover",
    "resume",
    "application_letter",
    "CreatePdfTool",
    "CreateDocxTool",
    "CreatePptxTool",
    "CreateChartTool",
    "CreateDocumentTool",
    "GenerateReportTool",
    "CreateTemplateTool",
    "create_pdf",
    "create_docx",
    "create_pptx",
    "create_chart",
    "create_document_tool",
    "generate_report",
    "create_template_document",
    "TOOLS",
]
