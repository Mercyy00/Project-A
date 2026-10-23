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
