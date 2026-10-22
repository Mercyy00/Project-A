"""AI-powered Document Outline Generator and End-to-End Creator for JARVIS.

Author: Vidhita (Document Engineer)
Module: creator.outline

Implements Day 5 Acceptance Criteria:
- create_document(topic, kind='pdf', theme='clean_light', language='en') -> str
- Generates 4-6 section structured JSON outline via Gemini / LLM
- Native Devanagari generation for Hindi and Marathi
- Dispatches directly to make_pdf, make_docx, or make_pptx
- Resilient JSON validation with retry and deterministic offline fallback
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

from creator.docx_maker import make_docx
from creator.pdf_maker import make_pdf
from creator.pptx_maker import make_pptx

load_dotenv()
logger = logging.getLogger(__name__)


def _build_fallback_outline(topic: str, language: str = "en") -> Dict[str, Any]:
    """Generate a high-quality, structured fallback outline when cloud APIs are unavailable.

    Ensures zero crashes when network issues or API quota limits (429) occur.

    Args:
        topic: The document subject.
        language: Language code ('en', 'hi', 'mr').

    Returns:
        Dict[str, Any]: Structured outline with title and 4-6 sections.
    """
    clean_topic = topic.strip() or "Project Overview"

    if language.lower() in ("hi", "hindi"):
        return {
            "title": f"{clean_topic}: एक व्यापक अध्ययन",
            "sections": [
                {
                    "heading": "१. परिचय एवं पृष्ठभूमि",
                    "text": f"{clean_topic} के मुख्य सिद्धांतों और बुनियादी अवधारणाओं का विस्तृत विवरण।",
                    "bullets": [
                        "प्रारंभिक पृष्ठभूमि और आधुनिक संदर्भ।",
                        "वर्तमान परिदृश्य में इसकी प्रासंगिकता।",
                        "मुख्य तकनीकी स्तंभ और उद्देश्य।"
                    ]
                },
                {
                    "heading": "२. मुख्य तकनीकी घटक",
                    "text": f"{clean_topic} की कार्यप्रणाली और प्रणालीगत वास्तुकला।",
                    "bullets": [
                        "आर्किटेक्चर के प्रमुख अंग और उनकी भूमिकाएं।",
                        "डेटा प्रवाह और अंतर-घटक संचार।",
                        "दक्षता एवं प्रदर्शन मानक।"
                    ]
                },
                {
                    "heading": "३. अनुप्रयोग एवं उपयोग के क्षेत्र",
                    "text": f"{clean_topic} के व्यावहारिक और औद्योगिक अनुप्रयोग।",
                    "bullets": [
                        "वास्तविक दुनिया में सफल क्रियान्वयन।",
                        "दक्षता में सुधार और समय की बचत।",
                        "भविष्य के विस्तार की संभावनाएं।"
                    ]
                },
                {
                    "heading": "४. निष्कर्ष एवं आगामी दिशा",
                    "text": f"{clean_topic} के समग्र प्रभाव और भविष्य की रणनीतियों का सारांश।",
                    "bullets": [
                        "मुख्य उपलब्धियों का संक्षिप्त सारांश।",
                        "दीर्घकालिक लाभ और अवसर।",
                        "आगे के अनुसंधान एवं विकास के बिंदु।"
                    ]
                }
            ]
        }

    if language.lower() in ("mr", "marathi"):
        return {
            "title": f"{clean_topic}: सविस्तर प्रकल्प अहवाल",
            "sections": [
                {
                    "heading": "१. प्रस्तावना आणि पार्श्वभूमी",
                    "text": f"{clean_topic} या विषयाचे मूलभूत पैलू आणि उद्दिष्टे स्पष्ट करणारा विभाग.",
                    "bullets": [
                        "प्रकल्पाची पार्श्वभूमी आणि गरज.",
                        "आधुनिक काळातील वाढती उपयुक्तता.",
                        "प्रणालीचे मुख्य उद्दिष्टे."
                    ]
                },
                {
                    "heading": "२. मुख्य वैशिष्ट्ये आणि कार्यपद्धती",
                    "text": f"{clean_topic} ची तांत्रिक रचना आणि कार्यप्रणालीचा तपशील.",
                    "bullets": [
                        "तांत्रिक घटकांची रचना आणि सहकार्य.",
                        "डेटा व्यवस्थापन आणि वेगवान प्रक्रिया.",
                        "उच्च अचूकता आणि सुरक्षा मानक."
                    ]
                },
                {
                    "heading": "३. व्यावहारिक वापर आणि फायदे",
                    "text": f"{clean_topic} मुळे दैनंदिन आणि औद्योगिक स्तरावर मिळणारे प्रमुख फायदे.",
                    "bullets": [
                        "कार्यक्षमतेत झालेली भरीव वाढ.",
                        "वेळेची आणि श्रमाची प्रभावी बचत.",
                        "वापरकर्त्यासाठी सुलभ आणि विश्वासार्ह अनुभव."
                    ]
                },
                {
                    "heading": "४. निष्कर्ष आणि भावी दिशा",
                    "text": f"{clean_topic} चा एकूण प्रभाव आणि भविष्यातील विकासाच्या संधी.",
                    "bullets": [
                        "प्रकल्पाच्या यशाचा अंतिम आढावा.",
                        "दीर्घकालीन परिणाम आणि संधी.",
                        "पुढील सुधारणांचे नियोजन."
                    ]
                }
            ]
        }

    # Default English outline
    return {
        "title": f"{clean_topic.title()}: Strategic Analysis",
        "sections": [
            {
                "heading": "1. Executive Summary",
                "text": f"This report delivers a strategic analysis of {clean_topic}, outlining essential methodologies and target capabilities.",
                "bullets": [
                    f"Comprehensive architectural foundations of {clean_topic}.",
                    "Key operational priorities and delivery milestones.",
                    "System performance, security, and scalability metrics."
                ]
            },
            {
                "heading": "2. Core Principles and Methodology",
                "text": f"The technical architecture governing {clean_topic} emphasizes decoupled modular design and high reliability.",
                "bullets": [
                    "Strict separation of concerns across functional layers.",
                    "Standardized interface contracts ensuring zero regression.",
                    "Optimized data flow for real-time responsiveness."
                ]
            },
            {
                "heading": "3. Implementation Highlights",
                "text": f"Practical execution demonstrates high throughput and measurable performance improvements across workflows.",
                "bullets": [
                    "Direct integration with production automation pipelines.",
                    "Resilient error recovery and graceful exception handling.",
                    "Validated output conforming to publication standards."
                ]
            },
            {
                "heading": "4. Comparative Assessment",
                "text": f"Evaluation against industry standards confirms significant advantages in fidelity, latency, and adaptability.",
                "bullets": [
                    "Sub-second processing and generation cycles.",
                    "Native cross-lingual and multilingual support.",
                    "Zero data leakage and strict local sandboxing."
                ]
            },
            {
                "heading": "5. Strategic Recommendations",
                "text": f"Key initiatives and forward-looking milestones for scaling {clean_topic} into operational maturity.",
                "bullets": [
                    "Continuous automated regression testing.",
                    "Expansion of multimodal capabilities and reach.",
                    "Long-term performance monitoring and optimization."
                ]
            }
        ]
    }


def _clean_json_text(raw_text: str) -> str:
    """Extract and sanitize JSON content from raw LLM output."""
    cleaned = raw_text.strip()
    # Strip markdown code fences if present
    if "```" in cleaned:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
        if match:
            cleaned = match.group(1).strip()
    return cleaned


def _request_gemini_outline(topic: str, language: str) -> Optional[Dict[str, Any]]:
    """Request a structured JSON document outline from Google Gemini.

    Args:
        topic: Subject matter for the document.
        language: Language code ('en', 'hi', 'mr').

    Returns:
        Optional[Dict[str, Any]]: Parsed outline dictionary if successful.
    """
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or api_key == "your_gemini_api_key_here":
        return None

    model_name = os.getenv("GEMINI_MODEL") or os.getenv("MODEL_NAME") or "gemini-3.8-flash"

    lang_desc = "English"
    if language.lower() in ("hi", "hindi"):
        lang_desc = "Hindi in native Devanagari script"
    elif language.lower() in ("mr", "marathi"):
        lang_desc = "Marathi in native Devanagari script"

    prompt = (
        f"You are an expert technical author. Create a comprehensive, professional document outline about '{topic}'. "
        f"Language requirement: You MUST write the entire document in {lang_desc}. "
        f"Output ONLY a raw, valid JSON object with exact keys: 'title' (string), and 'sections' (list of 4 to 6 objects). "
        f"Each section object MUST contain: 'heading' (string), 'text' (1-2 explanatory sentences), and 'bullets' (list of 3-4 bullet strings). "
        f"Do NOT wrap in markdown explanation. Return pure JSON."
    )

    try:
        from google import genai
        client = genai.Client(api_key=api_key)

        for attempt in range(2):  # Retry once if invalid
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )
                raw_text = response.text or ""
                cleaned = _clean_json_text(raw_text)
                parsed = json.loads(cleaned)

                if isinstance(parsed, dict) and "title" in parsed and "sections" in parsed:
                    if isinstance(parsed["sections"], list) and len(parsed["sections"]) >= 3:
                        return parsed
            except Exception as parse_err:
                logger.warning("Gemini outline parse attempt %d failed: %s", attempt + 1, parse_err)

    except Exception as exc:
        logger.warning("Gemini API call failed for outline: %s", exc)

    return None


def _request_groq_outline(topic: str, language: str) -> Optional[Dict[str, Any]]:
    """Request a structured JSON document outline from Groq Cloud LPU as high-speed fallback."""
    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    if not groq_key or groq_key == "your_groq_api_key_here":
        return None

    lang_desc = "English"
    if language.lower() in ("hi", "hindi"):
        lang_desc = "Hindi in native Devanagari script"
    elif language.lower() in ("mr", "marathi"):
        lang_desc = "Marathi in native Devanagari script"

    prompt = (
        f"Create a professional document outline for topic '{topic}' in {lang_desc}. "
        f"Return ONLY valid JSON with 'title' and 'sections' (4-6 items with 'heading', 'text', 'bullets')."
    )

    try:
        from groq import Groq
        client = Groq(api_key=groq_key)
        completion = client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1024,
            response_format={"type": "json_object"},
        )
        content = completion.choices[0].message.content or ""
        parsed = json.loads(_clean_json_text(content))
        if isinstance(parsed, dict) and "title" in parsed and "sections" in parsed:
            return parsed
    except Exception as groq_err:
        logger.warning("Groq outline fallback failed: %s", groq_err)

    return None


def generate_outline(topic: str, language: str = "en") -> Dict[str, Any]:
    """Generate a structured document outline using Gemini, Groq, or resilient fallback.

    Args:
        topic: Document subject.
        language: Language code ('en', 'hi', 'mr').

    Returns:
        Dict[str, Any]: Validated outline with 'title' and 'sections'.
    """
    # 1. Try Gemini
    outline = _request_gemini_outline(topic, language)
    if outline:
        return outline

    # 2. Try Groq LPU fallback
    outline = _request_groq_outline(topic, language)
    if outline:
        return outline

    # 3. Deterministic high-quality multilingual fallback
    logger.info("Using built-in structured outline generator for '%s' (%s)", topic, language)
    return _build_fallback_outline(topic, language)


def create_document(
    topic: str,
    kind: str = "pdf",
    theme: str = "clean_light",
    language: str = "en",
    out_dir: str = "workspace",
    auto_open: bool = False,
) -> str:
    """Generate a complete, professionally formatted document from a single topic directive.

    Implements Vidhita's Day 5 milestone:
    1. Generates 4-6 section structured outline in the requested language (en, hi, mr).
    2. Uses TrueType Noto Sans Devanagari fonts for Hindi/Marathi text.
    3. Renders into PDF, DOCX, or 16:9 PPTX.
    4. Automatically saves into out_dir and optionally launches on desktop.

    Args:
        topic: Subject or prompt (e.g. 'Solar Energy', 'AI in Healthcare', 'प्रकल्प व्यवस्थापन').
        kind: Document format ('pdf', 'docx', 'pptx', 'presentation', 'word'). Default is 'pdf'.
        theme: Theme style ('clean_light', 'dark_pro', 'colourful'). Default is 'clean_light'.
        language: Language ('en', 'hi', 'mr'). Default is 'en'.
        out_dir: Directory where the document will be saved (default 'workspace').
        auto_open: Whether to automatically launch the file on Windows desktop.

    Returns:
        str: Absolute or resolved path to the created document file.

    Raises:
        ValueError: If topic is empty or kind is unsupported.
    """
    clean_topic = topic.strip()
    if not clean_topic:
        raise ValueError("Document topic cannot be empty.")

    clean_kind = kind.lower().strip()
    if clean_kind in ("presentation", "slides", "deck", "powerpoint"):
        clean_kind = "pptx"
    elif clean_kind in ("word", "doc", "document"):
        clean_kind = "docx"

    if clean_kind not in ("pdf", "docx", "pptx"):
        raise ValueError(f"Unsupported document kind '{kind}'. Must be 'pdf', 'docx', or 'pptx'.")

    # Generate or retrieve structured 4-6 section outline
    outline = generate_outline(clean_topic, language=language)
    doc_title: str = outline.get("title", clean_topic)
    sections: List[Dict[str, Any]] = outline.get("sections", [])

    if not sections:
        fallback = _build_fallback_outline(clean_topic, language=language)
        doc_title = fallback["title"]
        sections = fallback["sections"]

    # Dispatch to appropriate format maker
    if clean_kind == "pdf":
        return make_pdf(
            title=doc_title,
            sections=sections,
            theme=theme,
            out_dir=out_dir,
            auto_open=auto_open,
        )
    elif clean_kind == "docx":
        return make_docx(
            title=doc_title,
            sections=sections,
            theme=theme,
            out_dir=out_dir,
            auto_open=auto_open,
        )
    else:  # pptx
        return make_pptx(
            title=doc_title,
            sections=sections,
            theme=theme,
            out_dir=out_dir,
            auto_open=auto_open,
        )
