# Task List: Jay's Core Engine & Team Integration (Day 7)

## Day 6: Streaming & Resilient Failover (Completed)
- [x] **Task 1: Add Streaming Generator & Backoff to JarvisBrain** (`core/brain.py`) - PASSED
- [x] **Task 2: Implement Async handle_text_stream in Service Layer** (`core/service.py`) - PASSED
- [x] **Task 3: Enable Streaming in Terminal REPL & Comprehensive Test Suite** (`main_cli.py`, `core/test_service.py`) - PASSED

---

## Day 7: Universal Tool Synchronization, Team PR Integration & Test Hardening

### Phase 1: Team Audit & Abhijit's Tools Integration
- [x] **Task 4: Audit GitHub Status Across All 4 Feature Pairs**
  - **Description:** Pull latest branches, inspect git log, verify status for Aryan, Abhijit, Rohit, Vidhita, Trupti, Madhuri, and Akanksha.
  - **Status:** All pairs up-to-date. Abhijit's unmerged commits identified and verified.
- [x] **Task 5: Review, Verify & Merge Abhijit's Tools Branch (`feature/abhijit-tools`)**
  - **Files:** `tools/guard.py`, `tools/system_tools.py`, `tools/code_tools.py`, `tools/control_tools.py`, `tests/test_guard.py`, `tests/test_code_tools.py`
  - **Description:** Verified kill-switch hotkey (`Ctrl+Alt+Q`), audit logging, settings page launcher, and workspace python execution. 61/61 tests passed. Cleanly fast-forward merged into `main`.

### Phase 2: Core Brain Full-Spectrum Tool Discovery & Alignment
- [x] **Task 6: Wire All 38 Registered Tools into JarvisBrain Discovery**
  - **File:** `core/brain.py`
  - **Description:** Expanded `_discover_tools()` from 29 tools to 38 tools to include:
    - Creator tools: `create_pdf`, `create_docx`, `create_pptx`, `create_document`
    - Messaging tools: `send_telegram`
    - Vision tools: `do_on_screen`, `explain_code_on_screen`
    - System & Control tools: `open_file`, `open_settings_page`
  - **Acceptance Criteria:** `len(brain.tools) == 38` and all schemas/docstrings match Gemini function calling spec.
- [x] **Task 7: Persona & System Prompt Expansion**
  - **File:** `core/brain.py`
  - **Description:** Updated `DEFAULT_SYSTEM_PROMPT` to enforce tool mandates for document creation, Telegram messaging, screen automation, and settings pages.

### Phase 3: Test Hardening & Dependency Pinning
- [x] **Task 8: Add `pynput` Dependency to `requirements.txt`**
  - **File:** `requirements.txt`
  - **Description:** Added `pynput>=1.7.6` to ensure kill-switch listener imports successfully on clean environments.
- [x] **Task 9: Fix Environment Hermetic Isolation in `tests/test_brain.py`**
  - **File:** `tests/test_brain.py`
  - **Description:** Isolated `GEMINI_MODEL` and `MODEL_NAME` in `setUp()` mock environment dictionary to prevent test failure when `.env` is loaded.
- [x] **Task 10: Expand Core Service Tests for 38 Tools Discovery**
  - **File:** `core/test_service.py`
  - **Description:** Added assertions for all 38 tools in `test_tool_discovery_count`. All 14 tests in `core/` passed.


---

## Week 2: Autonomous Agentic Intelligence & Proactive Voice Assistant (Days 8–14)

### Day 8: Full-Duplex Voice, Barge-In & Stream Cancellation
- [x] **Task 11: Cancellation Token & Abort Protocol in Brain & Service** (`core/brain.py`, `core/service.py`, `core/test_service.py`) - Jay (Core Brain) [PASSED]
  - Sub-100ms cancellation token (`cancel_event`) in `chat_stream()`, `stream_chat()`, and async `handle_text_stream()`.
  - Zero-latency `interrupt()` / `abort()` on `JarvisBrain` and `interrupt_generation()` service API.
  - Emission of `{"type": "interrupted", ...}` without history corruption.
  - Comprehensive unit test suite in `core/test_service.py` passing 14/14 tests.
- [ ] **Task 11b: UI WebSocket Interruption Action & HUD Pulse Wave** (`ui/server.py`, `ui/index.html`) - Rohit (UI)
- [ ] **Task 12: Continuous VAD & Zero-Latency Audio Muting on Speech** (`voice/stt.py`, `voice/tts.py`) - Pair B
- [ ] **Task 13: Non-Blocking Guard Interruption Logging** (`tools/guard.py`) - Pair C
- [ ] **Task 14: Telegram Voice Note Audio Transcribe Handler** (`messaging/telegram_bot.py`) - Pair D
- [x] **Task 14b: Multi-Format Document Reader, Table Extractor & Summarizer Suite** (`creator/document_reader.py`, `creator/tools.py`, `tests/test_creator.py`) - Vidhita (Creator - Pair D) [PASSED]
  - Full-fidelity ingestion across PDF (`pypdf`), Word (`python-docx`), PowerPoint (`python-pptx`), HTML Web Artifacts, and Markdown.
  - Sub-millisecond structural inspection (`inspect_document`) and 2D table extraction matrix (`extract_tables`).
  - Autonomous AI & offline heuristic executive summarizer (`summarize_document`) with sub-20ms cancellation token abort.
  - Central tool registry integration: `read_document`, `summarize_document`, and `inspect_document` (11 Creator tools registered).
  - 76/76 unit and acceptance tests passing hermetically.

### Day 9: Long-Term Semantic Vector Memory (RAG) & Workspace Indexing
- [ ] **Task 15: ChromaDB Persistent Vector Memory Store** (`memory/vector_store.py`) - Pair A
- [ ] **Task 16: Local Workspace & Codebase Semantic Search Tool** (`tools/file_tools.py`) - Pair C
- [ ] **Task 17: User Accent Adaptation & Whisper Prompt Priming** (`voice/stt.py`) - Pair B
- [x] **Task 18: Multi-Format Document Summarizer Tool** (`creator/document_reader.py`) - Vidhita (Pair D) [PASSED in Day 8 Elevation]

### Day 10: Multi-Step Autonomous Agent Workflows & Look-Decide-Act Loop
- [ ] **Task 19: Recursive ReAct Goal Planner with Step Milestones** (`core/brain.py`, `ui/index.html`) - Pair A
- [ ] **Task 20: Screen-Guided Look-Decide-Act GUI Loop** (`vision/loop.py`) - Pair C
- [ ] **Task 21: Spoken Milestone Progress Audio Cues** (`voice/tts.py`) - Pair B
- [ ] **Task 22: Telegram Inline Action Confirmation Buttons** (`messaging/telegram_bot.py`) - Pair D

### Day 11: Real-Time Web Intelligence & Live Web Scraping
- [ ] **Task 23: Clean Webpage Content & Table Extractor Tools** (`tools/web_tools.py`) - Pair C
- [ ] **Task 24: Academic Citation Engine & Link Preview in HUD** (`core/brain.py`, `ui/index.html`) - Pair A
- [ ] **Task 25: Morning Audio Briefing Generator** (`voice/briefing.py`) - Pair B
- [ ] **Task 26: Web Research to PDF/DOCX Report Compiler** (`creator/report_builder.py`) - Pair D

### Day 12: Proactive System Monitoring, Cron Triggers & Smart Alerts
- [ ] **Task 27: Background Async Task Scheduler & HUD Toast Alerts** (`core/scheduler.py`, `ui/index.html`) - Pair A
- [ ] **Task 28: Hardware Watchdog (CPU, Battery & Disk)** (`tools/guardian.py`) - Pair C
- [ ] **Task 29: Auditory Sci-Fi Alert Chimes** (`voice/audio/`) - Pair B
- [ ] **Task 30: Proactive Telegram Push Notification Dispatcher** (`messaging/telegram_bot.py`) - Pair D

### Day 13: Local Offline LLM Fallback (Ollama / Llama-3) & Air-Gapped Mode
- [ ] **Task 31: Triple-Engine Failover (Groq ➔ Gemini ➔ Local Ollama)** (`core/brain.py`) - Pair A
- [ ] **Task 32: Air-Gapped Tool Execution Validation** (`tools/safety.py`) - Pair C
- [ ] **Task 33: End-to-End 100% Offline Spoken Loop Benchmark** (`voice/benchmark_offline.py`) - Pair B
- [ ] **Task 34: Offline Document Template Engine** (`creator/templates.py`) - Pair D

### Day 14: Final Integration 2.0, Packaging & Evaluator Showcase
- [ ] **Task 35: Full Regression Test Suite (Target: 350+ Tests)** (`tests/`) - All Hands
- [ ] **Task 36: One-Click Windows Executable / Installer Packaging** (`run.bat`, `setup.py`) - All Hands
- [ ] **Task 37: 3-Minute Week 2 Video Walkthrough & Viva Guide** (`docs/DAY_14_DEMO_SCRIPT.md`) - All Hands
