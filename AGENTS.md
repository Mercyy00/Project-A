# Team Rules for Antigravity AI Assistants

These rules apply to ANY Antigravity agent running in this workspace.

## 1. Modular Isolation Rule (Strict!)
- **Jay's Agent**: You are ONLY allowed to create and edit files inside `core/`.
- **Aryan's Agent**: You are ONLY allowed to create and edit files inside `voice/`.
- **Abhijit's Agent**: You are ONLY allowed to create and edit files inside `tools/`.
- **Rohit's Agent**: You are ONLY allowed to create and edit files inside `ui/` and `memory/`.
- If an agent needs a change in another module, DO NOT edit the other module directly. Instead, inform the developer to request changes from that module's owner.

## 2. Interface Contract Compliance
- Every tool created in `tools/` MUST follow the `BaseTool` specification in `tools/base.py` and `ARCHITECTURE.md`.
- No agent may modify `ARCHITECTURE.md` or `tools/base.py` without team consensus.

## 3. Security & Safety First
- **NEVER** write API keys, passwords, or secrets into code files. Always read from `os.getenv(...)` via `python-dotenv`.
- **NEVER** run destructive commands (e.g. `rm -rf`, `format`, bulk file deletions) without explicit user confirmation.
- Restrict all file operations to a designated safe sandbox directory during initial testing.

## 4. Code Quality & Standards
- Python Version: **Python 3.11+**.
- Type hints: Mandatory on all function signatures (`def foo(bar: str) -> bool:`).
- Docstrings: Concise explanation of parameters and return types.
- Error handling: Every tool and async call must be wrapped in `try/except` returning structured error results (`ToolResult(success=False, ...)`). Never crash the host process!
- Clean imports: Do not use wildcard imports (`from module import *`).
