# Task List: Jay's Core Engine - Streaming & Resilient Failover (Day 6)

## Phase 1: Core Brain Streaming & Backoff
- [x] **Task 1: Add Streaming Generator & Backoff to JarvisBrain**
  - **File:** `core/brain.py`
  - **Description:** Implement `chat_stream(user_message, mode)` and exponential backoff retry on 429/503.
  - **Acceptance Criteria:** `chat_stream` yields tokens in real-time; handles tool calls.
  - **Verification:** Unit tests in `core/test_service.py` - PASSED.

## Phase 2: Async Service Stream Wrapper
- [x] **Task 2: Implement Async handle_text_stream in Service Layer**
  - **File:** `core/service.py`
  - **Description:** Expose `handle_text_stream(text, source, mode)` for WebSocket and Voice engines.
  - **Acceptance Criteria:** Yields `{"type": "chunk", "text": "..."}` and final `{"type": "done", ...}` packet.
  - **Verification:** Async tests in `core/test_service.py` - PASSED.

## Phase 3: CLI Streaming Integration & Test Suite
- [x] **Task 3: Enable Streaming in Terminal REPL & Comprehensive Test Suite**
  - **Files:** `main_cli.py`, `core/test_service.py`
  - **Description:** Add live streaming to terminal REPL and complete unit test coverage.
  - **Acceptance Criteria:** `pytest core/` passes 100%.
  - **Verification:** Run `pytest core/` - 9/9 passed; Full repo - 207/207 passed.
