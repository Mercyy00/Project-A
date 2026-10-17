# 🤖 Jarvis Desktop AI Assistant

An autonomous desktop AI assistant built to run locally on your laptop, execute system tasks, manage memory, and communicate via real-time voice and a sci-fi HUD.

---

## 👥 The Engineering Team & Roles

| Developer | Role | Module | Focus Area |
| :--- | :--- | :--- | :--- |
| **Jay** | **Team Lead & Core Brain** | `core/` | LLM orchestration, Tool-calling loops, Prompting, Merging |
| **Aryan** | **Voice Engineer** | `voice/` | Wake-word detection, Speech-to-Text (STT), Neural TTS |
| **Abhijit** | **System & Automation Engineer** | `tools/` | OS subprocesses, File operations, System stats, Safety guards |
| **Rohit** | **Frontend & Memory Engineer** | `ui/`, `memory/` | React HUD, WebSockets/FastAPI, SQLite, Vector DB (RAG) |

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Python 3.11+
- Git
- Node.js LTS (for UI dashboard)

### 2. Setup Environment
```bash
# Clone the repository
git clone <repo-url>
cd jarvis-desktop-assistant

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
```
Add your `GEMINI_API_KEY` or `OPENAI_API_KEY` to `.env`.

---

## 📚 Key Project Documents

- 📋 [**WEEK_1_EXECUTION_PLAN.md**](file:///d:/engineers/Project%20-%20A/WEEK_1_EXECUTION_PLAN.md) — Day-by-day technical tasks, skills, and acceptance criteria for all 4 team members.
- 📐 [**ARCHITECTURE.md**](file:///d:/engineers/Project%20-%20A/ARCHITECTURE.md) — Module boundaries, communication protocols, and canonical tool interfaces.
- 🛡️ [**AGENTS.md**](file:///d:/engineers/Project%20-%20A/AGENTS.md) — Strict guidelines for all Antigravity AI agents working in this workspace.
