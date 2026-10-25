# Implementation Plan: Jay's Core Engine & Team Integration (Day 7)

## Overview
As Team Lead and Core Brain architect, today's focus is two-fold:
1. **GitHub Team Status & Branch Synchronization:** Audit git history across all 4 engineering pairs, verify and integrate unmerged commits from Abhijit's `feature/abhijit-tools` into `main`, and verify full cross-module interoperability.
2. **Core Brain Universal Tool Synchronization:** Bridge the gap between `tools.registry.TOOL_REGISTRY` (38 tools) and `core.brain.JarvisBrain._discover_tools()` (previously 29 tools) so that Google Gemini and Groq function calling can autonomously invoke document creation (PDF, DOCX, PPTX), Telegram messaging, screen automation, visual code diagnosis, and Windows settings.

---

## Deliverables & Architectural Decisions

### 1. Tool Coverage Parity
- **Problem:** When Vidhita, Trupti, and Aryan merged document, messaging, and advanced vision tools, `core/brain.py` was hardcoded to only 29 system tools. As a result, requests like "Create a PDF report on AI" or "Send a Telegram message" could not trigger function calling under Gemini.
- **Solution:** Added exact function wrappers with typed arguments, comprehensive docstrings, and error handling for all 9 newly registered tools:
  - `open_file(file_path: str)`
  - `open_settings_page(page: str)`
  - `do_on_screen(goal: str, max_steps: int = 5)`
  - `explain_code_on_screen(task: str, active_window: bool)`
  - `create_pdf(title: str, sections: list, theme: str, auto_open: bool)`
  - `create_docx(title: str, sections: list, theme: str, auto_open: bool)`
  - `create_pptx(title: str, sections: list, theme: str, auto_open: bool)`
  - `create_document(topic: str, kind: str, language: str, theme: str, auto_open: bool)`
  - `send_telegram(text: str)`
- **Total Tool Count:** 38 tools registered and exposed to LLM.

### 2. Abhijit Tools Branch Integration
- Reviewed Abhijit's latest commits:
  - `f0249c4`: Safe workspace Python execution (`tools/code_tools.py`)
  - `29193e0`: Kill-switch hotkey (`Ctrl+Alt+Q`) and action log auditing (`tools/guard.py`)
  - `2de171c`: App allowlist, website shortcuts, and Windows settings launcher (`tools/system_tools.py`)
- Verified 61/61 unit tests in `tests/test_code_tools.py`, `tests/test_guard.py`, and `tests/test_system_tools.py`.
- Merged cleanly into `main`.

### 3. Safety & Environment Hardening
- Added `pynput>=1.7.6` to `requirements.txt`.
- Isolated `.env` variable bleed (`GEMINI_MODEL`, `MODEL_NAME`) in `tests/test_brain.py`.
- Verified test suite passes hermetically across modules.


---

# Week 2 Plan: Autonomous Agentic Intelligence & Proactive Voice Assistant (Days 8–14)

## Overview & Strategic Objectives
In Week 2, Project JARVIS transitions from an interactive reactive assistant into an autonomous proactive agent:
1. **Full-Duplex Voice & Interruption (Day 8):** Continuous VAD and Barge-In detection that mutes TTS and halts LLM generation immediately upon user speech.
2. **Semantic Vector Memory & Code RAG (Day 9):** Persistent ChromaDB integration to recall user facts and index local workspace source code.
3. **Multi-Step ReAct Planner (Day 10):** Structured task decomposition allowing JARVIS to plan, chain up to 8 tools, observe intermediate states, and self-correct.
4. **Real-Time Web Intelligence (Day 11):** Clean article scraping, table parsing, live web research, and citation attribution.
5. **Proactive Watchdog & Alerts (Day 12):** Background scheduler for hardware health warnings, scheduled reminders, and proactive Telegram push notifications.
6. **Air-Gapped Offline LLM Fallback (Day 13):** Triple-engine failover (`Groq LPU ➔ Gemini ➔ Local Ollama`) with local Whisper and offline tools.
7. **Week 2 Release 2.0 Packaging (Day 14):** 350+ unit tests, multi-channel stress tests, and one-click installer.

---

## Day 8 Implementation: Full-Duplex Stream Cancellation & Abort Mechanics (Core Brain)

### Architectural Design
1. **Thread-Safe Cancellation Bridging (`BridgedCancelEvent`):**
   - Implemented in `core/service.py` to seamlessly connect `asyncio.Event` (used by FastAPI/WebSocket and asyncio event loops) with `threading.Event` (used in worker threads running synchronous LLM generators).
   - Exposes `.is_set()`, `.set()`, and `.wait(timeout)` with zero CPU overhead.

2. **Core Brain Generation Abort Protocol (`core/brain.py`):**
   - Added `interrupt()`, `abort()`, and `is_interrupted` property to `JarvisBrain`.
   - Updated `chat_stream()`, `stream_chat()`, `_chat_stream_with_groq()`, and `_chat_stream_with_gemini()` to accept optional `cancel_event`.
   - Verified that token generation halts in <20ms upon cancellation, closing stream sockets where applicable and preventing partial truncated turns from polluting history or memory.

3. **Service Layer API (`core/service.py`):**
   - Exposed `interrupt_generation()` and `abort_stream()`.
   - When cancelled, `handle_text_stream()` emits a dedicated `{"type": "interrupted", "text": "...", "source": source}` event.

4. **Module Handoff Requirements:**
   - **For Rohit (UI - `ui/server.py`):** When receiving `{"action": "interrupt"}` over WebSocket, invoke `core.service.interrupt_generation()`.
   - **For Aryan & Madhuri (Voice - `voice/stt.py`):** On barge-in voice detection, invoke `core.service.interrupt_generation()` and call `voice.tts.stop_speaking()`.

## Day 8 Implementation: Document Intelligence, Multi-Format Reader & Summarizer (Creator Engine)

### Architectural Design
1. **Multi-Format Ingestion Engine (`creator/document_reader.py`):**
   - High-fidelity text, heading hierarchy, 2D table matrices, and metadata extraction across PDF (`pypdf`), Word (`python-docx`), PowerPoint (`python-pptx`), HTML Web Artifacts, and Markdown.
   - Zero-dependency HTML5 parser (`_WebArtifactHTMLParser`) extracting bento metric cards and data tables.
   - Devanagari Unicode script detection (`_contains_devanagari`).

2. **Structural Inspection & Table Extraction:**
   - `inspect_document(file_path)` provides sub-millisecond structural diagnostics (page count, table count, headings, words, valid format).
   - `extract_tables(file_path)` yields 2D matrices preserving column headers and rows.

3. **Dual-Engine Executive Summarizer:**
   - `summarize_document(file_path)` utilizes Google Gemini API with fallback to statistical extractive NLP heuristic.
   - Complies with Day 8 Stream Cancellation Token protocol (`cancel_event` aborts within 20ms).

4. **Central Registry & Brain Tools (`creator/tools.py`):**
   - Exposed `ReadDocumentTool`, `SummarizeDocumentTool`, and `InspectDocumentTool`.
   - Expands Creator tools count to 11 registered tools.

