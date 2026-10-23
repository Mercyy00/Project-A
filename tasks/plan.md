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
