"""JARVIS Document & Web Artifact Creator Module.

Author: Document Engineer
Role: Document Generation (PDF, Word, PowerPoint, Web Artifacts, Charts, Executive Reports, Templates)
"""

from creator.themes import (
    THEMES,
    get_theme,
    contains_devanagari,
    register_devanagari_fonts,
    register_all_fonts,
)
from creator.hello_docs import generate_hello_docs
from creator.pdf_maker import make_pdf
from creator.docx_maker import make_docx
from creator.pptx_maker import make_pptx
from creator.web_maker import make_website
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
from creator.document_reader import (
    read_document,
    inspect_document,
    extract_tables,
    summarize_document,
)
from creator.tools import (
    CreatePdfTool,
    CreateDocxTool,
    CreatePptxTool,
    CreateWebsiteTool,
    CreateChartTool,
    CreateDocumentTool,
    GenerateReportTool,
    CreateTemplateTool,
    ReadDocumentTool,
    SummarizeDocumentTool,
    InspectDocumentTool,
    create_pdf,
    create_docx,
    create_pptx,
    create_website,
    create_chart,
    create_document_tool,
    generate_report,
    create_template_document,
    read_document_tool,
    summarize_document_tool,
    inspect_document_tool,
    TOOLS,
)

__all__ = [
    "THEMES",
    "get_theme",
    "contains_devanagari",
    "register_devanagari_fonts",
    "register_all_fonts",
    "generate_hello_docs",
    "make_pdf",
    "make_docx",
    "make_pptx",
    "make_website",
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
    "CreateWebsiteTool",
    "CreateChartTool",
    "CreateDocumentTool",
    "GenerateReportTool",
    "CreateTemplateTool",
    "create_pdf",
    "create_docx",
    "create_pptx",
    "create_website",
    "create_chart",
    "create_document_tool",
    "generate_report",
    "create_template_document",
    "read_document",
    "inspect_document",
    "extract_tables",
    "summarize_document",
    "ReadDocumentTool",
    "SummarizeDocumentTool",
    "InspectDocumentTool",
    "read_document_tool",
    "summarize_document_tool",
    "inspect_document_tool",
    "TOOLS",
]
