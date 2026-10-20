"""Language detection and configuration utilities for JARVIS Voice STT.

Supports detection among English ('en'), Hindi ('hi'), and Marathi ('mr').
Uses langdetect alongside Devanagari script heuristics to distinguish
Hindi and Marathi, while returning 'en' for Roman-script text per project rules.
"""

from __future__ import annotations

import re
from typing import Final
import langdetect
from langdetect.detector_factory import DetectorFactory

# Set seed for deterministic langdetect results
DetectorFactory.seed = 0

SUPPORTED_LANGUAGES: Final[dict[str, str]] = {
    "en": "English",
    "hi": "Hindi",
    "mr": "Marathi",
}

# Standard language codes mapping for backward compatibility and TTS/STT usage
LANGUAGE_CODES: Final[dict[str, str]] = {
    "english": "en-US",
    "en": "en-US",
    "hindi": "hi-IN",
    "hi": "hi-IN",
    "marathi": "mr-IN",
    "mr": "mr-IN",
}

# Distinctive Marathi lexical and grammatical tokens
MARATHI_MARKERS: Final[set[str]] = {
    "आहे", "आहेत", "नाही", "नाहीत", "काय", "कसं", "कसे", "कसा", "करा", "करावे",
    "करतो", "करते", "करतात", "हो", "नमस्कार", "धन्यवाद", "पुन्हा", "सांग",
    "सांगा", "तुम्ही", "आम्ही", "आपण", "माझे", "माझा", "माझी", "तुझे", "तुझा",
    "झाले", "झाला", "झाली", "कशासाठी", "कोण", "कधी", "कुठे", "वेळ", "आज",
    "उद्या", "काल", "कृपया", "चांगले", "नवीन", "नको", "बघ", "बघा"
}

# Distinctive Hindi lexical and grammatical tokens
HINDI_MARKERS: Final[set[str]] = {
    "है", "हैं", "नहीं", "क्या", "कैसे", "कैसा", "कैसी", "करो", "करें", "करता",
    "करती", "करते", "नमस्ते", "शुक्रिया", "धन्यवाद", "बताओ", "बताइए", "आप",
    "हम", "मेरा", "मेरी", "मेरे", "तेरा", "तेरी", "हुआ", "हुई", "हुए",
    "किसलिए", "कौन", "कब", "कहाँ", "समय", "आज", "कल", "कृपया", "अच्छा", "नया"
}

DEVANAGARI_REGEX: Final[re.Pattern[str]] = re.compile(r"[\u0900-\u097F]")
ROMAN_REGEX: Final[re.Pattern[str]] = re.compile(r"[A-Za-z]")


def is_roman_script(text: str) -> bool:
    """Return True if text primarily consists of Roman/Latin characters."""
    clean_text = text.strip()
    if not clean_text:
        return True
    
    devanagari_count = len(DEVANAGARI_REGEX.findall(clean_text))
    roman_count = len(ROMAN_REGEX.findall(clean_text))

    # If there are no Devanagari characters, treat as Roman script
    if devanagari_count == 0:
        return True

    # If Roman characters dominate heavily
    return roman_count > devanagari_count


def _detect_devanagari_language(text: str) -> str:
    """Distinguish whether Devanagari text is Marathi ('mr') or Hindi ('hi')."""
    # 1. Letter 'ळ' (U+0933) is exclusively used in Marathi (not Standard Hindi)
    if "\u0933" in text:
        return "mr"

    tokens = set(re.findall(r"[\u0900-\u097F]+", text))
    marathi_matches = len(tokens.intersection(MARATHI_MARKERS))
    hindi_matches = len(tokens.intersection(HINDI_MARKERS))

    if marathi_matches > hindi_matches:
        return "mr"
    if hindi_matches > marathi_matches:
        return "hi"

    # Use langdetect as statistical classifier
    try:
        detected = langdetect.detect(text)
        if detected == "mr":
            return "mr"
        if detected == "hi":
            return "hi"
    except Exception:
        pass

    # Default fallback for Devanagari if ambiguous: Marathi if any Marathi marker exists, else Hindi
    if marathi_matches > 0:
        return "mr"
    return "hi"


def detect_language(text: str) -> str:
    """Detect the language of the given text.

    Per JARVIS specification:
    - Roman-script text (English or transliterated Hinglish/Marathi in Latin alphabet) returns 'en'.
    - Devanagari script returns 'hi' (Hindi) or 'mr' (Marathi).
    - Empty or non-alphabetic text defaults to 'en'.

    Args:
        text: The string to analyze.

    Returns:
        One of 'en', 'hi', or 'mr'.
    """
    if not isinstance(text, str):
        return "en"

    clean_text = text.strip()
    if not clean_text:
        return "en"

    # If text is Roman-script (Latin alphabet), always return 'en' per spec
    if is_roman_script(clean_text):
        return "en"

    # If Devanagari characters are present, classify between 'hi' and 'mr'
    return _detect_devanagari_language(clean_text)


def get_language_code(language: str) -> str:
    """Return the BCP-47 language tag (e.g., 'mr-IN', 'hi-IN', 'en-US').

    Args:
        language: Language name or short code ('en', 'hi', 'mr', 'marathi', etc.).

    Returns:
        BCP-47 language code string.
    """
    normalized = language.strip().lower()
    if normalized in LANGUAGE_CODES:
        return LANGUAGE_CODES[normalized]
    raise ValueError(
        f"Unsupported language '{language}'. "
        f"Supported options: {', '.join(sorted(LANGUAGE_CODES.keys()))}"
    )


def get_supported_languages() -> list[str]:
    """Return list of supported language short codes."""
    return list(SUPPORTED_LANGUAGES.keys())


# Personality and conversational phrases across all three supported languages
PERSONALITY_LINES: Final[dict[str, dict[str, str]]] = {
    "en": {
        "one_moment": "One moment, please.",
        "didnt_catch": "Sorry, I didn't catch that. Could you please repeat?",
        "listening": "Listening... Please speak now.",
        "online": "Jarvis is online and ready.",
    },
    "hi": {
        "one_moment": "कृपया एक पल रुकिए।",
        "didnt_catch": "माफ़ कीजिए, मुझे सुनाई नहीं दिया। क्या आप दोबारा कह सकते हैं?",
        "listening": "सुन रहा हूँ... कृपया बोलिए।",
        "online": "जार्विस ऑनलाइन और तैयार है।",
    },
    "mr": {
        "one_moment": "कृपया एक क्षण थांबा.",
        "didnt_catch": "माफ करा, मला नीट ऐकू आले नाही. कृपया पुन्हा सांगाल का?",
        "listening": "ऐकत आहे... कृपया बोला.",
        "online": "जार्विस ऑनलाइन आणि सज्ज आहे.",
    },
}


def get_personality_phrase(key: str, lang: str = "en") -> str:
    """Return a localized personality phrase in the target language.

    Args:
        key: Phrase identifier ('one_moment', 'didnt_catch', 'listening', 'online').
        lang: Language short code ('en', 'hi', 'mr'). Defaults to 'en'.

    Returns:
        The localized phrase string.
    """
    clean_lang = lang if lang in PERSONALITY_LINES else "en"
    phrases = PERSONALITY_LINES[clean_lang]
    return phrases.get(key, PERSONALITY_LINES["en"].get(key, ""))

