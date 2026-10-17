# Jarvis AI Assistant - System Architecture & Interface Contract

This document defines the single source of truth for all modules, communication protocols, and code contracts. 
**Every developer and their Antigravity agent must adhere strictly to this specification.**

---

## 1. High-Level Architecture Overview

```
                        +----------------------------+
                        |        User Interface      |
                        | (React / Next.js HUD / Web)|  <-- Rohit
                        +--------------+-------------+
                                       |
                            WebSocket / REST (FastAPI)
                                       |
+---------------------+ <--------------+-------------> +---------------------+
|    Voice Engine     |                                |    Memory Engine    |
| (Wake Word, STT,TTS)|                                | (SQLite + Vector DB)|
|       Aryan         |                                |       Rohit         |
+----------+----------+                                +----------+----------+
           |                                                      ^
    Transcribed Text                                              |
           |                                              Read/Write Context
           v                                                      |
+-----------------------------------------------------------------+----------+
|                               Core Brain                                   |
|               (LLM Orchestrator, Prompt, Tool-Calling Loop)                |
|                                  Jay                                       |
+-------------------------------------+--------------------------------------+
                                      |
                            Executes via Tool Registry
                                      |
                                      v
                        +----------------------------+
                        |   System & Automation Tools|
                        | (Subprocess, Apps, Files)  |  <-- Abhijit
                        +----------------------------+
```

---

## 2. Module Ownership & Folder Boundaries

| Folder | Owner | Scope & Responsibility | Strict Rule |
| :--- | :--- | :--- | :--- |
| `core/` | **Jay** | LLM integration, prompt templates, agentic tool execution loop, coordinator | Only Jay modifies `core/` |
| `voice/` | **Aryan** | Microphone capture, Wake-word, Speech-to-Text (STT), Text-to-Speech (TTS) | Only Aryan modifies `voice/` |
| `tools/` | **Abhijit** | OS automation, file operations, app launching, system telemetry, safety guards | Only Abhijit modifies `tools/` |
| `memory/` | **Rohit** | SQLite persistence (notes, tasks, history) & Vector DB (RAG) | Only Rohit modifies `memory/` |
| `ui/` | **Rohit** | React/Next.js dashboard, HUD components, WebSocket client | Only Rohit modifies `ui/` |
| `tests/` | **All** | Unit tests for each respective module | Everyone writes tests for their tools/code |

---

## 3. The Tool Interface Contract (CRITICAL)

All tools implemented by **Abhijit** (and called by **Jay's Brain**) MUST follow this unified standard.

### 3.1 The Standard Tool Base Specification
Each tool is either:
1. A Python function decorated with `@jarvis_tool`, OR
2. A class inheriting from `BaseTool`.

We use Python typing and docstrings so LLMs can dynamically inspect parameters.

```python
# tools/base.py
from typing import Any, Callable, Dict, Optional
from pydantic import BaseModel
import inspect

class ToolResult(BaseModel):
    success: bool
    data: Any
    message: str

    def to_llm_string(self) -> str:
        """Format the result as a clear string for the LLM context."""
        status = "SUCCESS" if self.success else "FAILED"
        return f"[{status}] {self.message}\nData: {self.data}"

class BaseTool:
    """Base class for all Jarvis tools."""
    name: str
    description: str

    def run(self, **kwargs) -> ToolResult:
        raise NotImplementedError("Each tool must implement run()")

    def get_schema(self) -> Dict[str, Any]:
        """Returns JSON schema for OpenAI/Gemini function calling."""
        raise NotImplementedError()
```

### 3.2 Canonical Tool Example (Copy This Exactly)

```python
# tools/system_tools.py
import psutil
from tools.base import BaseTool, ToolResult

class GetSystemStatsTool(BaseTool):
    name = "get_system_stats"
    description = (
        "Retrieves current laptop telemetry including CPU usage percentage, "
        "RAM usage, and battery status. Takes no arguments."
    )

    def run(self) -> ToolResult:
        try:
            cpu_percent = psutil.cpu_percent(interval=0.5)
            ram = psutil.virtual_memory()
            battery = psutil.sensors_battery()

            battery_info = (
                f"{battery.percent}% ({'Plugged in' if battery.power_plugged else 'On Battery'})"
                if battery else "No battery detected (Desktop/Plugged)"
            )

            stats = {
                "cpu_usage_percent": cpu_percent,
                "ram_usage_percent": ram.percent,
                "ram_used_gb": round(ram.used / (1024 ** 3), 2),
                "ram_total_gb": round(ram.total / (1024 ** 3), 2),
                "battery": battery_info
            }
            return ToolResult(
                success=True,
                data=stats,
                message="System statistics retrieved successfully."
            )
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                message=f"Failed to fetch system stats: {str(e)}"
            )
```

---

## 4. Communication Contracts Between Modules

### 4.1 Voice -> Brain (Aryan to Jay)
- Voice emits clean, normalized text string: `user_text: str`.
- Brain receives text, yields or returns: `assistant_text: str`.
- Aryan calls: `brain.process_input(text: str) -> str` (or asynchronous generator `AsyncGenerator[str, None]` for streaming).

### 4.2 Brain -> Tools (Jay to Abhijit)
- Jay loads tools via `tools.registry.get_registered_tools()`.
- Jay passes the schema to LLM (Gemini / OpenAI function declaration).
- When LLM emits `tool_call(name="open_app", args={"app_name": "notepad"})`, Jay calls `registry.execute(name, args)`.
- The returned `ToolResult.to_llm_string()` is appended to LLM conversation messages.

### 4.3 Brain -> Memory (Jay to Rohit)
- Before querying LLM, Jay calls: `memory.get_relevant_context(query: str, limit=5) -> List[str]`.
- After conversation turn, Jay calls: `memory.save_interaction(role="user", content=...)` and `memory.save_interaction(role="assistant", content=...)`.

### 4.4 Backend Server -> UI (Jay/Rohit to Frontend)
- Communication via WebSocket (`ws://127.0.0.1:8000/ws/jarvis`).
- Event payload format:
```json
{
  "type": "agent_state", // "listening" | "thinking" | "executing_tool" | "speaking" | "idle"
  "payload": {
    "tool_name": "get_system_stats",
    "text_chunk": "Your CPU usage is currently 14%...",
    "error": null
  }
}
```
