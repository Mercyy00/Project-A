# Task List: JARVIS Core Persona & Anti-Phantom Execution Overhaul

## Phase 1: Persona & Anti-Hallucination Prompt Architecture
- [x] **Task 1: System Prompt & Persona Engine Overhaul**
  - **File:** `core/brain.py`
  - **Description:** Rewrite `DEFAULT_SYSTEM_PROMPT` to instill the authentic, witty Tony Stark JARVIS persona and enforce the strict Zero-Phantom Execution rule.
  - **Acceptance Criteria:** Under 25 words per response, addresses user as "sir", authentic British cadence, never claims action without tool execution.
  - **Verification:** Unit tests in `core/test_llm.py` and `core/test_service.py`.

## Checkpoint 1: Persona Review
- [x] Persona prompt verified for tone, brevity, and anti-hallucination constraint.

## Phase 2: Dynamic Tool Discovery & Registration Alignment
- [x] **Task 2: Dynamic Tool Discovery & Schema Synchronization**
  - **File:** `core/brain.py`
  - **Description:** Register all 29 tools from `tools.registry.TOOL_REGISTRY` into `JarvisBrain` so Gemini and Groq have access to 100% of available tools (including volume, brightness, battery, and window management).
  - **Acceptance Criteria:** All tools in `TOOL_REGISTRY` exposed to brain; zero missing system tools.
  - **Verification:** Assert `len(brain.tools) >= 29` in `core/test_service.py`.

## Checkpoint 2: Tool Registry Alignment
- [x] All 29 system tools exposed and validated without schema errors.

## Phase 3: Dual-Engine ReAct Loop & Anti-Phantom Fallback
- [x] **Task 3: Robust Dual-Engine ReAct Loop & Safe Fallback**
  - **File:** `core/brain.py`
  - **Description:** Refactor `chat()` and `_chat_with_groq()` to eliminate unsafe tool-stripping fallback and guarantee honest error reporting if tools fail.
  - **Acceptance Criteria:** No silent fallback to tool-less completions; tools are executed and verified before final output.
  - **Verification:** Live battery check and calculator execution verified with real step logging.

## Checkpoint 3: Execution Verification
- [x] Desktop commands consistently trigger tool execution and step logging.

## Phase 4: Test Suite & End-to-End Verification
- [x] **Task 4: Unit Test Suite & Regression Guard**
  - **Files:** `core/test_service.py`, `core/test_llm.py`
  - **Description:** Update core unit tests to cover multi-lingual responses, tool invocation tracking, and failure handling.
  - **Acceptance Criteria:** `pytest core/` passes with 100% green tests.
  - **Verification:** Ran `pytest core/` (4 passed in 2.91s).

## Final Checkpoint: Complete
- [x] All tests pass.
- [x] CLI and live tool verification verified.
- [x] Ready for Jay's review.
