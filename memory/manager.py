"""
Episodic, Preference, and Custom Skill Memory Manager for JARVIS.

Provides:
- Prompt-injection sanitization for recalled memory
- Structured user preferences (default browser, voice, language, tone, user_name)
- Long-term memory facts and episodic recall
- Learned custom skills and workflows taught by the user
- Dynamic adaptive prompt context injection so JARVIS actively changes his speaking
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
    """Thread-safe persistent preferences, learned skills, and fact memory manager."""

    DEFAULT_PREFERENCES: Dict[str, Any] = {
        "user_name": "Sir",
        "speaking_style": "British witty, polite, sharp, and concise",
        "tone": "adaptive",
        "default_browser": "chrome",
        "voice_language": "en",
        "auto_speech": True,
        "llm_provider": "gemini",
        "tts_provider": "edge",
        "preferred_model": "gemini-3.5-flash-lite",
        "facts": {},
        "learned_skills": {},
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
                        if "facts" not in merged or not isinstance(merged["facts"], dict):
                            merged["facts"] = {}
                        if "learned_skills" not in merged or not isinstance(merged["learned_skills"], dict):
                            merged["learned_skills"] = {}
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

    # -------------------------------------------------------------------------
    # Personal Facts & Knowledge Retention
    # -------------------------------------------------------------------------

    def add_fact(self, key: str, fact: str) -> None:
        """Stores or updates a learned personal fact or preference."""
        clean_key = re.sub(r"[^\w\s-]", "", key.lower().strip().replace(" ", "_"))
        clean_fact = sanitize_memory_value(fact)
        if not clean_key or not clean_fact:
            return
        prefs = self.load()
        facts = prefs.setdefault("facts", {})
        facts[clean_key] = clean_fact
        self.save(prefs)

    def get_fact(self, key: str) -> Optional[str]:
        """Retrieves a stored fact by key."""
        clean_key = re.sub(r"[^\w\s-]", "", key.lower().strip().replace(" ", "_"))
        return self.load().get("facts", {}).get(clean_key)

    def remove_fact(self, key: str) -> bool:
        """Removes a stored fact. Returns True if deleted."""
        clean_key = re.sub(r"[^\w\s-]", "", key.lower().strip().replace(" ", "_"))
        prefs = self.load()
        facts = prefs.get("facts", {})
        if clean_key in facts:
            del facts[clean_key]
            self.save(prefs)
            return True
        return False

    def get_all_facts(self) -> Dict[str, str]:
        """Returns dictionary of all remembered user facts and preferences."""
        return dict(self.load().get("facts", {}))

    def clear_facts(self) -> None:
        """Clears all stored user facts."""
        prefs = self.load()
        prefs["facts"] = {}
        self.save(prefs)

    # -------------------------------------------------------------------------
    # Skill Learner & Custom Procedures
    # -------------------------------------------------------------------------

    def add_skill(
        self,
        name: str,
        trigger: str,
        steps: Any,
        description: str = "",
        raw_instruction: str = "",
    ) -> Dict[str, Any]:
        """Registers a new learned skill with associated trigger and action steps."""
        clean_name = re.sub(r"[^\w\s-]", "", name.lower().strip().replace(" ", "_"))
        clean_trigger = trigger.lower().strip()
        clean_desc = description.strip() or f"User-taught custom skill: {clean_name}"
        clean_raw = raw_instruction.strip() or str(steps)

        skill_entry = {
            "name": clean_name,
            "trigger": clean_trigger,
            "steps": steps,
            "description": clean_desc,
            "raw_instruction": clean_raw,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        prefs = self.load()
        skills = prefs.setdefault("learned_skills", {})
        skills[clean_name] = skill_entry
        self.save(prefs)
        return skill_entry

    def get_skill(self, name_or_trigger: str) -> Optional[Dict[str, Any]]:
        """Finds a learned skill by exact name or trigger phrase."""
        clean = name_or_trigger.lower().strip().replace(" ", "_")
        skills = self.load().get("learned_skills", {})
        if clean in skills:
            return skills[clean]
        raw_search = name_or_trigger.lower().strip()
        for skill in skills.values():
            if skill.get("trigger", "").lower() == raw_search or skill.get("name", "").lower() == raw_search:
                return skill
        return None

    def list_skills(self) -> List[Dict[str, Any]]:
        """Returns all registered learned skills."""
        return list(self.load().get("learned_skills", {}).values())

    def remove_skill(self, name: str) -> bool:
        """Removes a learned skill by name. Returns True if removed."""
        clean = name.lower().strip().replace(" ", "_")
        prefs = self.load()
        skills = prefs.get("learned_skills", {})
        if clean in skills:
            del skills[clean]
            self.save(prefs)
            return True
        return False

    def find_matching_skill(self, user_query: str) -> Optional[Dict[str, Any]]:
        """Finds a learned skill whose trigger matches the user utterance."""
        q = user_query.lower().strip()
        skills = self.load().get("learned_skills", {})
        for skill in skills.values():
            trigger = (skill.get("trigger") or "").lower().strip()
            if trigger and (trigger == q or trigger in q or q in trigger):
                return skill
            name = (skill.get("name") or "").lower().replace("_", " ")
            if name and (name == q or name in q):
                return skill
        return None

    # -------------------------------------------------------------------------
    # Dynamic Adaptive Prompt Context for Speech & Reasoning Adaptation
    # -------------------------------------------------------------------------

    def get_facts_context(self) -> str:
        """Returns sanitized facts formatted for LLM system prompt injection."""
        facts = self.get_all_facts()
        if not facts:
            return ""
        lines = [f"- {k}: {v}" for k, v in facts.items() if v]
        return "\nUser Profile & Facts:\n" + "\n".join(lines)

    def get_adaptive_prompt_context(self) -> str:
        """Compiles learned user memory, speaking style, facts, and custom skills
        into a structured directive injected directly into the Gemini system instruction.
        This forces JARVIS to dynamically reflect everything he has learned in his speaking.
        """
        prefs = self.load()
        user_name = prefs.get("user_name", "Sir")
        style = prefs.get("speaking_style", "British witty, polite, sharp, and concise")
        facts = prefs.get("facts", {})
        skills = prefs.get("learned_skills", {})

        sections: List[str] = [
            "### ADAPTIVE MEMORY & LEARNED PERSONA PROTOCOL:",
            f"- Preferred Address: Address the user respectfully as '{user_name}'.",
            f"- Speaking Style & Cadence: {style}.",
        ]

        if facts:
            sections.append("### REMEMBERED USER FACTS & PREFERENCES:")
            for k, v in facts.items():
                clean_k = k.replace("_", " ").title()
                sections.append(f"  * {clean_k}: {v}")

        if skills:
            sections.append(f"### USER-TAUGHT CUSTOM SKILLS & PROCEDURES ({len(skills)} learned):")
            for s in skills.values():
                s_name = s.get("name", "")
                s_trig = s.get("trigger", s_name)
                s_desc = s.get("description") or s.get("raw_instruction", "")
                sections.append(f"  * '{s_name}' (Trigger: '{s_trig}'): {s_desc}")

        sections.append(
            f"CRITICAL PERSONALIZATION MANDATE: You MUST actively demonstrate in your phrasing that you remember the user's learned facts, preferences, and custom skills. Always address them by their chosen title ('{user_name}') and honor their stated preferences throughout your speech."
        )

        return "\n".join(sections)


# Global singleton instance
preference_manager = PreferenceManager()
