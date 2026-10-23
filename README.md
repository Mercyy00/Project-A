# 🤖 Jarvis Desktop AI Assistant

An autonomous desktop AI assistant built to run locally on your laptop, execute system tasks, manage memory, and communicate via real-time voice, neural Edge-TTS, and a futuristic sci-fi Web HUD.

---

## 👥 The Engineering Team & Roles (8-Member Architecture)

| Developer | Role | Module | Focus Area |
| :--- | :--- | :--- | :--- |
| **Jay** | **Team Lead & Core Brain** | `core/` | LLM orchestration, ReAct tool-calling loops, Merging |
| **Rohit** | **Frontend & Memory Engineer** | `ui/`, `memory/` | Sci-Fi Web HUD, WebSocket, SQLite Memory, Neural TTS |
| **Abhijit** | **System & Control Engineer** | `tools/` | Process launch (`OpenAppTool`), System stats, Safety guards |
| **Aryan** | **Vision Engineer** | `vision/` | Screen capture, Visual QA with Gemini |
| **Madhuri** | **Voice Engineer (STT)** | `voice/` | Whisper Speech-to-Text, Language detection (EN/HI/MR) |
| **Akanksha** | **Voice Engineer (TTS)** | `voice/` | Neural Edge-TTS speech synthesis (EN/HI/MR) |
| **Vidhita** | **Document Engineer** | `creator/` | Automated PDF, Word, PowerPoint creation |
| **Trupti** | **Messaging Engineer** | `messaging/`| Telegram Bot, WhatsApp automation, Scheduled reminders |

---

## 🚀 Quick Start Guide (Day 10 Installation)

### 1. Prerequisites
- Python 3.11+
- Windows 10 / 11 (or macOS / Linux)
- Google Chrome or Microsoft Edge (for Web Speech API)

### 2. One-Click Launch (Windows)
Double-click **`run.bat`** in the project root folder. It will:
1. Detect Python virtual environment.
2. Launch the FastAPI & WebSocket backend on `http://127.0.0.1:8000`.
3. Open your browser automatically to the futuristic Jarvis HUD.

### 3. Manual Setup & Run
```bash
# 1. Clone the repository
git clone https://github.com/Mercyy00/Project-A.git
cd Project-A

# 2. Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1   # On Windows PowerShell

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Add your GEMINI_API_KEY inside .env

# 5. Run Backend Server
python -m uvicorn ui.server:app --port 8000 --reload
```
Open **`http://127.0.0.1:8000`** in your browser.

### 📱 Accessing from Mobile Phones / Tablets
Jarvis Web HUD is fully responsive!
To use Jarvis on your mobile phone on the same Wi-Fi network:
1. Find your computer's local IP address (e.g. `192.168.1.15`).
2. Run server with: `python -m uvicorn ui.server:app --host 0.0.0.0 --port 8000`
3. On your phone's browser (Chrome/Safari), open: `http://192.168.1.15:8000`

---

## 🧪 Running Automated Tests
```bash
pytest tests/ -v
```

---

## 📚 Key Project Documents

- 📋 [**WEEK_1_EXECUTION_PLAN.md**](file:///d:/engineers/Project%20-%20A/WEEK_1_EXECUTION_PLAN.md) — Day-by-day technical tasks, skills, and acceptance criteria for all 4 team members.
- 📐 [**ARCHITECTURE.md**](file:///d:/engineers/Project%20-%20A/ARCHITECTURE.md) — Module boundaries, communication protocols, and canonical tool interfaces.
- 🛡️ [**AGENTS.md**](file:///d:/engineers/Project%20-%20A/AGENTS.md) — Strict guidelines for all Antigravity AI agents working in this workspace.
