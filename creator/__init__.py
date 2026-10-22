"""JARVIS Document Creator Module.

Author: Vidhita (Document Engineer)
Role: Document Generation (PDF, Word, PowerPoint)
"""

from creator.themes import THEMES, get_theme, contains_devanagari, register_devanagari_fonts
from creator.hello_docs import generate_hello_docs
from creator.pdf_maker import make_pdf
from creator.docx_maker import make_docx
from creator.pptx_maker import make_pptx
from creator.outline import create_document, generate_outline
from creator.tools import (
    CreatePdfTool,
    CreateDocxTool,
    CreatePptxTool,
    CreateDocumentTool,
    create_pdf,
    create_docx,
    create_pptx,
    create_document_tool,
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
    "create_document",
    "generate_outline",
    "CreatePdfTool",
    "CreateDocxTool",
    "CreatePptxTool",
    "CreateDocumentTool",
    "create_pdf",
    "create_docx",
    "create_pptx",
    "create_document_tool",
    "TOOLS",
]
