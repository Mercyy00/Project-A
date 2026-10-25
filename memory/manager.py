"""
Episodic and Preference Memory Manager for JARVIS.

Ported from Mark LVI's memory/memory_manager.py.
Provides:
- Prompt-injection sanitization for recalled memory
- Structured user preferences (default browser, voice, language, tone)
- Long-term memory facts and episodic recall
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional

_lock = Lock()
_MEMORY_FILE = Path("memory") / "preferences.json"


def sanitize_memory_value(val: str) -> str:
    """Sanitizes a memory value before injecting into LLM context to prevent prompt injection."""
    if not val or not isinstance(val, str):
        return ""
    # Strip dangerous control characters
    val = re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", "", val)
    # Replace newlines with spaces to avoid injecting fake dialogue turns
    val = val.replace("\r", " ").replace("\n", " ")
    # Defang fake role markers
    val = re.sub(r"(?i)\b(system|assistant|user)\s*:\s*", r"[\1]: ", val)
    # Defang tag markers
    val = val.replace("<<<", "<<").replace(">>>", ">>")
    return re.sub(r"\s+", " ", val).strip()


class PreferenceManager:
    """Thread-safe persistent preferences and fact memory manager."""

    DEFAULT_PREFERENCES: Dict[str, Any] = {
        "user_name": "Sir",
        "default_browser": "chrome",
        "voice_language": "en",
        "auto_speech": True,
        "llm_provider": "gemini",
        "tts_provider": "edge",
        "preferred_model": "gemini-3.5-flash-lite",
        "facts": {}
    }

    def __init__(self, storage_path: Optional[Path] = None) -> None:
        self.path = storage_path or _MEMORY_FILE
        self._ensure_file()

    def _ensure_file(self) -> None:
        if not self.path.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.save(self.DEFAULT_PREFERENCES)

    def load(self) -> Dict[str, Any]:
        with _lock:
            try:
                if self.path.exists():
                    with open(self.path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        merged = dict(self.DEFAULT_PREFERENCES)
                        merged.update(data)
                        return merged
            except Exception:
                pass
            return dict(self.DEFAULT_PREFERENCES)

    def save(self, data: Dict[str, Any]) -> None:
        with _lock:
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"Warning: Failed to save preferences: {e}")

    def get_preference(self, key: str, default: Any = None) -> Any:
        prefs = self.load()
        return prefs.get(key, default)

    def set_preference(self, key: str, value: Any) -> None:
        prefs = self.load()
        prefs[key] = value
        self.save(prefs)

    def add_fact(self, key: str, fact: str) -> None:
        prefs = self.load()
        facts = prefs.setdefault("facts", {})
        facts[key] = sanitize_memory_value(fact)
        self.save(prefs)

    def get_facts_context(self) -> str:
        """Returns sanitized facts formatted for LLM system prompt injection."""
        facts = self.load().get("facts", {})
        if not facts:
            return ""
        lines = [f"- {k}: {v}" for k, v in facts.items() if v]
        return "\nUser Profile & Facts:\n" + "\n".join(lines)


# Global singleton instance
preference_manager = PreferenceManager()
