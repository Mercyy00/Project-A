# JARVIS AI ASSISTANT: WEEK 1 COMPREHENSIVE EXECUTION PLAN
### From Absolute Zero to Working Autonomous Desktop Assistant MVP
**Target:** Grow technically proficient, master modern AI architecture, and deliver a rock-solid Phase 1 MVP.

---

## 🧭 The Engineering Mindset: How to Work with Antigravity

Before writing a single line of code, burn this principle into your team's culture:
> **"You are the Software Engineers; Antigravity is your high-speed co-pilot."**
> If your AI assistant writes code you cannot explain in an interview, technical viva, or architecture review, you haven't built anything—you have only borrowed technical debt.

### Core Rules for AI-Assisted Pair Programming
1. **Never accept code blindly:** Read every file Antigravity touches. Ask it: *"Explain why you used `asyncio` here instead of standard threading"* or *"Why did you use `psutil` instead of a raw shell command?"*
2. **One Person, One Territory:** 
   - Jay owns `core/`
   - Aryan owns `voice/`
   - Abhijit owns `tools/`
   - Rohit owns `memory/` and `ui/`
   Never tell your AI to modify another teammate's folder. If you need something, ask them to export the interface.
3. **Commit often, branch cleanly:** No one pushes directly to `main`. Every feature lives on a branch (`feature/voice-stt`, `feature/system-tools`). Jay reviews and merges Pull Requests (PRs).

---

## 🛠️ Step 0: Absolute Scratch Setup (Before Day 1 Kicks Off)

Every teammate must execute these foundation steps on their laptops.

### 0.1 GitHub & Git Configuration
1. **Sign up on GitHub:** Everyone creates an account at [github.com](https://github.com).
2. **Install Git:** Download and install [Git for Windows](https://git-scm.com/download/win).
   - In the installer, select: *Use Git from the Windows Command Prompt* and *Git Credential Manager*.
3. **Configure Git Identity (Run in PowerShell / Terminal):**
   ```powershell
   git config --global user.name "Your Name"
   git config --global user.email "your_email@example.com"
   ```
4. **Create the Central Repository (Jay only):**
   - Go to GitHub -> New Repository -> Name: `jarvis-desktop-assistant`.
   - Set to **Private** or **Public**.
   - Do NOT initialize with README (we already have local files).
   - Go to Settings -> Collaborators -> Add Aryan, Abhijit, Rohit.
5. **Accept Collaborator Invites:** Aryan, Abhijit, and Rohit check their email / GitHub notifications and accept.

### 0.2 Python 3.11+ Setup
1. Download Python 3.11 or 3.12 from [python.org](https://www.python.org/).
   - ⚠️ **CRITICAL CHECKBOX:** Ensure you check **"Add python.exe to PATH"** before clicking Install!
2. Verify in PowerShell:
   ```powershell
   python --version
   pip --version
   ```

### 0.3 Node.js Setup (Rohit)
1. Download Node.js LTS (v20+) from [nodejs.org](https://nodejs.org/).
2. Verify in PowerShell:
   ```powershell
   node -v
   npm -v
   ```

### 0.4 Antigravity IDE Setup
1. Launch Antigravity.
2. Open the project root folder: `Project - A` (or `jarvis-desktop-assistant`).
3. Notice the pre-configured project files:
   - `ARCHITECTURE.md` (System Interface Contract)
   - `AGENTS.md` (Behavior rules for all agents)
   - `.gitignore` (Prevents leaking secrets or cache files)
   - `.env.example` (API keys and settings template)
   - `requirements.txt` (Core dependencies)

### 0.5 Virtual Environment & Dependency Installation
In the project directory, run in PowerShell:
```powershell
# 1. Create a clean virtual environment
python -m venv venv

# 2. Activate it (On Windows PowerShell)
.\venv\Scripts\Activate.ps1
# (If PowerShell gives an execution policy error, run: Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass)

# 3. Upgrade pip and install baseline dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

# 4. Copy the environment secrets template
cp .env.example .env
```
*(Now open `.env` and insert your Gemini API Key or OpenAI API Key).*

---

# 📅 THE 7-DAY ROADMAP

```
DAY 1: Foundations, Repo Onboarding & Environment Sanity Checks
DAY 2: Isolated Prototypes (LLM Chat, Audio Capture, System Tools, SQLite)
DAY 3: Tool-Calling Engine, TTS Audio & REST Endpoints
DAY 4: INTEGRATION MILESTONE 1 (The Working Text-Only MVP)
DAY 5: Voice Pipeline Hookup & Conversational Memory
DAY 6: Hardening, Safety Guards, Screen Awareness & UI HUD Polish
DAY 7: FINAL INTEGRATION, Stress-Testing, Demo Video & Retrospective
```

---

## 📍 DAY 1 (Tomorrow): Genesis & Ground Rules

### Daily Theme
Zero to first commit. Everyone has a working environment, branches off `main`, and runs their first standalone test script without errors.

---

### 👑 Jay (Lead & Core/Brain)
- **Today's Goal:** Initialize the Git repository, push initial architecture skeleton, and verify LLM API connectivity.
- **Tasks to Complete:**
  1. Initialize local git in the project root:
     ```powershell
     git init
     git branch -M main
     git remote add origin https://github.com/YOUR_USERNAME/jarvis-desktop-assistant.git
     git add .
     git commit -m "chore: initial project skeleton with architecture and contracts"
     git push -u origin main
     ```
  2. Create your working branch:
     ```powershell
     git checkout -b feature/jay-core-setup
     ```
  3. Acquire a Google Gemini API Key (from Google AI Studio - free tier available).
  4. Write a sanity check script `core/test_llm.py` that imports `google-genai` and prints a response from `gemini-2.5-flash`.
- **Technical Skill to Master:** *LLM Context & API mechanics.*
  - Understand how prompt messages, system instructions, and temperature work.
  - Learn why Gemini 2.5 Flash / 3.8 Flash is chosen for speed and latency (sub-second response time is essential for a live assistant).
- **Day 1 Acceptance Criteria:**
  - Running `python core/test_llm.py` prints: `"Gemini connection successful: Hello Jay, Jarvis core initialized."`

---

### 🎙️ Aryan (Voice Engineer)
- **Today's Goal:** Verify microphone input and speaker output through Python scripts on your laptop.
- **Tasks to Complete:**
  1. Pull `main` branch:
     ```powershell
     git checkout -b feature/aryan-voice-setup
     ```
  2. Install audio dependencies: `pip install sounddevice numpy soundfile`.
  3. Create `voice/audio_check.py` to:
     - Query and list all audio input/output devices (`sounddevice.query_devices()`).
     - Record 3 seconds of audio from the default microphone at 16,000 Hz.
     - Play back the recorded audio through your laptop speakers.
- **Technical Skill to Master:** *Digital Audio Foundations (DSP basics).*
  - What is Sample Rate (e.g., 16kHz vs 44.1kHz)? Why do speech recognition models (Whisper) strictly expect 16,000 samples per second, 16-bit mono PCM?
  - What is an audio buffer/chunk?
- **Day 1 Acceptance Criteria:**
  - Running `python voice/audio_check.py` records your voice, plays it back crisply, and exits with code 0.

---

### ⚙️ Abhijit (System & Automation)
- **Today's Goal:** Validate OS automation primitives on your operating system.
- **Tasks to Complete:**
  1. Pull `main` branch:
     ```powershell
     git checkout -b feature/abhijit-system-tools
     ```
  2. Review `tools/base.py` and `ARCHITECTURE.md`.
  3. Create `tools/test_system.py` using `psutil` and `subprocess`:
     - Fetch CPU %, RAM %, and Battery %.
     - Test launching a standard desktop app (e.g., `notepad.exe` or `calc.exe` on Windows) via Python `subprocess.Popen`.
- **Technical Skill to Master:** *Operating System Process Management.*
  - The difference between `subprocess.run` (blocking, waits for process to close) and `subprocess.Popen` (non-blocking, launches app and lets Python continue).
  - Why launching an app with `subprocess.run` freezes the assistant until you close the app, while `Popen` is asynchronous!
- **Day 1 Acceptance Criteria:**
  - Running `python tools/test_system.py` launches Notepad asynchronously and outputs system RAM/CPU stats in terminal.

---

### 🖥️ Rohit (Frontend & Memory)
- **Today's Goal:** Setup the FastAPI backend skeleton and verify SQLite database creation.
- **Tasks to Complete:**
  1. Pull `main` branch:
     ```powershell
     git checkout -b feature/rohit-backend-memory
     ```
  2. Create `memory/test_db.py`:
     - Initializes a SQLite database file `memory/jarvis.db` using `aiosqlite`.
     - Creates tables: `notes` (`id`, `title`, `content`, `created_at`) and `interactions` (`id`, `role`, `content`, `timestamp`).
     - Inserts a dummy test note and reads it back.
  3. Create a minimal FastAPI app `ui/server.py`:
     - A health check endpoint: `GET /health` returning `{"status": "online", "version": "0.1.0"}`.
- **Technical Skill to Master:** *Relational Data Persistence & Async I/O.*
  - Why use `aiosqlite` instead of standard `sqlite3`? (Standard `sqlite3` blocks Python's async event loop during disk writes; `aiosqlite` keeps the server responsive).
  - What is SQLite WAL (Write-Ahead Logging) mode and why does it speed up concurrent reads?
- **Day 1 Acceptance Criteria:**
  - Running `uvicorn ui.server:app --reload` serves `GET http://127.0.0.1:8000/health` returning JSON `{"status": "online"}`.
  - SQLite database file `memory/jarvis.db` is created with tables verified.

---

### 🤝 Day 1 Evening Sync (15 Minutes)
- **Agenda:** 
  1. Has everyone successfully cloned the repo and activated their virtual environment?
  2. Did anyone get stuck on Python PATH or audio driver permissions?
  3. Confirm that all four branches (`feature/...`) can push to GitHub without conflicts.

### ⚠️ Pitfalls & Gotchas to Avoid on Day 1
- **Do NOT commit `.env`!** Run `git status` before every commit. If you see `.env` listed under "Untracked files", STOP. It belongs in `.gitignore`.
- **Windows ExecutionPolicy error:** If PowerShell blocks activating your venv, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that terminal.
- **PyAudio vs sounddevice:** Avoid `pyaudio` if possible on Windows (requires C++ build tools / portaudio binaries). Prefer `sounddevice` which bundles wheels seamlessly.

---

## 📍 DAY 2: Standalone Component Prototypes

### Daily Theme
Building the independent "atoms" of Jarvis. No complex cross-module wiring yet. Each developer builds their module's core functionality with unit tests.

---

### 👑 Jay (Core Brain)
- **Today's Goal:** Build the interactive CLI chat loop and define system prompts for Jarvis.
- **Tasks to Complete:**
  1. Create `core/brain.py`:
     - Define `JarvisBrain` class with initialization loading `.env` API keys.
     - System prompt: Set persona (helpful, concise, witty, technical, proactive, speaks in brief sentences suitable for voice).
     - Implement `chat(user_input: str) -> str` maintaining a conversation history list (`[{"role": "user", ...}, {"role": "model", ...}]`).
  2. Create a runnable terminal runner `main_cli.py`:
     - Type messages in terminal -> get responses from Jarvis.
     - Exit on `quit` or `exit`.
- **Technical Skill to Master:** *System Prompt Engineering & Conversation State.*
  - How system instructions anchor the LLM's identity.
  - Multi-turn conversation representation: passing past turns so the model understands context like "Who is Elon Musk?" followed by "How old is he?".
- **Day 2 Acceptance Criteria:**
  - In `main_cli.py`, you can have a 5-turn conversation in terminal where Jarvis remembers previous statements.

---

### 🎙️ Aryan (Voice Engineer)
- **Today's Goal:** Implement Speech-to-Text (STT) transcribe function from microphone input.
- **Tasks to Complete:**
  1. Choose STT engine:
     - *Option A (Fastest to setup & highest accuracy):* Gemini Multimodal Audio API or Groq Whisper Cloud API (instant transcription, 0.2s latency).
     - *Option B (Fully offline):* `faster-whisper` (base or small model running locally on CPU/GPU).
  2. Implement `voice/stt.py`:
     - Function `record_and_transcribe(duration_seconds=5) -> str`.
     - Automatically record audio when called and return the transcribed string.
  3. Create `voice/test_stt.py` to test speaking: *"Jarvis, what time is it?"* and viewing the printed transcription.
- **Technical Skill to Master:** *Speech-to-Text Pipelines & Audio Tokenization.*
  - How Whisper converts spectrogram audio frames into text tokens.
  - Trade-offs between local models (resource-heavy on CPU) vs fast API inference (requires internet, minimal CPU load).
- **Day 2 Acceptance Criteria:**
  - Running `python voice/test_stt.py`, you speak into your laptop mic for 4 seconds, and terminal prints the exact words you said with >90% accuracy.

---

### ⚙️ Abhijit (System & Automation)
- **Today's Goal:** Implement the first 3 standardized system tools adhering to `BaseTool`.
- **Tasks to Complete:**
  1. Create `tools/system_tools.py`:
     - **Tool 1: `GetSystemStatsTool`** (already defined in `ARCHITECTURE.md`): reports CPU, RAM %, battery.
     - **Tool 2: `OpenAppTool`**: accepts `app_name: str` (e.g. "chrome", "notepad", "code", "spotify"). Uses a lookup dictionary of common application executable paths on Windows and runs `subprocess.Popen`.
     - **Tool 3: `ListDirectoryTool`**: accepts `path: str` (defaults to user Desktop or working dir) and safely returns list of files/folders.
  2. Create `tools/registry.py`:
     - A dictionary / registry class that stores all available tools: `{"get_system_stats": GetSystemStatsTool(), ...}`.
     - Function `execute_tool(name: str, arguments: dict) -> ToolResult`.
- **Technical Skill to Master:** *Subprocess Sandboxing & Defensive Input Sanitization.*
  - Never run `subprocess.Popen(command, shell=True)` with unvalidated user input! Explain why `shell=True` allows shell injection (e.g., `calc.exe & del /f /q *`). Always use tokenized lists: `subprocess.Popen(["notepad.exe"])`.
- **Day 2 Acceptance Criteria:**
  - Running `python -c "from tools.registry import execute_tool; print(execute_tool('get_system_stats', {}))"` outputs valid JSON stats.
  - Running `execute_tool('open_app', {'app_name': 'notepad'})` instantly opens Notepad on your desktop.

---

### 🖥️ Rohit (Frontend & Memory)
- **Today's Goal:** Implement Note taking and Memory CRUD in SQLite, and build REST endpoints.
- **Tasks to Complete:**
  1. Create `memory/storage.py`:
     - Class `MemoryManager`:
       - `add_note(title: str, content: str) -> int`
       - `search_notes(keyword: str) -> List[Dict]`
       - `get_recent_notes(limit: int = 5) -> List[Dict]`
       - `save_chat_turn(role: str, message: str)`
       - `get_recent_chat_history(limit: int = 10) -> List[Dict]`
  2. Expose in `ui/server.py`:
     - `POST /api/notes` (creates a note)
     - `GET /api/notes` (fetches recent notes)
     - `GET /api/stats` (calls Abhijit's `GetSystemStatsTool` to prove module interop!)
- **Technical Skill to Master:** *REST API Design & Separation of Concerns.*
  - What HTTP status codes mean (200 OK, 201 Created, 400 Bad Request, 500 Internal Error).
  - Pydantic models for request validation (`class NoteCreateRequest(BaseModel)`).
- **Day 2 Acceptance Criteria:**
  - Open Swagger docs in your browser at `http://127.0.0.1:8000/docs`.
  - Use the interactive UI to create a note *"Buy milk"*, fetch notes, and see it stored permanently in `jarvis.db`.

---

### 🤝 Day 2 Evening Sync (15 Minutes)
- **Agenda:**
  1. Demo round: Everyone shares screen for 2 minutes to show their Day 2 milestone working.
  2. Code review check: Does Abhijit's `tools` match what Jay needs for tomorrow's tool-calling loop?
  3. Commit and push Day 2 branches.

---

## 📍 DAY 3: The Tool-Calling Loop & Feedback Engines

### Daily Theme
Connecting the Brain to the Hand. Jay connects the LLM to Abhijit's tools so the model can autonomously decide to run commands on the laptop. Aryan creates voice output (TTS).

---

### 👑 Jay (Core Brain)
- **Today's Goal:** Implement the Autonomous Function-Calling Loop (ReAct / Tool Execution Loop).
- **Tasks to Complete:**
  1. In `core/brain.py`, register tools with the LLM API:
     - Convert Abhijit's `tools.registry` schemas into Gemini/OpenAI Tool declarations.
  2. Implement the **Execution Loop**:
     - Step 1: Send user prompt to LLM along with available tool schemas.
     - Step 2: Check if LLM response is text OR a function call request (`tool_calls`).
     - Step 3: If function call, parse tool name & arguments.
     - Step 4: Execute tool via `registry.execute_tool(name, args)` and get `ToolResult`.
     - Step 5: Append the `ToolResult` as a `tool_response` back to the conversation.
     - Step 6: Call LLM again so it can explain the result to the user in natural language!
- **Technical Skill to Master:** *The ReAct (Reasoning + Acting) Agent Pattern.*
  - Understand how autonomous AI agents work: the LLM itself doesn't click buttons or read RAM; it emits a structured plan, the Python runtime executes it, and feeds reality back to the model.
- **Day 3 Acceptance Criteria:**
  - In `main_cli.py`, you type: *"Jarvis, check my RAM usage and open Notepad."*
  - The brain autonomously invokes `get_system_stats`, receives the RAM number, invokes `open_app(app_name="notepad")`, Notepad pops up, and Jarvis replies: *"I've opened Notepad for you, and your RAM usage is currently at 42%."*

---

### 🎙️ Aryan (Voice Engineer)
- **Today's Goal:** Implement ultra-fast Text-to-Speech (TTS) so Jarvis can speak back.
- **Tasks to Complete:**
  1. Install `edge-tts` (Microsoft Edge neural speech - free, realistic, high quality, requires no local GPU).
     ```powershell
     pip install edge-tts
     ```
  2. Implement `voice/tts.py`:
     - Function `speak(text: str)`:
       - Uses `edge_tts.Communicate(text, voice="en-US-GuyNeural")` (or `en-US-ChristopherNeural` or `en-GB-RyanNeural`).
       - Streams or saves audio to a temporary memory buffer or `temp_audio/output.wav`.
       - Plays audio through speakers via `sounddevice` or `playsound3`.
  3. Test in `voice/test_tts.py`:
     - Test Jarvis speaking: *"Good evening, Jay. All systems are operational."*
- **Technical Skill to Master:** *Audio Synthesis & Latency Tuning.*
  - Why is TTS latency crucial? (A 2-second delay before speaking feels robotic and awkward; aim for <500ms time-to-first-sound).
  - Neural vs Formant synthesis: how deep learning models generate natural human prosody and intonation.
- **Day 3 Acceptance Criteria:**
  - Running `python voice/test_tts.py` speaks out crisp, natural human voice in under 1 second without audio clipping.

---

### ⚙️ Abhijit (System & Automation)
- **Today's Goal:** Implement File Operations with Safety Guardrails & Confirmation.
- **Tasks to Complete:**
  1. Create `tools/file_tools.py`:
     - **Tool 4: `ReadFileTool`**: reads text from a given file path.
     - **Tool 5: `WriteFileTool`**: writes or appends text to a file.
     - **Tool 6: `CreateFolderTool`**: creates a directory.
  2. Implement the **Safety Guardrail Engine** (`tools/safety.py`):
     - Restrict file modifications to a safe directory (e.g. `d:/engineers/Project - A/sandbox` or User's Documents) during testing.
     - Block dangerous paths (e.g., `C:\Windows`, `C:\Program Files`).
     - If an action tries to delete or overwrite an existing file, require an explicit user prompt: `[CONFIRMATION REQUIRED]: Are you sure you want to overwrite X? (y/n)`.
- **Technical Skill to Master:** *Software Security & Principle of Least Privilege.*
  - Why autonomous agents can be dangerous if given unlimited write/delete access.
  - Designing a permission escalation model where read actions are auto-approved, but write/delete actions require authorization.
- **Day 3 Acceptance Criteria:**
  - Attempting to write a file in the sandbox directory works.
  - Attempting to overwrite a file prompts the user for confirmation.
  - Attempting to write into `C:\Windows\System32` returns a clean `ToolResult(success=False, message="Permission Denied: System directory protected.")`.

---

### 🖥️ Rohit (Frontend & Memory)
- **Today's Goal:** Build the WebSocket bridge for live real-time bidirectional messaging.
- **Tasks to Complete:**
  1. In `ui/server.py`, create a WebSocket endpoint: `@app.websocket("/ws/jarvis")`.
  2. Define message schemas:
     - Client -> Server: `{"action": "send_message", "text": "What is my CPU?"}`
     - Server -> Client: `{"type": "status", "data": "executing_tool: get_system_stats"}` followed by `{"type": "response", "data": "Your CPU usage is 12%."}`.
  3. Build a simple HTML/CSS/JS or React test page in `ui/index.html` to connect to the WebSocket and verify chat messaging in a real browser tab.
- **Technical Skill to Master:** *WebSockets vs HTTP Polling.*
  - Why HTTP request-response is unsuitable for interactive voice/chat assistants (the server cannot push events like "thinking..." or "tool starting" without WebSockets).
  - Managing WebSocket connection lifecycles (connect, ping/pong, disconnect, reconnect).
- **Day 3 Acceptance Criteria:**
  - Open `http://127.0.0.1:8000` in Chrome/Edge, type a message in the browser UI, and receive a response pushed through the WebSocket.

---

### 🤝 Day 3 Evening Sync (15 Minutes)
- **Agenda:**
  1. Tomorrow is Integration Day 1! Review PRs that need to be merged into `main`.
  2. Jay reviews Abhijit's `tools/` PR and Rohit's `ui/` PR.
  3. Ensure no code conflicts exist before tomorrow morning.

---

## 📍 DAY 4: INTEGRATION MILESTONE 1 (The Text-Only MVP)

### Daily Theme
**First Major Milestone!** Merge everyone's code into `main`. Build the complete end-to-end loop: Type into Rohit's UI -> routes to Jay's Brain -> executes Abhijit's Tools -> logs into Rohit's SQLite DB -> displays in UI.

---

### 👑 Jay (Core Brain)
- **Today's Goal:** Coordinate the merge, resolve any import issues, and connect Brain to Rohit's WebSocket server.
- **Tasks to Complete:**
  1. Review and approve PRs from Abhijit, Rohit, and Aryan on GitHub.
  2. Merge all branches into `main`.
  3. Wire `JarvisBrain` into `ui/server.py` so that WebSocket messages trigger the actual brain tool-calling loop.
  4. Ensure graceful error handling: if an LLM API error or tool failure occurs, the server doesn't crash.
- **Technical Skill to Master:** *Git Merge Strategies & PR Code Review.*
  - How to resolve merge conflicts cleanly in VS Code / Antigravity.
  - Verifying semantic consistency across different authors' code.

---

### 🎙️ Aryan (Voice Engineer)
- **Today's Goal:** Create the standalone Voice Loop (`voice/voice_pipeline.py`).
- **Tasks to Complete:**
  1. Combine `stt.py` and `tts.py` into a unified script.
  2. Create a test runner where you speak a sentence -> it transcribes -> echoes it back using TTS.
  3. Measure latency: how many milliseconds between when speech stops and when TTS audio begins?
- **Technical Skill to Master:** *Voice Activity Detection (VAD) & Latency Profiling.*
  - How to automatically detect when the user has stopped speaking without waiting for a fixed 5-second timer (using energy threshold or Silero VAD).

---

### ⚙️ Abhijit (System & Automation)
- **Today's Goal:** Write the comprehensive test suite for all system tools.
- **Tasks to Complete:**
  1. Create `tests/test_tools.py`:
     - Test `GetSystemStatsTool` returns expected dictionary keys (`cpu_usage_percent`, `ram_usage_percent`).
     - Test `OpenAppTool` handles nonexistent applications gracefully without crashing.
     - Test `ListDirectoryTool` with valid and invalid paths.
     - Test `WriteFileTool` and `ReadFileTool` with temporary files.
  2. Run `pytest` or `python -m unittest tests/test_tools.py` and ensure 100% tests pass.
- **Technical Skill to Master:** *Automated Unit Testing & Mocking.*
  - Why tests are the safety net of high-velocity teams: writing tests ensures no future commit accidentally breaks existing tools.

---

### 🖥️ Rohit (Frontend & Memory)
- **Today's Goal:** Enhance the UI with a live Terminal / Chat HUD feed showing tool execution events.
- **Tasks to Complete:**
  1. Style the UI with a modern dark theme (Jarvis aesthetic: dark slate background `#0f172a`, cyan accents `#06b6d4`, monospace terminal font).
  2. Add visual status badges:
     - 🟢 *Online*
     - 🟡 *Thinking...*
     - ⚙️ *Executing Tool: [tool_name]*
     - 🔵 *Speaking*
  3. Display system stats widget in top corner (pulling from `GetSystemStatsTool`).
- **Technical Skill to Master:** *Reactive UI State Management.*
  - How to manage asynchronous UI state updates without re-rendering the entire DOM.

---

### 🏆 Day 4 Milestone Demo (30 Minutes - All Hands)
- **The Team Gathers:**
  1. Launch the server: `python -m uvicorn ui.server:app --reload`.
  2. Open the browser UI at `http://127.0.0.1:8000`.
  3. Type: *"Jarvis, create a note titled 'Project Plan' with content 'Finish Phase 1', and tell me how much RAM my laptop has left."*
  4. **Verification:**
     - Note is inserted into SQLite database.
     - System tool fetches RAM statistics.
     - UI displays real-time execution steps.
     - Final response displays cleanly.
  - 🎉 **Celebrate:** You have built a functioning autonomous AI desktop agent!

---

## 📍 DAY 5: Voice Meets Brain & Long-Term Memory

### Daily Theme
Voice integration & semantic recall. Voice replaces the keyboard as the input channel, and Rohit adds contextual memory so Jarvis remembers user preferences across sessions.

---

### 👑 Jay & 🎙️ Aryan (Pair Programming)
- **Today's Goal:** Plug Aryan's Voice Pipeline into Jay's Brain loop.
- **Tasks to Complete:**
  1. Create `voice_assistant.py` (The Voice Runtime):
     - Step 1: Aryan's STT captures user voice command.
     - Step 2: Passes text directly to `Jay's brain.chat(text)`.
     - Step 3: Brain executes tools if needed.
     - Step 4: Assistant text is sent directly to `Aryan's tts.speak(response)`.
  2. Add basic Wake-Word detection or Push-to-Talk:
     - *Push-to-Talk (easiest & most reliable):* Press `Spacebar` or `Ctrl+Shift+J` to talk.
     - *Wake-Word:* Keyword detector listening for "Jarvis".
- **Technical Skill to Master:** *Streaming Audio & Async Pipeline Orchestration.*
  - Handling interruptions: what happens if the user speaks while Jarvis is still reading a long response? (Cancelling the TTS stream).

---

### ⚙️ Abhijit (System & Automation)
- **Today's Goal:** Add Screen Awareness / Screenshot Tool.
- **Tasks to Complete:**
  1. Create `tools/screen_tools.py`:
     - **Tool 7: `CaptureScreenTool`**:
       - Uses `pyautogui.screenshot()` or `pillow` to capture the current laptop screen.
       - Saves to `cache/screen.png`.
       - Returns file path and image dimensions.
  2. (Optional/Bonus) Add OCR or Multimodal Vision:
     - Allow Jay's brain to pass `cache/screen.png` to Gemini's multimodal vision model so Jarvis can "see" what is on the user's screen (e.g., *"What error is showing on my screen?"*).
- **Technical Skill to Master:** *Multimodal AI & Computer Vision Primitives.*
  - How multimodal models process image tokens alongside text tokens.
  - Image compression: resizing large 4K screenshots to 1080p to minimize token latency.

---

### 🖥️ Rohit (Frontend & Memory)
- **Today's Goal:** Add Semantic Search / Vector Memory using ChromaDB.
- **Tasks to Complete:**
  1. Install ChromaDB: `pip install chromadb`.
  2. Create `memory/vector_store.py`:
     - Initialize local embedded ChromaDB in `memory/chroma_db`.
     - Method `add_memory(fact: str, category: str)`.
     - Method `search_relevant_memories(query: str, n_results: int = 3) -> List[str]`.
  3. Connect to Jay's Brain:
     - When user says: *"Remember that my favorite programming language is Rust"*, brain calls `memory.add_memory(...)`.
     - When user asks: *"What programming language do I like?"*, brain queries vector store, retrieves the fact, and answers accurately!
- **Technical Skill to Master:** *Embeddings, Vector Databases & RAG (Retrieval-Augmented Generation).*
  - What are high-dimensional vector embeddings?
  - How cosine similarity finds semantically related knowledge even when exact keywords don't match.

---

### 🤝 Day 5 Evening Sync (15 Minutes)
- **Agenda:**
  1. Test the Voice + Brain loop: speak a command and hear Jarvis respond.
  2. Test memory persistence: restart the script and verify Jarvis still remembers facts from 10 minutes ago.

---

## 📍 DAY 6: Hardening, Latency Optimization & UI Polish

### Daily Theme
Making the assistant fast, stable, and beautiful. Eliminating awkward lags and preventing crashes.

---

### 👑 Jay (Core Brain)
- **Today's Goal:** Implement Streaming Responses and Fallback Error Handling.
- **Tasks to Complete:**
  1. Update `brain.chat()` to support streaming generator (`yield chunk`).
  2. Add network retry logic: if the LLM API throws a 429 (rate limit) or 503 (timeout), implement exponential backoff retry.
  3. Ensure that if a tool fails (e.g., path not found), the brain explains the error helpfully to the user instead of throwing an unhandled Python traceback.
- **Technical Skill to Master:** *Resilience & Fault Tolerance in Distributed Systems.*

---

### 🎙️ Aryan (Voice Engineer)
- **Today's Goal:** Sentence-level TTS Streaming for zero perceived latency.
- **Tasks to Complete:**
  1. Connect to Jay's streaming generator.
  2. Split incoming text tokens by punctuation (`.`, `!`, `?`).
  3. As soon as the first sentence finishes generating, immediately send it to TTS to start speaking, while the LLM is still generating the second sentence!
- **Technical Skill to Master:** *Pipelined Concurrency.*
  - How pipelining drops perceived conversational latency from 4.5 seconds to under 0.8 seconds.

---

### ⚙️ Abhijit (System & Automation)
- **Today's Goal:** Safe Command Execution & Whitelist Manager.
- **Tasks to Complete:**
  1. Create `tools/shell_tools.py`:
     - **Tool 8: `RunShellCommandTool`**.
     - Implement a strict whitelist of safe read-only commands (e.g. `dir`, `ls`, `git status`, `ping`, `ipconfig`, `python --version`).
     - Block dangerous commands (`format`, `del /s`, `rmdir`, `shutdown`).
  2. Create configuration file `tools/config.json` allowing user to customize allowed apps and aliases.
- **Technical Skill to Master:** *Command Injection Defenses & Whitelisting.*

---

### 🖥️ Rohit (Frontend & Memory)
- **Today's Goal:** Complete the Jarvis HUD Dashboard with real-time visual feedback.
- **Tasks to Complete:**
  1. Add audio wave visualizer effect when Jarvis is speaking (CSS / Canvas).
  2. Add quick-action buttons on the HUD (e.g. "Check Stats", "Summarize Screen", "List Notes").
  3. Display active tools currently loaded in the system.
- **Technical Skill to Master:** *Audio Visualization (Web Audio API / CSS Animation).*

---

### 🤝 Day 6 Evening Sync (15 Minutes)
- **Agenda:**
  1. Dry run of the complete system ahead of Day 7 final demo.
  2. Fix any remaining bugs or edge-case crashes.

---

## 📍 DAY 7: The Grand Finale – Demo, Documentation & Review

### Daily Theme
Polishing the deliverable, recording the demo, celebrating success, and preparing for Phase 2.

---

### 👑 All Hands (Collaborative Tasks)
1. **Run Full Verification Suite:**
   - Execute unit tests: `pytest tests/`.
   - Test voice command: *"Hey Jarvis, what's my CPU and open VS Code."*
   - Test memory: *"Jarvis, note down that our viva is on November 20th."*
   - Test screen: *"Jarvis, capture my screen and describe it."*
2. **Write Professional `README.md` (Jay leading):**
   - Project Overview with architecture diagram.
   - 3-step setup guide (`git clone`, `pip install`, `python main.py`).
   - Team credits and role breakdown.
3. **Record a 2-Minute Demo Video:**
   - Aryan/Jay records screen + mic demonstrating voice control, app opening, telemetry check, and HUD UI.
   - Perfect portfolio proof for GitHub, LinkedIn, and university evaluations!
4. **Week 1 Retrospective (45 Minutes):**
   - *What went surprisingly well?*
   - *What was the hardest technical blocker?*
   - *What did each person learn that they didn't know 7 days ago?*

---

## 🧠 Technical Knowledge Checklist: What You Will Know by Sunday Night

| Team Member | Core Skills Mastered by End of Week 1 |
| :--- | :--- |
| **Jay** | LLM ReAct agent loops, Function calling JSON schemas, Streaming generators, Context management, Architecture governance |
| **Aryan** | Digital signal processing (DSP), 16kHz audio sampling, Whisper STT pipelines, Neural TTS synthesis, Latency optimization |
| **Abhijit** | Windows process management (`subprocess`), Telemetry APIs (`psutil`), Least-privilege security sandboxing, Defensive input validation |
| **Rohit** | Full-stack WebSockets, FastAPI async event loops, SQLite WAL mode, ChromaDB vector embeddings & cosine similarity, Reactive UI design |

---

## 🚀 Ready to Launch?
Tomorrow morning, **Jay** runs the Day 1 commands, pushes the repository, and everyone begins with their respective Step 0 tasks. Happy engineering!
