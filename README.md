# 🤖 Project JARVIS - Autonomous Desktop AI Assistant

[![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com)
[![Groq LPU](https://img.shields.io/badge/LLM-Groq%20Cloud%20LPU%20(Qwen--27B)-f55036.svg)](https://groq.com)
[![Google Gemini](https://img.shields.io/badge/LLM-Google%20Gemini%20Flash-4285F4.svg?logo=google)](https://ai.google.dev/)
[![STT](https://img.shields.io/badge/STT-faster--whisper%20(Base)-green.svg)](https://github.com/SYSTRAN/faster-whisper)
[![TTS](https://img.shields.io/badge/TTS-Edge--TTS%20Neural-purple.svg)](https://github.com/rany2/edge-tts)
[![Tests](https://img.shields.io/badge/tests-62%2B%20passed-brightgreen.svg)](https://docs.pytest.org/)

An autonomous, multimodal desktop AI assistant engineered to run locally on Windows. Jarvis executes OS automation tasks, maintains long-term memory, understands desktop screens, and interacts via high-speed multilingual voice and a futuristic Web HUD.

---

## 👥 Engineering Team & Module Boundaries

Project Jarvis is developed under strict modular isolation rules defined in [`AGENTS.md`](file:///d:/engineers/Project%20-%20A/AGENTS.md) and [`ARCHITECTURE.md`](file:///d:/engineers/Project%20-%20A/ARCHITECTURE.md).

| Developer / Engineer | Role | Module | Primary Scope & Responsibilities |
| :--- | :--- | :--- | :--- |
| **Jayesh (Jay)** | **Team Lead & Core Brain** | `core/` | Dual LLM orchestration (Groq Cloud LPU + Gemini), quota failover, ReAct tool loop, system prompts, git integration |
| **Madhuri & Akanksha** | **Voice Engineers** | `voice/` | Multilingual Speech-to-Text (`faster-whisper`), language classification (`en`, `hi`, `mr`), Neural TTS (`edge-tts`), spoken voice loop |
| **Aryan** | **Vision Engineer** | `vision/` | Desktop capture (`mss`), image compression, Gemini multimodal screen understanding, privacy toggle |
| **Abhijit** | **System & Automation Engineer** | `tools/` | Windows application launching, Start Menu indexer, system telemetry (`psutil`), file operations, safety guards |
| **Rohit** | **Frontend & Memory Engineer** | `ui/`, `memory/` | Sci-Fi Web HUD, FastAPI WebSocket backend, persistent SQLite database (WAL mode), conversation memory |

---

## 🧠 Core Architecture & Key Capabilities

```
                              +---------------------------------------+
                              |         User Interaction Layer        |
                              |  [Web HUD]   [Voice Loop]   [CLI REPL]|
                              +-------------------+-------------------+
                                                  |
                                                  v
                              +---------------------------------------+
                              |         Core Brain Engine (Jay)       |
                              |   Dual-Engine: Groq LPU + Gemini      |
                              |   Automatic 429 / Quota Failover      |
                              +-------------------+-------------------+
                                                  |
                                                  v
                              +---------------------------------------+
                              |         Tool Registry Dispatch        |
                              |        (BaseTool Specification)       |
                              +---+----------+----------+----------+--+
                                  |          |          |          |
                                  v          v          v          v
                             [System/Apps] [Vision]  [Memory]   [Voice]
                               Abhijit      Aryan     Rohit     Madhuri
```

### 1. Dual-Engine LLM Core (`core/brain.py`)
- **Primary Engine:** Groq Cloud LPU running `qwen/qwen3.8-27b` for sub-second, ultra-low-latency reasoning and autonomous tool calling.
- **Failover Engine:** Google Gemini (`gemini-3.8-flash` / `gemini-2.5-flash`) via the `google-genai` SDK with automatic failover when rate limits, quota limits, or 429 status codes occur.
- **Multi-Turn Memory:** Conversational context tracking with language-adaptive persona.

### 2. Multilingual Voice Pipeline (`voice/`)
- **Speech-to-Text (STT):** `faster-whisper` (`base` model, `cpu` with `int8` quantization) with microphone capture and 1.5-second silence auto-stop.
- **Language Detection:** Real-time automatic classification between **English (`en`)**, **Hindi (`hi`)**, and **Marathi (`mr`)**.
- **Neural Text-to-Speech (TTS):** Edge-TTS high-fidelity neural voices with pygame playback:
  - English: `en-US-GuyNeural`
  - Hindi: `hi-IN-MadhurNeural`
  - Marathi: `mr-IN-ManoharNeural`
- **Spoken Loop:** Complete hands-free conversational loop in `main_voice.py` measuring round-trip response latency.

### 3. Vision & Screen Understanding (`vision/`)
- High-speed screen capture via `mss` with automatic resolution scaling (1280px max width).
- Multimodal visual reasoning with Google Gemini to analyze screen contents, troubleshoot UI errors, and inspect windows.
- Hardware-level desktop handle resolution (`_ensure_desktop_access`) and privacy kill-switch (`VISION_PAUSED=1`).

### 4. System Automation & Tooling (`tools/`)
- **Application Launcher (`OpenAppTool`):** Resolves desktop applications across Windows UWP protocols (`calculator:`, `ms-settings:`), PATH binaries, registry `App Paths`, and recursive Start Menu shortcut (`.lnk`) scanning.
- **System Telemetry (`GetSystemStatsTool`):** Live CPU load percentage, RAM usage (GB used / total), and battery status.
- **File System Tools:** Sandboxed file read and write operations.
- **GUI Control:** Mouse click, scroll, keyboard text typing, and shortcut execution (`pyautogui`).

### 5. Memory & Telemetry Vault (`memory/`)
- Persistent SQLite storage with Write-Ahead Logging (`PRAGMA journal_mode=WAL;`) for high concurrency.
- Storage for user notes, tasks, and historical chat interactions.

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- **Operating System:** Windows 10 or Windows 11 (64-bit)
- **Python:** Python 3.11 or 3.12 (with `python.exe` added to system `PATH`)
- **Git:** Git for Windows

### 2. Installation
```powershell
# Clone the repository
git clone https://github.com/Mercyy00/Project-A.git
cd Project-A

# Create and activate a virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install all project dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration
Copy the template configuration file to `.env`:
```powershell
cp .env.example .env
```
Open `.env` and configure your API keys and preferred models:
```ini
# LLM Providers
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key_here
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=qwen/qwen3.8-27b
MODEL_NAME=gemini-3.8-flash

# Voice Engine Defaults
WHISPER_MODEL=base
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
TTS_VOICE_EN=en-US-GuyNeural
TTS_VOICE_HI=hi-IN-MadhurNeural
TTS_VOICE_MR=mr-IN-ManoharNeural

# Server Configuration
SERVER_HOST=127.0.0.1
SERVER_PORT=8000
```

---

## 🎮 How to Run Jarvis

Jarvis provides three distinct operational interfaces:

### Option A: Futuristic Web HUD (Recommended)
Launch the FastAPI WebSocket backend and open the sci-fi browser dashboard:
```powershell
python -m uvicorn ui.server:app --host 127.0.0.1 --port 8000
```
Then navigate to: **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

### Option B: Interactive Spoken Voice Loop
Talk to Jarvis in English, Hindi, or Marathi through your microphone:
```powershell
python main_voice.py
```
*(Or double-click `run_jarvis_voice.bat`)*

### Option C: Interactive Terminal REPL
Direct text conversation with the Jarvis Core Brain in PowerShell:
```powershell
python main_cli.py
```

---

## 🧪 Testing & Verification

Run the comprehensive automated test suite (62+ unit and integration tests):
```powershell
# Run the entire test suite
pytest

# Run voice STT and TTS tests only
pytest voice/test_stt.py voice/test_tts.py

# Run core brain and tool tests
pytest tests/test_brain.py tests/test_tools.py tests/test_control_tools.py
```

Convenience batch launchers are also available in the repository root:
- `run_voice_tests.bat` — Run all voice unit tests.
- `run_audio_check.bat` — Test microphone capture and audio playback.
- `run_benchmark.bat` — Benchmark Whisper `tiny`, `base`, and `small` models.

---

## 📁 Repository Structure

```
Project-A/
│
├── .env.example              # Environment variables template
├── requirements.txt          # Python dependencies
├── ARCHITECTURE.md           # System contracts and architecture design
├── AGENTS.md                 # Team modular isolation rules for AI agents
├── main_cli.py               # Interactive CLI terminal runner
├── main_voice.py             # Spoken conversational loop (listen -> brain -> speak)
│
├── run_jarvis_voice.bat      # 1-click launcher for spoken voice loop
├── run_voice_tests.bat       # 1-click runner for voice test suite
├── run_audio_check.bat       # Audio hardware diagnostic check
├── run_benchmark.bat         # Whisper model benchmark runner
│
├── core/                     # [Jay] LLM Brain & Reasoning Core
│   ├── brain.py              # JarvisBrain engine (Gemini + Groq failover + tools)
│   ├── service.py            # Async core brain service
│   ├── test_llm.py           # LLM connection verification
│   └── test_service.py       # Core service unit tests
│
├── voice/                    # [Madhuri & Akanksha] Voice STT & TTS
│   ├── stt.py                # Faster-Whisper speech-to-text with silence detection
│   ├── tts.py                # Edge-TTS multilingual speech synthesizer
│   ├── lang.py               # Language detection (English, Hindi, Marathi)
│   ├── audio_check.py        # Hardware loopback and microphone test
│   ├── benchmark_models.py   # Quantitative latency/accuracy benchmarks
│   ├── test_stt.py           # STT unit tests (synthetic audio & vad)
│   └── test_tts.py           # TTS unit tests
│
├── vision/                   # [Aryan] Screen Understanding
│   ├── screen.py             # Desktop screenshot capture & Gemini multimodal analysis
│   └── tools.py              # TakeScreenshotTool and AnalyzeScreenTool
│
├── tools/                    # [Abhijit] System Automation & OS Control
│   ├── base.py               # Canonical BaseTool & ToolResult specifications
│   ├── registry.py           # Central tool registry with auto-module loader
│   ├── system_tools.py       # OpenAppTool, GetSystemStatsTool, SearchWebTool
│   ├── file_tools.py         # ReadFileTool, WriteFileTool
│   ├── control_tools.py      # ClickTool, TypeTextTool, PressKeysTool, ScrollTool
│   └── safety.py             # Sandboxed path validator
│
├── memory/                   # [Rohit] Long-Term Memory & SQLite Storage
│   ├── db.py                 # SQLite database connection pool & schema (WAL mode)
│   ├── storage.py            # MemoryManager for notes & conversation history
│   └── tools.py              # SaveNoteTool and SearchNotesTool
│
├── ui/                       # [Rohit] Web HUD & WebSocket Server
│   ├── index.html            # Futuristic sci-fi visual dashboard
│   └── server.py             # FastAPI REST & WebSocket server
│
├── docs/                     # Documentation and benchmark reports
│   └── voice_results.md      # Whisper benchmark performance metrics
│
└── tests/                    # Project test suite
    ├── test_brain.py         # Multi-turn conversation and failover tests
    ├── test_tools.py         # System tool execution tests
    ├── test_memory.py        # SQLite persistence tests
    ├── test_control_tools.py # GUI automation tests
    └── voice_cases.csv       # Multilingual test dataset (31 prompts)
```

---

## 📄 License & Team Contract
This project is built for the **Project Jarvis AI Assistant Initiative**. All modules adhere to team consensus, modular boundaries, and safe execution standards.
