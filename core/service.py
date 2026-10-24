"""Service layer for Project Jarvis Core.

Exposes asynchronous execution wrapper around JarvisBrain for consumption by
WebSocket HUD (Rohit), Telegram bot (Trupti), and Voice engines.
Runs synchronous LLM calls in worker threads to prevent event loop starvation.
Supports sub-100ms cancellation tokens for full-duplex voice barge-in and HUD aborts.
"""

from __future__ import annotations

import asyncio
import threading
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

from core.brain import JarvisBrain

# Module-level singleton instance for persistent multi-turn conversations
_brain_instance: Optional[JarvisBrain] = None

# Active cancellation token tracking for full-duplex stream interruption
_current_cancel_event: Optional[BridgedCancelEvent] = None


class BridgedCancelEvent:
    """Thread-safe cancellation token adapter supporting both threading and asyncio events."""

    def __init__(self, external_event: Optional[Any] = None) -> None:
        self._thread_event: threading.Event = threading.Event()
        self._external: Optional[Any] = external_event

    def is_set(self) -> bool:
        """Check if either internal or external cancellation token has fired."""
        if self._thread_event.is_set():
            return True
        if self._external is not None and hasattr(self._external, "is_set"):
            return bool(self._external.is_set())
        return False

    def set(self) -> None:
        """Trigger cancellation immediately across all attached tokens."""
        self._thread_event.set()
        if self._external is not None and hasattr(self._external, "set"):
            try:
                self._external.set()
            except Exception:
                pass

    def wait(self, timeout: Optional[float] = None) -> bool:
        """Wait for cancellation event or timeout."""
        return self._thread_event.wait(timeout)


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
    global _brain_instance, _current_cancel_event
    _current_cancel_event = None
    if _brain_instance is not None:
        _brain_instance.reset()


def interrupt_generation() -> bool:
    """Immediately interrupts any in-progress generation in JarvisBrain or handle_text_stream.

    Can be triggered by WebSocket client ({"action": "interrupt"}),
    Voice engine barge-in listener, or CLI Ctrl+C.

    Returns:
        bool: True if an active stream or brain session was signaled to abort, False otherwise.
    """
    global _current_cancel_event
    signaled: bool = False
    if _current_cancel_event is not None and not _current_cancel_event.is_set():
        _current_cancel_event.set()
        signaled = True

    brain: JarvisBrain = get_brain()
    if brain.interrupt():
        signaled = True

    return signaled


def abort_stream() -> bool:
    """Alias for interrupt_generation()."""
    return interrupt_generation()


async def handle_text(
    text: str,
    source: str = "cli",
    mode: str = "normal",
    cancel_event: Optional[Any] = None,
) -> Dict[str, Any]:
    """Process incoming text directive asynchronously in a background thread.

    Conforms strictly to ARCHITECTURE.md and Catch-Up Plan interface contract.

    Args:
        text: User query, spoken transcription, or UI message.
        source: Source channel identifier ('cli', 'ws', 'telegram', 'voice').
        mode: Operating mode ('normal', 'silent', 'attentive', 'combat').
        cancel_event: Optional cancellation token to abort generation.

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
        # Execute synchronous LLM chat in a worker thread to keep asyncio event loop responsive
        try:
            if cancel_event is not None:
                response_text: str = await asyncio.to_thread(brain.chat, cleaned, mode, cancel_event)
            else:
                response_text: str = await asyncio.to_thread(brain.chat, cleaned, mode)
        except TypeError:
            response_text: str = await asyncio.to_thread(brain.chat, cleaned, mode)
        tool_steps: List[str] = list(brain.last_tool_steps)

        is_interrupted = (
            (cancel_event is not None and hasattr(cancel_event, "is_set") and cancel_event.is_set())
            or brain.is_interrupted
        )

        if not is_interrupted:
            # Persist turn to SQLite long-term memory vault (Day 4 deliverable)
            try:
                from memory.storage import MemoryManager
                mem = MemoryManager()
                await mem.save_interaction("user", cleaned)
                await mem.save_interaction("assistant", response_text)
            except Exception:
                pass

        return {
            "text": response_text if not is_interrupted else "[Interrupted]",
            "tool_steps": tool_steps,
            "source": source,
            "interrupted": is_interrupted,
        }
    except Exception as exc:
        error_msg: str = f"Subsystem execution error: {str(exc)}"
        return {
            "text": error_msg,
            "tool_steps": [],
            "source": source,
        }


async def handle_text_stream(
    text: str,
    source: str = "cli",
    mode: str = "normal",
    cancel_event: Optional[Any] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """Process incoming text directive with asynchronous streaming token events.

    Designed for consumption by WebSocket HUD (Rohit), CLI, and Voice engines.
    Supports sub-100ms cancellation tokens for full-duplex voice barge-in
    and Web HUD interruption signals.

    Yields:
        Dict[str, Any]:
            - Token chunk event: {"type": "chunk", "text": "..."}
            - Completion event: {"type": "done", "text": full_text, "tool_steps": [...], "source": source}
            - Interrupted event: {"type": "interrupted", "text": partial_text, "source": source}
    """
    cleaned: str = text.strip() if text else ""
    if not cleaned:
        default_resp = "I am listening. How can I assist you?"
        yield {"type": "chunk", "text": default_resp}
        yield {
            "type": "done",
            "text": default_resp,
            "tool_steps": [],
            "source": source,
        }
        return

    global _current_cancel_event
    active_cancel = BridgedCancelEvent(cancel_event)
    _current_cancel_event = active_cancel

    brain: JarvisBrain = get_brain()
    queue: asyncio.Queue[Tuple[str, Any]] = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def sync_worker() -> None:
        try:
            try:
                stream_iter = brain.chat_stream(cleaned, mode=mode, cancel_event=active_cancel)
            except TypeError:
                stream_iter = brain.chat_stream(cleaned, mode=mode)
            for chunk in stream_iter:
                if active_cancel.is_set():
                    break
                loop.call_soon_threadsafe(queue.put_nowait, ("chunk", chunk))

            if active_cancel.is_set():
                loop.call_soon_threadsafe(queue.put_nowait, ("interrupted", None))
            else:
                loop.call_soon_threadsafe(queue.put_nowait, ("done", None))
        except Exception as exc:
            loop.call_soon_threadsafe(queue.put_nowait, ("error", exc))

    fut = asyncio.create_task(asyncio.to_thread(sync_worker))

    accumulated_chunks: List[str] = []
    was_interrupted: bool = False
    try:
        while True:
            event_type, payload = await queue.get()
            if event_type == "chunk":
                accumulated_chunks.append(payload)
                yield {"type": "chunk", "text": payload}
            elif event_type == "done":
                break
            elif event_type == "interrupted":
                was_interrupted = True
                break
            elif event_type == "error":
                err_text = f"Subsystem execution error: {str(payload)}"
                accumulated_chunks.append(err_text)
                yield {"type": "chunk", "text": err_text}
                break
    finally:
        if _current_cancel_event is active_cancel:
            _current_cancel_event = None
        await fut

    full_text = "".join(accumulated_chunks)
    if was_interrupted:
        yield {
            "type": "interrupted",
            "text": full_text,
            "source": source,
        }
        return

    tool_steps = list(brain.last_tool_steps)

    # Persist turn to SQLite long-term memory vault (Day 4 deliverable)
    try:
        from memory.storage import MemoryManager
        mem = MemoryManager()
        await mem.save_interaction("user", cleaned)
        await mem.save_interaction("assistant", full_text)
    except Exception:
        pass

    yield {
        "type": "done",
        "text": full_text,
        "tool_steps": tool_steps,
        "source": source,
    }
