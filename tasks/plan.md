# Implementation Plan: Jay's Core Engine - Streaming & Resilient Failover (Day 6)

## Overview
Implement the remaining Day 6 deliverables for Jay on `feature/jay-core`: real-time streaming response generation (`chat_stream` and `handle_text_stream`), exponential backoff retry on transient API limits (429/503), and async stream coordination for UI WebSocket and Voice engines, while preserving the strict modular isolation rule.

## Architecture Decisions
- **Unified Streaming Generator:** Add `chat_stream()` to `JarvisBrain` in `core/brain.py` supporting token streaming from both Groq (`stream=True`) and Gemini (`client.models.generate_content_stream`).
- **Async Service Stream Wrapper:** Add `handle_text_stream()` in `core/service.py` yielding structured events (`{"type": "chunk", "text": "..."}`) and finalizing with `{"type": "done", "text": full_text, "tool_steps": steps}`.
- **Adaptive Network Backoff:** Wrap LLM completions with a 2-stage exponential backoff (0.5s, 1.0s) for transient 429/503 errors before triggering seamless dual-engine failover.
- **Strict Territory Isolation:** All changes stay strictly within Jay's files (`core/brain.py`, `core/service.py`, `core/test_service.py`, `main_cli.py`).

## Task List

### Phase 1: Core Brain Streaming & Backoff
- [x] **Task 1: Add Streaming Generator & Backoff to JarvisBrain (`core/brain.py`)**
  - Implement `chat_stream(user_message, mode)` yielding string tokens/chunks.
  - Implement 2-retry exponential backoff on 429/503 before failover.
  - Acceptance Criteria: Generator yields tokens in real time; tool calling executes seamlessly before stream conclusion.
  - Verification: Unit tests in `core/test_service.py` - PASSED.

### Phase 2: Async Service Stream Wrapper
- [x] **Task 2: Implement Async handle_text_stream in Service Layer (`core/service.py`)**
  - Expose `handle_text_stream(text, source, mode)` returning `AsyncGenerator[Dict[str, Any], None]`.
  - Save completed interaction to memory vault upon stream termination.
  - Acceptance Criteria: Consumer receives token chunks and final done packet with tool steps.
  - Verification: Async test in `core/test_service.py` - PASSED.

### Phase 3: CLI Streaming Integration & Test Suite
- [x] **Task 3: Enable Streaming in Terminal REPL & Comprehensive Test Suite (`main_cli.py`, `core/test_service.py`)**
  - Update `main_cli.py` to stream tokens to the terminal with immediate typing cadence.
  - Add unit tests verifying `chat_stream`, `handle_text_stream`, and retry backoff.
  - Acceptance Criteria: `pytest core/` passes 100%.
  - Verification: Run `pytest core/` and live stream test - 207/207 passed.
