# Implementation Plan: JARVIS Core Persona & Anti-Phantom Execution Overhaul

## Overview
Transform Project JARVIS's core brain engine into a high-speed, cinematic AI desktop assistant that behaves with the authentic persona of Tony Stark's JARVIS (witty, crisp, intelligent, respectful) while guaranteeing zero phantom execution (never claiming a desktop task was done without actually invoking and verifying the tool).

## Architecture Decisions
- **Strict Anti-Phantom Rule:** The system prompt will enforce an uncompromisable constraint: JARVIS must never state, imply, or hallucinate that an action was performed unless the corresponding tool was invoked and returned success.
- **Dynamic Tool Synchronization:** Instead of maintaining a hardcoded subset of 18 tools in `_discover_tools()`, dynamically generate function signatures and wrappers from `tools.registry.TOOL_REGISTRY` so all registered system tools (including volume, brightness, window controls, and battery) are exposed to both Gemini and Groq.
- **Eliminate Unsafe Tool Stripping:** Remove the fallback in `_chat_with_groq()` that silently strips tools and sends a bare conversational prompt on schema errors, which previously caused the model to hallucinate task execution.
- **Latency Optimization:** Limit response length to 1–2 punchy sentences, enforce tight token generation limits, and streamline tool follow-up turns.
- **Strict Modular Isolation:** All edits stay strictly within Jay's territory (`core/brain.py`, `core/service.py`, `core/test_*.py`).

## Task List

### Phase 1: Persona & Anti-Hallucination Prompt Architecture
- [ ] **Task 1: System Prompt & Persona Engine Overhaul (`core/brain.py`)**
  - **Description:** Rewrite `DEFAULT_SYSTEM_PROMPT` to embody the genuine JARVIS persona (crisp British wit, addressing user as "sir", 1–2 punchy sentences, proactive) and mandate the zero-phantom tool rule.
  - **Acceptance Criteria:**
    - Model outputs snappy, authentic JARVIS dialogue (under 25 words per turn).
    - Model strictly refuses to claim a task is complete without tool execution.
    - Multilingual Devanagari rules for Hindi and Marathi are preserved.
  - **Verification:**
    - Prompt evaluation via unit tests in `core/test_llm.py`.
  - **Estimated Scope:** Small (1 file: `core/brain.py`).

### Checkpoint 1: Persona Review
- [ ] Persona prompt verified for tone, brevity, and anti-hallucination constraint.

---

### Phase 2: Dynamic Tool Discovery & Registration Alignment
- [ ] **Task 2: Dynamic Tool Discovery & Schema Synchronization (`core/brain.py`)**
  - **Description:** Replace the hardcoded 18-tool list in `_discover_tools()` with dynamic wrapper generation from `tools.registry.TOOL_REGISTRY`. Ensure tools like `set_volume`, `set_brightness`, `lock_screen`, `battery`, `list_windows`, `focus_window`, `minimize_window`, and clipboard tools are properly registered with Gemini and Groq.
  - **Acceptance Criteria:**
    - All tools in `TOOL_REGISTRY` are discoverable by `JarvisBrain`.
    - Gemini tools config and Groq function definitions match exact schemas.
    - Zero missing tool definitions.
  - **Verification:**
    - Unit test checking that `len(brain.tools) >= len(TOOL_REGISTRY)`.
  - **Estimated Scope:** Small-Medium (1 file: `core/brain.py`).

### Checkpoint 2: Tool Registry Alignment
- [ ] Verify all 20+ tools are exposed and callable by the LLM without schema validation errors.

---

### Phase 3: Dual-Engine ReAct Loop & Anti-Phantom Fallback
- [ ] **Task 3: Robust Dual-Engine ReAct Loop & Safe Fallback (`core/brain.py`)**
  - **Description:** Refactor `chat()` and `_chat_with_groq()` to reliably handle tool calling, eliminate unsafe fallback to tool-less prompts, and ensure `last_tool_steps` captures all executed actions accurately.
  - **Acceptance Criteria:**
    - If a command requires a tool, the model invokes it rather than generating mock text.
    - If a tool fails, the error is handled gracefully and reported honestly.
    - No silent fallback to tool-less completions on Groq.
  - **Verification:**
    - Test execution of tool calls with mocked Groq and Gemini responses.
  - **Estimated Scope:** Medium (1 file: `core/brain.py`).

### Checkpoint 3: Execution Verification
- [ ] Verify that commands like "open calculator" or "mute volume" consistently invoke tools and record steps.

---

### Phase 4: Test Suite & End-to-End Verification
- [ ] **Task 4: Unit Test Suite & Regression Guard (`core/test_service.py`, `core/test_llm.py`)**
  - **Description:** Complete and update the test suite for `core/service.py` and `core/brain.py` to validate multi-lingual responses, tool invocation tracking, and failure handling.
  - **Acceptance Criteria:**
    - All tests in `core/test_service.py` pass.
    - All tests in `core/test_llm.py` pass.
    - `handle_text` properly formats `text`, `tool_steps`, and `source`.
  - **Verification:**
    - `pytest core/` executes cleanly with zero failures.
  - **Estimated Scope:** Small (2 files: `core/test_service.py`, `core/test_llm.py`).

### Final Checkpoint: Ready for Production & Team Integration
- [ ] Full `pytest core/` passes.
- [ ] Quick smoke test of `python main_cli.py`.
- [ ] Ready for Jay to review and merge into `feature/jay-core`.

---

## Risks and Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| Dynamic tool wrapping for Gemini fails typing/docstring inspection | High | Inspect `BaseTool.get_schema()` and wrap with explicit typed docstrings and parameter signatures. |
| Groq rate limit (429) during peak hours | Medium | Seamless dual-engine failover between Groq LPU and Gemini 3.8 Flash is already established. |
| Model remains overly conversational despite system prompt | Medium | Set `temperature=0.3` for tool tasks and enforce strict max_tokens limits. |

## Open Questions
- None. Requirements and scope confirmed via `interview-me`.
