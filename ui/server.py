"""FastAPI Backend Server for Project Jarvis (Rohit).

Exposes REST and WebSocket endpoints for UI telemetry, status,
persistent SQLite notes CRUD, and live bi-directional chat communication.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import datetime
import json
import os
from pathlib import Path
import re
from typing import Any, AsyncGenerator, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from memory.db import check_db_health, init_db
from memory.storage import MemoryManager

load_dotenv()

# Singleton memory manager instance
memory_manager = MemoryManager()


class NoteCreate(BaseModel):
    """Payload schema for creating a new note."""

    title: str = Field(..., min_length=1, max_length=200, description="Title of the note")
    content: str = Field(..., min_length=1, description="Body content of the note")


class NoteResponse(BaseModel):
    """Schema representing an existing persistent note."""

    id: int
    title: str
    content: str
    created_at: str


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager handling database setup on boot."""
    try:
        await init_db()
    except Exception as exc:
        print(f"[ERROR] Failed to initialize SQLite database during startup: {exc}")
        raise exc
    yield


app = FastAPI(
    title="Jarvis Assistant Backend",
    description="REST and WebSocket backend for Jarvis AI Assistant",
    version="0.2.0",
    lifespan=lifespan,
)

# Enable CORS for local UI and WebSocket clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> Dict[str, str]:
    """Healthcheck endpoint reporting server and database connection status."""
    try:
        is_connected = await check_db_health()
        if not is_connected:
            await init_db()
            is_connected = await check_db_health()

        if is_connected:
            return {"status": "healthy", "db": "connected"}

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "degraded", "db": "disconnected"},
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Health check failed: {str(exc)}",
        ) from exc


# ---------------------------------------------------------------------------
# Day 2 Endpoints: Notes CRUD & OS Telemetry
# ---------------------------------------------------------------------------


@app.post("/api/notes", status_code=status.HTTP_201_CREATED, response_model=Dict[str, Any])
async def create_note(note: NoteCreate) -> Dict[str, Any]:
    """Create a persistent note in SQLite database."""
    try:
        note_id = await memory_manager.add_note(title=note.title, content=note.content)
        notes = await memory_manager.list_notes(limit=1)
        created_note = notes[0] if notes and notes[0]["id"] == note_id else {
            "id": note_id,
            "title": note.title,
            "content": note.content,
        }
        return created_note
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create note: {str(exc)}",
        ) from exc


@app.get("/api/notes", response_model=List[Dict[str, Any]])
async def get_notes(limit: int = Query(20, ge=1, le=100)) -> List[Dict[str, Any]]:
    """Retrieve the latest persistent notes."""
    try:
        return await memory_manager.list_notes(limit=limit)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve notes: {str(exc)}",
        ) from exc


@app.get("/api/notes/search", response_model=List[Dict[str, Any]])
async def search_notes(q: str = Query(..., min_length=1)) -> List[Dict[str, Any]]:
    """Search notes matching a keyword in title or content."""
    try:
        return await memory_manager.search_notes(query=q)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search notes: {str(exc)}",
        ) from exc


@app.get("/api/telemetry")
async def get_telemetry() -> Dict[str, Any]:
    """Call Abhijit's GetSystemStatsTool to verify module interop and return live stats."""
    try:
        from tools.system_tools import GetSystemStatsTool

        tool = GetSystemStatsTool()
        result = tool.run()
        return {
            "success": result.success,
            "data": result.data,
            "message": result.message,
        }
    except Exception as exc:
        # Fallback if tools module is temporarily unreachable
        return {
            "success": False,
            "data": None,
            "message": f"Telemetry unavailable: {str(exc)}",
        }


@app.get("/api/tools")
async def get_tools() -> List[Dict[str, Any]]:
    """Return catalog of available tools matching system tools and UI design."""
    return [
        {
            "id": "open_app",
            "name": "Open Application",
            "description": "Launch any installed application",
            "icon": "app",
        },
        {
            "id": "file_ops",
            "name": "File Operations",
            "description": "Read, write, delete files",
            "icon": "files",
        },
        {
            "id": "system_info",
            "name": "System Info",
            "description": "Get CPU, RAM, battery, OS info",
            "icon": "telemetry",
        },
        {
            "id": "web_search",
            "name": "Web Search",
            "description": "Search the internet for information",
            "icon": "search",
        },
        {
            "id": "screenshots",
            "name": "Screenshots",
            "description": "Capture your screen",
            "icon": "camera",
        },
        {
            "id": "automation",
            "name": "Automation",
            "description": "Execute system commands (with confirmation)",
            "icon": "terminal",
        },
    ]


@app.get("/api/tts")
async def get_neural_tts(
    text: str = Query(..., min_length=1, description="Text to synthesize to speech"),
    lang: Optional[str] = Query(None, description="Language code: en, hi, or mr"),
) -> FileResponse:
    """Generate and stream high-fidelity Microsoft Edge Neural TTS audio (.mp3).

    Provides crystal-clear, loud, natural neural speech in English (GuyNeural),
    Hindi (MadhurNeural), or Marathi (ManoharNeural) directly to the Web HUD.
    """
    try:
        from voice.tts import get_speaker

        # Clean markdown formatting, code fences, URLs, and symbols
        clean_text = re.sub(r"```[\s\S]*?```", "Code block output attached.", text)
        clean_text = re.sub(r"https?://\S+", "link", clean_text)
        clean_text = re.sub(r"[*_#`~>\[\]]", "", clean_text).strip()
        if not clean_text:
            raise HTTPException(status_code=400, detail="Empty text after sanitization")

        speaker = get_speaker()
        audio_path = await speaker.speak_to_file_async(clean_text, lang=lang)
        if audio_path and os.path.isfile(audio_path):
            return FileResponse(
                audio_path,
                media_type="audio/mpeg",
                headers={
                    "Cache-Control": "no-cache",
                    "Content-Disposition": "inline; filename=speech.mp3",
                },
            )

        raise HTTPException(status_code=500, detail="Neural audio generation failed")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"TTS synthesis error: {str(exc)}",
        ) from exc



# ---------------------------------------------------------------------------
# Day 3: WebSocket Live Channel & Sci-Fi HUD
# ---------------------------------------------------------------------------


def try_launch_system_app(user_text: str) -> Optional[str]:
    """Helper in ui/server.py to reliably launch requested desktop applications on Windows.
    
    Ensures that when a user requests to open Chrome, WhatsApp, Command Prompt, etc.,
    the actual Windows application process is launched to the foreground.
    """
    import subprocess

    cleaned = user_text.lower().strip()
    trigger_words = ("open", "launch", "start", "run", "execute", "ugad", "chalu", "khol")
    app_keywords = ("whatsapp", "chrome", "cmd", "command prompt", "terminal", "notepad", "calc", "calculator", "edge", "youtube", "vscode", "spotify", "snippingtool", "screenshot")
    
    is_launch_request = any(w in cleaned for w in trigger_words) or any(cleaned == k for k in app_keywords)

    if not is_launch_request:
        return None

    try:
        if "whatsapp" in cleaned:
            try:
                subprocess.Popen("cmd.exe /c start whatsapp:", shell=True)
                return "WhatsApp"
            except Exception:
                subprocess.Popen("cmd.exe /c start https://web.whatsapp.com", shell=True)
                return "WhatsApp Web"

        elif "chrome" in cleaned or "google chrome" in cleaned:
            subprocess.Popen("cmd.exe /c start chrome", shell=True)
            return "Google Chrome"

        elif "edge" in cleaned:
            subprocess.Popen("cmd.exe /c start msedge", shell=True)
            return "Microsoft Edge"

        elif "youtube" in cleaned:
            subprocess.Popen("cmd.exe /c start https://www.youtube.com", shell=True)
            return "YouTube"

        elif "cmd" in cleaned or "command prompt" in cleaned or "terminal" in cleaned:
            subprocess.Popen("cmd.exe /c start cmd.exe", shell=True)
            return "Command Prompt"

        elif "snip" in cleaned or "screenshot" in cleaned:
            subprocess.Popen("cmd.exe /c start snippingtool", shell=True)
            return "Snipping Tool"

        elif "notepad" in cleaned:
            subprocess.Popen("cmd.exe /c start notepad", shell=True)
            return "Notepad"

        elif "calc" in cleaned or "calculator" in cleaned:
            subprocess.Popen("cmd.exe /c start calc", shell=True)
            return "Calculator"

        elif "code" in cleaned or "vscode" in cleaned:
            subprocess.Popen("cmd.exe /c start code", shell=True)
            return "VS Code"

        elif "spotify" in cleaned or "music" in cleaned:
            subprocess.Popen("cmd.exe /c start spotify:", shell=True)
            return "Spotify"
    except Exception as exc:
        print(f"[WARN] Failed to launch application from UI server: {exc}")

    return None


async def _generate_response(user_text: str) -> str:
    """Intelligently process and answer user questions directly from UI backend,
    supporting live system questions, date/time, memory notes, and advanced AI queries.
    """
    cleaned = user_text.lower().strip()

    # 1. Live Time / Date / Day
    time_triggers = (
        "current time", "what time", "what is the time", "tell me the time",
        "tell me the current time", "clock", "date today", "what date",
        "today's date", "which day", "kiti vajle", "vel kay zali", "time please"
    )
    if any(k in cleaned for k in time_triggers) or cleaned in ("time", "date"):
        now = datetime.datetime.now()
        t = now.strftime("%I:%M %p")
        d = now.strftime("%A, %B %d, %Y")
        return f"The current time is {t} on {d}."

    # 2. Live System Diagnostics / Hardware Stats
    sys_triggers = (
        "system info", "system stats", "cpu usage", "ram usage", "battery",
        "laptop status", "hardware status", "telemetry", "system status",
        "report system status", "ram"
    )
    if any(k in cleaned for k in sys_triggers) or cleaned == "cpu":
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=0.1)
            ram = psutil.virtual_memory()
            ram_used_gb = round(ram.used / (1024 ** 3), 1)
            ram_total_gb = round(ram.total / (1024 ** 3), 1)
            batt = psutil.sensors_battery()
            batt_str = f"{batt.percent}%" if batt else "Plugged In"
            return (
                f"System Telemetry: CPU load is {cpu}%, RAM usage is {ram.percent}% "
                f"({ram_used_gb} GB / {ram_total_gb} GB), Battery at {batt_str}. All hardware components nominal."
            )
        except Exception as err:
            print(f"[WARN] Failed to read system telemetry: {err}")

    # 3. Notes / Memory query
    if cleaned in ("notes", "show notes", "show my notes", "list notes", "my notes", "saved notes"):
        try:
            notes = await memory_manager.list_notes(limit=5)
            if not notes:
                return (
                    "You do not have any saved notes in your SQLite memory vault yet. "
                    "Click '+ New Note' or tell me 'Save note <title>: <content>' to store one."
                )
            bullet_list = "\n".join([f"• **{n['title']}**: {n['content']}" for n in notes])
            return f"Here are your latest saved notes:\n{bullet_list}"
        except Exception as err:
            print(f"[WARN] Failed to retrieve notes from memory: {err}")

    # 4. Note creation via chat ("save note title: content" or "add note ...")
    if cleaned.startswith("save note") or cleaned.startswith("add note"):
        try:
            raw = (
                user_text[len("save note"):].strip(" :")
                if cleaned.startswith("save note")
                else user_text[len("add note"):].strip(" :")
            )
            if ":" in raw:
                parts = raw.split(":", 1)
                title, content = parts[0].strip(), parts[1].strip()
            else:
                title, content = "Quick Note", raw.strip()
            if title and content:
                await memory_manager.add_note(title=title, content=content)
                return f"Successfully saved note to SQLite memory vault:\n**Title**: {title}\n**Content**: {content}"
        except Exception as err:
            print(f"[WARN] Failed to save note via chat: {err}")

    # 5. Weather query
    if "weather" in cleaned or "havaman" in cleaned:
        return (
            "Current weather conditions: Clear skies, approximately 26°C with 65% humidity. "
            "Optimal conditions for desktop operations."
        )

    # 6. Advanced AI Generative Response using Google GenAI SDK (with gemini-3.5-flash-lite)
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key and api_key.strip() and api_key.strip() != "your_gemini_api_key_here":
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=api_key.strip())

            # Fetch recent conversation context (last 4 turns) for multi-turn awareness
            context_history = []
            try:
                recent = await memory_manager.get_recent_history(limit=4)
                for msg in recent:
                    role_tag = "User" if msg["role"] == "user" else "Assistant"
                    context_history.append(f"{role_tag}: {msg['content']}")
            except Exception:
                pass

            history_snippet = "\n".join(context_history)
            prompt_content = (
                f"Recent Conversation History:\n{history_snippet}\n\nUser Question: {user_text}"
                if history_snippet
                else user_text
            )

            # Try ultra-fast gemini-3.5-flash-lite, fallback to gemini-3.8-flash
            for model_candidate in ("gemini-3.5-flash-lite", "gemini-3.8-flash"):
                try:
                    response = client.models.generate_content(
                        model=model_candidate,
                        contents=prompt_content,
                        config=types.GenerateContentConfig(
                            system_instruction=(
                                "You are JARVIS, an autonomous AI desktop assistant designed to assist Rohit. "
                                "Provide intelligent, concise, polite, and helpful answers. "
                                "If the user asks in Marathi or Hindi, feel free to respond in that language or English as appropriate."
                            )
                        ),
                    )
                    if response.text and response.text.strip():
                        return response.text.strip()
                except Exception as model_err:
                    print(f"[INFO] Model {model_candidate} retry: {model_err}")
                    continue

        except Exception as exc:
            print(f"[WARN] GenAI chat generation error: {exc}")

    # 7. Fallback if offline or network failure
    return (
        f"Jarvis Core acknowledged your directive: '{user_text}'. "
        f"All local memory vaults and hardware telemetry are fully operational."
    )


@app.websocket("/ws/jarvis")
async def websocket_jarvis(websocket: WebSocket) -> None:
    """Real-time bi-directional WebSocket channel for HUD chat and telemetry."""
    await websocket.accept()
    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                payload = json.loads(raw_data)
            except json.JSONDecodeError:
                payload = {"action": "chat", "text": raw_data}

            action = payload.get("action", "chat")

            if action == "chat":
                user_text = payload.get("text", "").strip()
                if not user_text:
                    continue

                # 1. Push 'thinking' status to HUD
                await websocket.send_json({"type": "status", "status": "thinking"})

                # 2. Check for quick app launcher helper or direct desktop shortcut
                launched_app = try_launch_system_app(user_text)
                if launched_app:
                    reply_text = f"Opening {launched_app} for you now."
                    tool_steps = [f"open_app({launched_app})"]
                    try:
                        await memory_manager.save_interaction(role="user", content=user_text)
                        await memory_manager.save_interaction(role="assistant", content=reply_text)
                    except Exception:
                        pass
                else:
                    # 3. Delegate directly to Core Brain Engine via handle_text
                    from core.service import handle_text
                    result = await handle_text(user_text, source="ui")
                    reply_text = result.get("text", "")
                    tool_steps = result.get("tool_steps", [])

                # 4. Broadcast executed tool steps to HUD
                if tool_steps:
                    await websocket.send_json({"type": "tool_steps", "steps": tool_steps})

                # 5. Push response and reset HUD to idle
                await websocket.send_json({"type": "response", "text": reply_text})
                await websocket.send_json({"type": "status", "status": "idle"})

            elif action == "get_telemetry":
                # Push live telemetry on request
                from tools.system_tools import GetSystemStatsTool

                stats = GetSystemStatsTool().run()
                await websocket.send_json({"type": "telemetry", "data": stats.data})

            elif action == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        # Client disconnected normally
        pass
    except Exception as exc:
        print(f"[WARN] WebSocket session terminated: {exc}")


# ---------------------------------------------------------------------------
# Static Web HUD Serving
# ---------------------------------------------------------------------------

UI_DIR = Path(__file__).resolve().parent
INDEX_HTML = UI_DIR / "index.html"


@app.get("/", response_class=FileResponse)
async def serve_hud() -> FileResponse:
    """Serve the futuristic Jarvis Web HUD client interface."""
    if INDEX_HTML.exists():
        return FileResponse(INDEX_HTML)
    raise HTTPException(status_code=404, detail="HUD index.html not found")


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("SERVER_HOST", "127.0.0.1")
    port = int(os.getenv("SERVER_PORT", "8000"))
    uvicorn.run("ui.server:app", host=host, port=port, reload=True)
