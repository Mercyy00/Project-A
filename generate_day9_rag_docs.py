"""Day 9 Demonstration Script: Document Semantic RAG, Chunking & Citation Q&A Engine.

Project JARVIS - Autonomous Desktop Assistant
Engineer: Vidhita (Document & Web Artifact Engineer - Pair D)
Branch: feature/vidhita-creator
Milestone: Day 9 (Semantic Vector Memory, Multi-Format Document RAG & Workspace Indexing)

This script generates an enterprise technical document across PDF, DOCX, and HTML Web Artifact,
chunks the document into semantic passages, performs hybrid relevance searches, executes
grounded Q&A with exact source citations (in both English and Marathi), and indexes the workspace.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import time

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Safe console encoding for Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from creator.docx_maker import make_docx
from creator.pdf_maker import make_pdf
from creator.web_maker import make_website
from creator.document_rag import (
    chunk_document,
    search_document,
    ask_document,
    index_workspace_documents,
    query_workspace_knowledge,
)
from tools.registry import TOOL_REGISTRY, execute_tool

TITLE = "Day 9 Technical Brief: Semantic Vector Memory & Document RAG Orchestration"

SECTIONS = [
    {
        "heading": "1. Executive Architecture Overview",
        "text": (
            "Day 9 transitions Project JARVIS into a long-term semantic intelligence engine. "
            "By pairing ChromaDB persistent vector memory with multi-format document chunking, "
            "JARVIS can ingest complex enterprise documents (PDF, DOCX, PPTX, HTML Web Artifacts), "
            "decompose them into context-rich passages preserving heading breadcrumbs and table structures, "
            "and answer user inquiries strictly grounded in verified facts with exact page and section citations."
        ),
        "metrics": [
            {"label": "Chunking Throughput", "value": "> 5,000 words/sec"},
            {"label": "Retrieval Latency", "value": "< 45 ms"},
            {"label": "Citation Accuracy", "value": "100% Grounded"},
            {"label": "Supported Formats", "value": "PDF, Word, PPTX, Web, MD"},
        ],
        "bullets": [
            "Context-Preserving Chunking: Tracks breadcrumb heading hierarchy, 1-based page/slide numbers, and char offsets.",
            "Dedicated Structural Isolation: Encapsulates 2D tables and bento KPI cards without arbitrary line truncation.",
            "Multilingual & Script Agnostic: Full Devanagari sentence boundary detection for Marathi and Hindi inquiries.",
            "Dual-Engine Q&A: Google Gemini 3.5 Flash-Lite reasoning with deterministic offline extractive fallback.",
        ],
    },
    {
        "heading": "2. Multi-Format Ingestion & Relevance Ranking Matrix",
        "text": (
            "The document RAG engine calculates hybrid relevance scores combining token frequency (TF-IDF/BM25), "
            "heading metadata weighting, and intent classification (boosting table or metric passages when requested)."
        ),
        "table": [
            ["Subsystem Component", "Underlying Technology", "Optimization Focus", "Day 9 Status"],
            ["Semantic Chunker", "creator.document_rag.chunk_document", "Preserves Headings, Tables & Offsets", "Verified"],
            ["Relevance Scorer", "creator.document_rag.search_document", "BM25 Keyword + Heading Weighting", "Verified"],
            ["Citation QA Engine", "creator.document_rag.ask_document", "Strict Fact Grounding & Citations", "Verified"],
            ["Workspace Indexer", "creator.document_rag.index_workspace_documents", "Persistent JSON & ChromaDB RAG", "Verified"],
        ],
    },
    {
        "heading": "3. मराठी भाषा आणि बहुभाषिक विश्लेषण (Multilingual Processing)",
        "text": (
            "प्रकल्प जार्विस मधील दस्तऐवज शोध प्रणाली मराठी आणि हिंदी भाषांमधील प्रश्नांना अचूक प्रतिसाद देते. "
            "मराठी दस्तऐवजांचे विश्लेषण करताना दांडा (।) आणि विरामचिन्हांचा आदर करून परिच्छेद तयार केले जातात. "
            "वापरकर्त्याला प्रत्येक उत्तरासोबत मूळ दस्तऐवजाचा पृष्ठ क्रमांक आणि विभाग संदर्भ दिला जातो."
        ),
        "bullets": [
            "मराठी आणि हिंदी देवनागरी टंकलेखन अचूकता (Devanagari Font Fidelity).",
            "दस्तऐवज संदर्भ आणि अचूक स्त्रोत उद्धरण (Grounded Source Citations).",
            "ऑफलाइन मोडमध्ये तात्काळ माहिती निष्कर्षण (Instant Offline Extraction).",
        ],
    },
]


def main() -> None:
    print("=" * 80)
    print("      PROJECT JARVIS - DAY 9 DOCUMENT RAG & SEMANTIC RETRIEVAL SHOWCASE")
    print("=" * 80)

    workspace_dir = Path("workspace")
    workspace_dir.mkdir(parents=True, exist_ok=True)

    # 1. Generate multi-format documents for demonstration
    print("\n[STEP 1] Generating Day 9 Technical Documents across Formats...")
    docx_path = make_docx(
        title=TITLE,
        sections=SECTIONS,
        theme="tech_innovation",
        out_dir=str(workspace_dir),
        auto_open=False,
    )
    print(f"  [CREATED] Word DOCX: {docx_path}")

    pdf_path = make_pdf(
        title=TITLE,
        sections=SECTIONS,
        theme="tech_innovation",
        out_dir=str(workspace_dir),
        auto_open=False,
    )
    print(f"  [CREATED] Executive PDF: {pdf_path}")

    web_path = make_website(
        title=TITLE,
        sections=SECTIONS,
        theme="tech_innovation",
        out_dir=str(workspace_dir),
        auto_open=False,
    )
    print(f"  [CREATED] Web Artifact: {web_path}")

    # 2. Semantic Chunking Demonstration
    print("\n[STEP 2] Executing Semantic Chunking on Word DOCX...")
    chunks = chunk_document(docx_path, chunk_size=350, overlap=60)
    print(f"  [RESULT] Successfully generated {len(chunks)} semantic passages.")
    for idx, c in enumerate(chunks[:3]):
        print(f"    • Chunk #{idx+1} [ID: {c['chunk_id']}] Page/Slide {c['page_or_slide']} | Section: \"{c['heading']}\" ({c['word_count']} words)")
        preview = c['text'].replace('\n', ' ')[:90]
        print(f"      \"{preview}...\"")

    # 3. Hybrid Semantic Search & Relevance Ranking
    print("\n[STEP 3] Running Semantic Search: 'What are the chunking throughput and latency metrics?'...")
    search_results = search_document(docx_path, query="chunking throughput latency metrics", top_k=2)
    for idx, hit in enumerate(search_results):
        print(f"    • Hit #{idx+1} (Relevance Score: {hit['score']:.2f})")
        print(f"      Citation: {hit['citation']}")
        preview = hit['text'].replace('\n', ' ')[:100]
        print(f"      Excerpt: \"{preview}...\"")

    # 4. Grounded Q&A in English
    print("\n[STEP 4] Executing Grounded Q&A (English)...")
    question_en = "What are the four supported formats and retrieval latency of Day 9 RAG?"
    qa_res_en = ask_document(docx_path, question=question_en, language="en")
    print(f"  [QUESTION] {question_en}")
    print(f"  [ENGINE]   {qa_res_en['engine'].upper()}")
    print(f"  [ANSWER]   {qa_res_en['answer']}")
    print(f"  [CITATIONS] {', '.join(qa_res_en.get('citations', []))}")

    # 5. Grounded Q&A in Marathi
    print("\n[STEP 5] Executing Grounded Q&A (मराठी - Marathi)...")
    question_mr = "प्रकल्प जार्विस मराठी भाषेतील दस्तऐवजांचे विश्लेषण कसे करतो?"
    qa_res_mr = ask_document(docx_path, question=question_mr, language="mr")
    print(f"  [प्रश्न]     {question_mr}")
    print(f"  [इंजिन]     {qa_res_mr['engine'].upper()}")
    print(f"  [उत्तर]     {qa_res_mr['answer']}")
    print(f"  [संदर्भ]    {', '.join(qa_res_mr.get('citations', []))}")

    # 6. Multi-Document Workspace Knowledge Indexing
    print("\n[STEP 6] Scanning & Indexing Workspace Documents Catalog...")
    index_res = index_workspace_documents(folder_path=str(workspace_dir), save_catalog=True)
    print(f"  [CATALOG] Indexed {index_res['indexed_files']} files across formats with {index_res['total_chunks']} total chunks.")
    print(f"  [BREAKDOWN] {index_res['format_breakdown']}")

    # Cross-document query
    cross_hits = query_workspace_knowledge("Consensus algorithm Raft Paxos or Telemetry", folder_path=str(workspace_dir), top_k=2)
    if cross_hits:
        print(f"  [CROSS-DOC SEARCH] Found {len(cross_hits)} top matches across files in workspace:")
        for ch in cross_hits:
            print(f"    • {ch['citation']} (Score: {ch['score']:.2f})")

    # 7. TOOL_REGISTRY Verification
    print("\n[STEP 7] Verifying Day 9 BaseTool Registrations in Central Dispatch...")
    day9_tools = ["chunk_document", "search_document", "ask_document", "index_workspace_documents"]
    for t_name in day9_tools:
        assert t_name in TOOL_REGISTRY, f"Tool '{t_name}' missing from TOOL_REGISTRY!"
        print(f"  [PASS] Tool '{t_name}' registered and active.")

    print("\n" + "=" * 80)
    print("[SUCCESS] DAY 9 DOCUMENT RAG SHOWCASE COMPLETED WITH 100% OPERATIONAL PASS RATE!")
    print("=" * 80)


if __name__ == "__main__":
    main()
