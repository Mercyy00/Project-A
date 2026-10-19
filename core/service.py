"""Service layer for Project Jarvis Core.

Exposes asynchronous execution wrapper around JarvisBrain for consumption by
WebSocket HUD (Rohit), Telegram bot (Trupti), and Voice engines.
Runs synchronous LLM calls in worker threads to prevent event loop starvation.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from core.brain import JarvisBrain

# Module-level singleton instance for persistent multi-turn conversations
_brain_instance: Optional[JarvisBrain] = None


def get_brain() -> JarvisBrain:
    """Retrieve or lazily initialize the shared JarvisBrain singleton.

    Returns:
        JarvisBrain: Shared brain instance.
    """
    global _brain_instance
    if _brain_instance is None:
        _brain_instance = JarvisBrain()
    return _brain_instance


def reset_brain() -> None:
    """Reset the conversation state and reinitialize the brain session."""
    global _brain_instance
    if _brain_instance is not None:
        _brain_instance.reset()


async def handle_text(text: str, source: str = "cli") -> Dict[str, Any]:
    """Process incoming text directive asynchronously in a background thread.

    Conforms strictly to ARCHITECTURE.md and Catch-Up Plan interface contract.

    Args:
        text: User query, spoken transcription, or UI message.
        source: Source channel identifier ('cli', 'ws', 'telegram', 'voice').

    Returns:
        Dict[str, Any] containing:
            - 'text': Assistant response text (str)
            - 'tool_steps': List of tool action strings executed during turn (list[str])
            - 'source': Input channel identifier (str)
    """
    cleaned: str = text.strip() if text else ""
    if not cleaned:
        return {
            "text": "I am listening. How can I assist you?",
            "tool_steps": [],
            "source": source,
        }

    try:
        brain: JarvisBrain = get_brain()
        # Execute synchronous Gemini chat in a worker thread to keep asyncio event loop responsive
        response_text: str = await asyncio.to_thread(brain.chat, cleaned)
        tool_steps: List[str] = list(brain.last_tool_steps)

        return {
            "text": response_text,
            "tool_steps": tool_steps,
            "source": source,
        }
    except Exception as exc:
        error_msg: str = f"Subsystem execution error: {str(exc)}"
        return {
            "text": error_msg,
            "tool_steps": [],
            "source": source,
        }
