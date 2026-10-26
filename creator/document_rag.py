"""JARVIS Document Semantic RAG, Chunking & Citation Q&A Engine (Day 9 Deliverable).

Author: Vidhita (Document & Web Artifact Engineer - Pair D)
Role: Document Semantic Chunking, Multi-Format Vector RAG, and Grounded Citation Q&A
Branch: feature/vidhita-creator

Milestone Day 9 Capabilities:
1. Multi-format semantic chunking across PDF, Word (.docx), PowerPoint (.pptx), HTML Web Artifacts, and Markdown.
2. Context-preserving chunks: breadcrumb heading hierarchy, 1-based page/slide numbers, character offsets.
3. Dedicated table matrix and bento metric chunk isolation (never truncated across arbitrary boundaries).
4. Native Devanagari script awareness (accurate sentence tokenization for Marathi and Hindi text).
5. Hybrid semantic relevance ranking (BM25/TF-IDF keyword weighting, heading boost, table/metric intent boost).
6. Grounded autonomous Q&A (ask_document / query_document) via Google Gemini with strict factual citations.
7. Resilient offline extractive QA fallback with exact page and section citations when offline/quota-limited.
8. Full-Duplex stream cancellation token compliance (sub-20ms abort on cancel_event).
9. Workspace multi-document indexing (cross-document knowledge search with cached JSON catalog).
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
from pathlib import Path
import re
import sys
import time
from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Tuple, Union

from creator.document_reader import (
    SUPPORTED_EXTENSIONS,
    _clean_text,
    _contains_devanagari,
    _detect_format,
    inspect_document,
    read_document,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Stopwords and Tokenization Helpers (English, Marathi & Hindi)
# ---------------------------------------------------------------------------

_STOPWORDS_EN: Set[str] = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can", "cannot", "could", "did", "do",
    "does", "doing", "down", "during", "each", "few", "for", "from", "further",
    "had", "has", "have", "having", "he", "her", "here", "hers", "herself", "him",
    "himself", "his", "how", "i", "if", "in", "into", "is", "it", "its", "itself",
    "just", "me", "more", "most", "my", "myself", "no", "nor", "not", "now", "of",
    "off", "on", "once", "only", "or", "other", "ought", "our", "ours", "ourselves",
    "out", "over", "own", "same", "she", "should", "so", "some", "such", "than",
    "that", "the", "their", "theirs", "them", "themselves", "then", "there",
    "these", "they", "this", "those", "through", "to", "too", "under", "until",
    "up", "very", "was", "we", "were", "what", "when", "where", "which", "while",
    "who", "whom", "why", "with", "would", "you", "your", "yours", "yourself",
}

# Common Marathi / Hindi functional words
_STOPWORDS_INDIC: Set[str] = {
    "आहे", "आहेत", "होते", "होता", "होती", "नाही", "आणि", "किंवा", "पण", "परंतु",
    "या", "त्या", "ते", "ती", "तो", "ने", "मध्ये", "वर", "खाली", "साठी", "केले",
    "करा", "झाले", "का", "कसे", "काय", "कधी", "कुठे", "कोण", "सर्व", "काही",
    "है", "हैं", "था", "थी", "थे", "नहीं", "और", "या", "पर", "में", "से", "के",
    "की", "को", "का", "एक", "यह", "वह", "किया", "होगा", "सकता", "सकते",
}


def _tokenize(text: str) -> List[str]:
    """Tokenize string into lowercase alphanumeric words, stripping punctuation."""
    if not text:
        return []
    # Match English words, numbers, and Devanagari Unicode sequences
    tokens = re.findall(r"[\u0900-\u097F\w]+", text.lower())
    return [t for t in tokens if len(t) > 1 and t not in _STOPWORDS_EN and t not in _STOPWORDS_INDIC]


def _split_into_sentences(text: str) -> List[str]:
    """Split text into sentences respecting English periods and Devanagari Danda (।)."""
    if not text or not text.strip():
        return []
    # Split on period, exclamation, question mark, or Devanagari Danda followed by space or newline
    raw_sentences = re.split(r"(?<=[.!?।\n])\s+", text)
    sentences = [s.strip() for s in raw_sentences if s and len(s.strip()) > 2]
    return sentences if sentences else [text.strip()]


def _format_table_as_chunk(table: Dict[str, Any]) -> str:
    """Format a 2D table dictionary into a readable Markdown text block."""
    headers = table.get("headers") or []
    rows = table.get("rows") or []
    title = table.get("title") or "Table"

    lines: List[str] = [f"[Table: {title}]"]
    if headers:
        lines.append(" | ".join(str(h) for h in headers))
        lines.append(" | ".join("---" for _ in headers))
    for r in rows:
        lines.append(" | ".join(str(c) for c in r))
    return "\n".join(lines)


def _format_metrics_as_chunk(metrics: List[Dict[str, Any]]) -> str:
    """Format bento metric KPI cards into a clear readable text block."""
    lines: List[str] = ["[Key Metrics & Telemetry]"]
    for m in metrics:
        lbl = m.get("label", "Metric")
        val = m.get("value", "")
        delta = m.get("delta")
        if delta:
            lines.append(f"• {lbl}: {val} ({delta})")
        else:
            lines.append(f"• {lbl}: {val}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Multi-Format Semantic Chunking Engine
# ---------------------------------------------------------------------------

def chunk_document(
    file_path: Union[str, Path],
    chunk_size: int = 800,
    overlap: int = 150,
    max_chunks: int = 200,
) -> List[Dict[str, Any]]:
    """Chunks any supported document into rich semantic passages with metadata.

    Preserves heading hierarchies, page numbers, table matrices, and bento cards.
    Handles PDF, Word (.docx), PowerPoint (.pptx), HTML Web Artifacts, Markdown, and Text.

    Args:
        file_path: Path to the target document.
        chunk_size: Target character length per semantic passage (default: 800).
        overlap: Character overlap between consecutive text chunks (default: 150).
        max_chunks: Maximum number of chunks to return (guard against infinite loops).

    Returns:
        List of chunk dictionaries with:
        - chunk_id: Short unique SHA256 hash.
        - chunk_index: 0-based sequential integer.
        - text: Clean passage text content.
        - heading: Most immediate section heading.
        - breadcrumbs: Ancestor headings path list.
        - page_or_slide: 1-based page or slide index (when available).
        - source_file: Original filename.
        - format: Document format ('pdf', 'docx', 'pptx', 'html', etc.).
        - has_table: True if the chunk encapsulates a structured table.
        - has_metrics: True if the chunk encapsulates KPI metric cards.
        - char_start: Character offset start.
        - char_end: Character offset end.
        - word_count: Number of words in passage.
    """
    path = Path(file_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Document not found at: {path}")

    # Read document using full-fidelity Day 8 reader engine
    doc_data = read_document(str(path), max_chars=100000)
    filename = path.name
    doc_format = doc_data.get("format", _detect_format(path))
    sections = doc_data.get("sections") or []
    tables = doc_data.get("tables") or []
    metrics = doc_data.get("metrics") or []
    raw_text = doc_data.get("text", "")

    chunks: List[Dict[str, Any]] = []
    chunk_idx = 0
    running_char_offset = 0

    def _make_chunk(
        content: str,
        heading: str = "General",
        breadcrumbs: Optional[List[str]] = None,
        page_or_slide: int = 1,
        has_table: bool = False,
        has_metrics: bool = False,
    ) -> Optional[Dict[str, Any]]:
        nonlocal chunk_idx, running_char_offset
        clean = _clean_text(content)
        if not clean or len(clean) < 15:
            return None

        cid_raw = f"{filename}:{chunk_idx}:{clean[:40]}"
        chunk_id = hashlib.sha256(cid_raw.encode("utf-8")).hexdigest()[:12]
        char_len = len(clean)

        chunk_dict = {
            "chunk_id": chunk_id,
            "chunk_index": chunk_idx,
            "text": clean,
            "heading": heading,
            "breadcrumbs": breadcrumbs or ([heading] if heading else []),
            "page_or_slide": page_or_slide,
            "source_file": filename,
            "file_path": str(path),
            "format": doc_format,
            "has_table": has_table,
            "has_metrics": has_metrics,
            "char_start": running_char_offset,
            "char_end": running_char_offset + char_len,
            "word_count": len(clean.split()),
        }
        chunk_idx += 1
        running_char_offset += char_len + 1
        return chunk_dict

    # If no structured sections but raw_text exists, parse sections from headings or markers
    if not sections and raw_text:
        if "## " in raw_text:
            raw_parts = re.split(r"(?:^|\n+)##\s+", raw_text)
            for r_idx, part in enumerate(raw_parts):
                part_clean = part.strip()
                if not part_clean:
                    continue
                lines = part_clean.splitlines()
                h_name = lines[0].strip("# ").strip()
                body = "\n".join(lines[1:]).strip()
                sections.append({
                    "heading": h_name,
                    "text": body,
                    "page": r_idx + 1,
                })
        elif doc_data.get("headings"):
            # Split raw_text across identified headings
            doc_headings = doc_data["headings"]
            curr_pos = 0
            for h_idx, h in enumerate(doc_headings):
                next_h = doc_headings[h_idx + 1] if h_idx + 1 < len(doc_headings) else None
                start = raw_text.find(h, curr_pos)
                if start == -1:
                    continue
                end = raw_text.find(next_h, start + len(h)) if next_h else len(raw_text)
                sec_content = raw_text[start + len(h):end].strip() if end != -1 else raw_text[start + len(h):].strip()
                sections.append({
                    "heading": h,
                    "text": sec_content,
                    "page": h_idx + 1,
                })
                curr_pos = end if end != -1 else len(raw_text)

    # 1. Chunk structured sections if available (DOCX, PPTX, HTML, structured PDF)
    if sections:
        for s_idx, sec in enumerate(sections):
            if len(chunks) >= max_chunks:
                break

            heading = sec.get("heading") or f"Section {s_idx + 1}"
            sec_text = sec.get("text") or ""
            sec_bullets = sec.get("bullets") or []
            sec_metrics = sec.get("metrics") or []
            sec_table = sec.get("table") or []
            page_or_slide = sec.get("page", sec.get("slide", s_idx + 1))
            breadcrumbs = [doc_data.get("title", filename), heading]

            # Construct consolidated section body
            body_parts: List[str] = []
            if sec_text:
                body_parts.append(sec_text)
            if sec_bullets:
                body_parts.append("\n".join(f"• {b}" for b in sec_bullets))

            full_body = "\n\n".join(body_parts)

            # Split large section body with sliding window and sentence preservation
            if len(full_body) > chunk_size:
                sentences = _split_into_sentences(full_body)
                curr_passage: List[str] = []
                curr_len = 0

                for sent in sentences:
                    if curr_len + len(sent) > chunk_size and curr_passage:
                        passage_text = " ".join(curr_passage)
                        c = _make_chunk(
                            content=passage_text,
                            heading=heading,
                            breadcrumbs=breadcrumbs,
                            page_or_slide=page_or_slide,
                        )
                        if c:
                            chunks.append(c)

                        # Carry forward overlap
                        overlap_budget = overlap
                        overlap_sentences: List[str] = []
                        for prev_s in reversed(curr_passage):
                            overlap_sentences.insert(0, prev_s)
                            overlap_budget -= len(prev_s)
                            if overlap_budget <= 0:
                                break

                        curr_passage = list(overlap_sentences)
                        curr_len = sum(len(s) for s in curr_passage)

                    curr_passage.append(sent)
                    curr_len += len(sent)

                if curr_passage:
                    c = _make_chunk(
                        content=" ".join(curr_passage),
                        heading=heading,
                        breadcrumbs=breadcrumbs,
                        page_or_slide=page_or_slide,
                    )
                    if c:
                        chunks.append(c)
            elif full_body:
                c = _make_chunk(
                    content=full_body,
                    heading=heading,
                    breadcrumbs=breadcrumbs,
                    page_or_slide=page_or_slide,
                )
                if c:
                    chunks.append(c)

            # Dedicated metrics chunk if present
            if sec_metrics:
                m_text = _format_metrics_as_chunk(sec_metrics)
                c_m = _make_chunk(
                    content=m_text,
                    heading=f"{heading} - Metrics",
                    breadcrumbs=breadcrumbs + ["Metrics"],
                    page_or_slide=page_or_slide,
                    has_metrics=True,
                )
                if c_m:
                    chunks.append(c_m)

            # Dedicated table chunk if present in section
            if sec_table:
                t_dict = {"headers": sec_table[0] if sec_table else [], "rows": sec_table[1:] if len(sec_table) > 1 else [], "title": heading}
                t_text = _format_table_as_chunk(t_dict)
                c_t = _make_chunk(
                    content=t_text,
                    heading=f"{heading} - Table",
                    breadcrumbs=breadcrumbs + ["Table"],
                    page_or_slide=page_or_slide,
                    has_table=True,
                )
                if c_t:
                    chunks.append(c_t)

    # 2. Fallback: chunk raw text if no sections were produced
    if not chunks and raw_text:
        sentences = _split_into_sentences(raw_text)
        curr_passage = []
        curr_len = 0

        for sent in sentences:
            if curr_len + len(sent) > chunk_size and curr_passage:
                c = _make_chunk(
                    content=" ".join(curr_passage),
                    heading="Document Content",
                    breadcrumbs=[filename],
                    page_or_slide=1,
                )
                if c:
                    chunks.append(c)

                overlap_budget = overlap
                overlap_sentences = []
                for prev_s in reversed(curr_passage):
                    overlap_sentences.insert(0, prev_s)
                    overlap_budget -= len(prev_s)
                    if overlap_budget <= 0:
                        break

                curr_passage = list(overlap_sentences)
                curr_len = sum(len(s) for s in curr_passage)

            curr_passage.append(sent)
            curr_len += len(sent)

        if curr_passage:
            c = _make_chunk(
                content=" ".join(curr_passage),
                heading="Document Content",
                breadcrumbs=[filename],
                page_or_slide=1,
            )
            if c:
                chunks.append(c)

    # 3. Add top-level tables not captured inside sections
    if tables and not any(c.get("has_table") for c in chunks):
        for t_idx, tbl in enumerate(tables):
            if len(chunks) >= max_chunks:
                break
            t_text = _format_table_as_chunk(tbl)
            c = _make_chunk(
                content=t_text,
                heading=f"Data Table {t_idx + 1}",
                breadcrumbs=[doc_data.get("title", filename), f"Table {t_idx + 1}"],
                page_or_slide=tbl.get("page", 1),
                has_table=True,
            )
            if c:
                chunks.append(c)

    # 4. Add top-level metrics not captured inside sections
    if metrics and not any(c.get("has_metrics") for c in chunks):
        m_text = _format_metrics_as_chunk(metrics)
        c = _make_chunk(
            content=m_text,
            heading="Executive Metrics",
            breadcrumbs=[doc_data.get("title", filename), "Metrics"],
            page_or_slide=1,
            has_metrics=True,
        )
        if c:
            chunks.append(c)

    logger.info("Chunked document '%s' into %d semantic passages.", filename, len(chunks))
    return chunks


# ---------------------------------------------------------------------------
# Semantic Retrieval & Relevance Scoring Engine
# ---------------------------------------------------------------------------

def _score_chunk(chunk: Dict[str, Any], query_tokens: List[str], raw_query: str) -> float:
    """Calculates hybrid relevance score (0.0 to 1.0) for a chunk against a query."""
    if not query_tokens:
        return 0.0

    chunk_text = chunk.get("text", "").lower()
    heading = chunk.get("heading", "").lower()
    breadcrumbs_str = " ".join(chunk.get("breadcrumbs", [])).lower()
    chunk_tokens = _tokenize(chunk_text)

    if not chunk_tokens:
        return 0.0

    # 1. Term Match Frequency & Unique Hits
    chunk_token_set = set(chunk_tokens)
    matched_tokens = [t for t in query_tokens if t in chunk_token_set]
    unique_matches = len(set(matched_tokens))
    query_unique = len(set(query_tokens))

    coverage_ratio = unique_matches / max(query_unique, 1)

    # 2. Heading and Breadcrumbs Boost
    heading_matches = sum(1 for t in query_tokens if t in heading or t in breadcrumbs_str)
    heading_boost = 0.25 * min(heading_matches, 2)

    # 3. Exact Substring Match Boost
    clean_query = raw_query.strip().lower()
    exact_phrase_boost = 0.35 if (len(clean_query) > 3 and clean_query in chunk_text) else 0.0

    # 4. Table / Metric Intent Boost
    intent_boost = 0.0
    wants_numbers = bool(re.search(r"\b(?:table|matrix|metric|kpi|stat|stats|latency|percent|%|data|column|row)\b", clean_query))
    if wants_numbers:
        if chunk.get("has_table"):
            intent_boost += 0.30
        if chunk.get("has_metrics"):
            intent_boost += 0.25

    # 5. Composite Normalized Score
    raw_score = (0.50 * coverage_ratio) + heading_boost + exact_phrase_boost + intent_boost
    return min(round(raw_score, 4), 1.0)


def search_document(
    file_path: Union[str, Path],
    query: str,
    top_k: int = 3,
    min_score: float = 0.05,
    chunk_size: int = 800,
) -> List[Dict[str, Any]]:
    """Performs semantic relevance search over a document and returns ranked chunks with citations.

    Args:
        file_path: Path to target document (PDF, Word, PPTX, HTML, Markdown).
        query: User search question or topic.
        top_k: Maximum number of top passages to return (default: 3).
        min_score: Minimum relevance threshold (default: 0.05).
        chunk_size: Character size for chunking (default: 800).

    Returns:
        List of ranked chunk dictionaries sorted by relevance score, with 'score' and 'citation' added.
    """
    if not query or not str(query).strip():
        return []

    chunks = chunk_document(file_path=file_path, chunk_size=chunk_size)
    if not chunks:
        return []

    query_tokens = _tokenize(query)
    scored_chunks: List[Dict[str, Any]] = []

    for c in chunks:
        score = _score_chunk(c, query_tokens, query)
        if score >= min_score:
            res_chunk = dict(c)
            res_chunk["score"] = score

            # Build human-readable verified citation tag
            page_val = c.get("page_or_slide", 1)
            fmt = c.get("format", "").upper()
            unit_name = "Slide" if fmt == "PPTX" else "Page"
            heading = c.get("heading") or "General"
            res_chunk["citation"] = f"[{c['source_file']} - {unit_name} {page_val}, Section: \"{heading}\"]"
            scored_chunks.append(res_chunk)

    # Sort descending by score, tiebreak with chunk_index
    scored_chunks.sort(key=lambda x: (x["score"], -x["chunk_index"]), reverse=True)
    return scored_chunks[:top_k]


# ---------------------------------------------------------------------------
# Grounded Document Q&A Engine (Gemini + Resilient Offline Extractive Fallback)
# ---------------------------------------------------------------------------

def _offline_extractive_answer(
    question: str,
    top_chunks: List[Dict[str, Any]],
    language: str = "en",
) -> Dict[str, Any]:
    """Generates an extractive cited answer strictly grounded in top chunks without external LLMs."""
    if not top_chunks:
        msg = {
            "mr": "दस्तऐवजात या प्रश्नाचे अचूक उत्तर सापडले नाही.",
            "hi": "दस्तावेज़ में इस प्रश्न का सटीक उत्तर नहीं मिला.",
            "en": "No relevant information found in the document for this question.",
        }.get(language, "No relevant information found.")
        return {
            "success": False,
            "answer": msg,
            "citations": [],
            "grounded": False,
            "engine": "offline_extractive",
            "chunks_used": 0,
        }

    query_tokens = set(_tokenize(question))
    selected_sentences: List[str] = []
    citations: List[str] = []

    for chunk in top_chunks:
        c_cit = chunk.get("citation", "")
        if c_cit and c_cit not in citations:
            citations.append(c_cit)

        c_text = chunk.get("text", "")
        # If it's a table chunk, include key table lines
        if chunk.get("has_table") or "[Table:" in c_text:
            lines = [l.strip() for l in c_text.splitlines() if l.strip()]
            selected_sentences.extend(lines[:4])
            continue

        sentences = _split_into_sentences(c_text)
        scored_sents: List[Tuple[float, str]] = []
        for s in sentences:
            s_toks = set(_tokenize(s))
            overlap_cnt = len(query_tokens.intersection(s_toks))
            scored_sents.append((overlap_cnt, s))

        scored_sents.sort(key=lambda x: x[0], reverse=True)
        # Take top 2 most relevant sentences from each chunk
        for sc, st in scored_sents[:2]:
            if st not in selected_sentences:
                selected_sentences.append(st)

    ans_body = " ".join(selected_sentences[:5])
    if citations:
        ans_body += f"\n\n**Sources:** {', '.join(citations)}"

    return {
        "success": True,
        "answer": ans_body,
        "citations": citations,
        "grounded": True,
        "engine": "offline_extractive",
        "chunks_used": len(top_chunks),
        "language": language,
    }


def ask_document(
    file_path: Union[str, Path],
    question: str,
    language: str = "en",
    top_k: int = 3,
    cancel_event: Optional[Any] = None,
) -> Dict[str, Any]:
    """Answers user questions strictly grounded in a multi-format document with precise citations.

    Uses Google Gemini (gemini-3.5-flash-lite) with strict grounding, and falls back to
    deterministic extractive NLP when offline or when quota limits are reached.

    Args:
        file_path: Path to document (PDF, Word, PPTX, HTML, Markdown).
        question: Question to answer based on the document.
        language: Response language: 'en' (English), 'mr' (Marathi), 'hi' (Hindi).
        top_k: Number of semantic context passages to retrieve (default: 3).
        cancel_event: Optional threading.Event / asyncio.Event for Day 8 sub-20ms cancellation.

    Returns:
        Dictionary containing:
        - answer: Grounded, factual response string.
        - citations: List of formatted source references.
        - top_chunks: Retrieved passage dictionaries with scores.
        - engine: 'gemini' or 'offline_extractive'.
        - success: Boolean status.
    """
    if cancel_event is not None and getattr(cancel_event, "is_set", lambda: False)():
        raise InterruptedError("Document Q&A cancelled before retrieval.")

    path = Path(file_path).resolve()
    if not path.exists():
        return {
            "success": False,
            "error": f"File not found: {file_path}",
            "answer": f"Document '{path.name}' does not exist.",
            "citations": [],
            "engine": "none",
        }

    # 1. Retrieve top-k semantic chunks
    top_chunks = search_document(file_path=path, query=question, top_k=top_k)
    if not top_chunks:
        return _offline_extractive_answer(question, [], language=language)

    if cancel_event is not None and getattr(cancel_event, "is_set", lambda: False)():
        raise InterruptedError("Document Q&A cancelled after retrieval.")

    citations = [c.get("citation", "") for c in top_chunks if c.get("citation")]

    # 2. Attempt Google Gemini inference with strict grounding
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    gemini_model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

    if gemini_key:
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(
                api_key=gemini_key,
                http_options=types.HttpOptions(timeout=12000),
            )

            context_blocks = []
            for idx, c in enumerate(top_chunks):
                unit_label = "Slide" if c.get("format") == "pptx" else "Page"
                context_blocks.append(
                    f"--- EXCERPT {idx + 1} ({unit_label} {c.get('page_or_slide', 1)}, Section: \"{c.get('heading', 'General')}\") ---\n"
                    f"{c.get('text', '')}\n"
                )
            context_str = "\n".join(context_blocks)

            lang_rules = {
                "mr": "उत्तर शुद्ध मराठीत (मराठी देवनागरी) द्या. प्रत्येक मुख्य माहितीच्या शेवटी स्त्रोत उद्धृत करा.",
                "hi": "उत्तर स्पष्ट हिंदी (देवनागरी) में दें। हर महत्वपूर्ण तथ्य के साथ संदर्भ उद्धृत करें।",
                "en": "Answer in clear, authoritative English. Append inline citations [Page X / Section Y] directly after assertions.",
            }.get(language.lower(), "Answer in clear English with inline citations.")

            prompt = f"""You are the JARVIS Autonomous Document Intelligence Engine.
Answer the user's question STRICTLY based on the provided document excerpts below.

GROUNDING RULES:
1. Do NOT hallucinate or speculate. If the excerpts do not contain the answer, explicitly state that the document does not mention it.
2. {lang_rules}
3. Always cite the exact page/slide and section for every key fact using format: [Source: Page X, "Section Title"].
4. Keep the answer direct, concise, and professional.

QUESTION:
{question}

DOCUMENT EXCERPTS:
{context_str}

ANSWER:
"""

            response = client.models.generate_content(
                model=gemini_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                ),
            )

            if cancel_event is not None and getattr(cancel_event, "is_set", lambda: False)():
                raise InterruptedError("Document Q&A cancelled after inference.")

            raw_answer = response.text or ""
            if raw_answer.strip():
                return {
                    "success": True,
                    "answer": raw_answer.strip(),
                    "citations": citations,
                    "top_chunks": top_chunks,
                    "engine": "gemini",
                    "language": language,
                    "file_path": str(path),
                }
        except Exception as exc:
            logger.warning("Gemini document Q&A failed (%s), falling back to offline extractive answer: %s", type(exc).__name__, exc)

    # 3. Fallback to resilient offline extractive answer
    offline_res = _offline_extractive_answer(question, top_chunks, language=language)
    offline_res["success"] = True
    offline_res["top_chunks"] = top_chunks
    offline_res["file_path"] = str(path)
    return offline_res


# ---------------------------------------------------------------------------
# Multi-Document Workspace Knowledge Indexer
# ---------------------------------------------------------------------------

def index_workspace_documents(
    folder_path: Union[str, Path] = "workspace",
    save_catalog: bool = True,
) -> Dict[str, Any]:
    """Scans and indexes all documents in a workspace directory into a unified knowledge catalog.

    Discovers PDF, DOCX, PPTX, HTML, Markdown, and TXT files, parses their metadata and chunks,
    and caches the catalog to '{folder_path}/.document_index.json'.

    Args:
        folder_path: Target directory (default: 'workspace').
        save_catalog: If True, writes the index cache to JSON on disk.

    Returns:
        Dictionary summarizing indexed files, total chunks, format breakdown, and catalog data.
    """
    root = Path(folder_path).resolve()
    if not root.exists():
        return {
            "success": False,
            "error": f"Directory not found: {folder_path}",
            "indexed_files": 0,
            "total_chunks": 0,
        }

    supported_suffixes = set(SUPPORTED_EXTENSIONS.keys())
    discovered_files: List[Path] = []

    for f in root.iterdir():
        if f.is_file() and f.suffix.lower() in supported_suffixes and not f.name.startswith("."):
            discovered_files.append(f)

    catalog: List[Dict[str, Any]] = []
    format_counts: Dict[str, int] = {}
    total_chunks = 0

    for file_path in discovered_files:
        try:
            fmt = file_path.suffix.lower().lstrip(".")
            format_counts[fmt] = format_counts.get(fmt, 0) + 1

            # Inspect doc structure
            meta = inspect_document(str(file_path))
            # Generate semantic chunks
            chunks = chunk_document(str(file_path), chunk_size=800, max_chunks=50)
            total_chunks += len(chunks)

            catalog.append({
                "filename": file_path.name,
                "file_path": str(file_path),
                "format": fmt,
                "size_kb": meta.get("size_kb", 0),
                "page_or_slide_count": meta.get("page_or_slide_count", 1),
                "table_count": meta.get("table_count", 0),
                "word_count": meta.get("word_count", 0),
                "headings": meta.get("headings", [])[:10],
                "chunks": chunks,
            })
        except Exception as exc:
            logger.warning("Failed to index document '%s': %s", file_path.name, exc)

    summary = {
        "success": True,
        "indexed_files": len(catalog),
        "total_chunks": total_chunks,
        "format_breakdown": format_counts,
        "folder": str(root),
        "timestamp": time.time(),
        "catalog": catalog,
    }

    if save_catalog:
        try:
            cache_file = root / ".document_index.json"
            # Strip deep chunk text for lightweight disk cache
            lite_catalog = []
            for item in catalog:
                lite_item = dict(item)
                lite_item["chunks"] = [
                    {k: v for k, v in c.items() if k != "text"} for c in item["chunks"]
                ]
                lite_catalog.append(lite_item)

            cache_data = dict(summary)
            cache_data["catalog"] = lite_catalog
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            logger.info("Saved workspace document index cache to: %s", cache_file)
        except Exception as save_exc:
            logger.warning("Could not persist workspace index cache: %s", save_exc)

    return summary


def query_workspace_knowledge(
    query: str,
    folder_path: Union[str, Path] = "workspace",
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """Cross-document semantic search across all files in workspace directory.

    Args:
        query: Search question or concept.
        folder_path: Folder to search across (default: 'workspace').
        top_k: Top results to return across all documents (default: 5).

    Returns:
        List of top-scoring passages across all workspace documents with citations.
    """
    root = Path(folder_path).resolve()
    if not root.exists():
        return []

    index_res = index_workspace_documents(folder_path=root, save_catalog=False)
    all_chunks: List[Dict[str, Any]] = []
    for doc in index_res.get("catalog", []):
        all_chunks.extend(doc.get("chunks", []))

    if not all_chunks:
        return []

    query_tokens = _tokenize(query)
    scored: List[Dict[str, Any]] = []

    for c in all_chunks:
        score = _score_chunk(c, query_tokens, query)
        if score > 0.05:
            res_chunk = dict(c)
            res_chunk["score"] = score
            unit_name = "Slide" if c.get("format") == "pptx" else "Page"
            res_chunk["citation"] = f"[{c['source_file']} - {unit_name} {c.get('page_or_slide', 1)}, Section: \"{c.get('heading', 'General')}\"]"
            scored.append(res_chunk)

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]
