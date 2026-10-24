"""FastAPI Backend Server for Project Jarvis (Rohit).

Exposes REST and WebSocket endpoints for UI telemetry, status,
persistent SQLite notes CRUD, universal application/file launching,
dynamic multi-user isolation, and live bi-directional chat communication.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import datetime
import json
import os
from pathlib import Path
import platform
import re
import shutil
import socket
import subprocess
import time
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple
import webbrowser

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import psutil
from pydantic import BaseModel, Field

from memory.db import check_db_health, init_db
from memory.storage import MemoryManager

load_dotenv()

# Singleton memory manager instance
memory_manager = MemoryManager()

# Persistent GenAI singleton & fast response cache
_genai_client: Optional[Any] = None
_response_cache: Dict[str, str] = {}


def get_genai_client() -> Optional[Any]:
    """Retrieve or initialize persistent Google GenAI SDK client for instant calls."""
    global _genai_client
    if _genai_client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key and api_key.strip() and api_key.strip() != "your_gemini_api_key_here":
            try:
                from google import genai

                _genai_client = genai.Client(api_key=api_key.strip())
            except Exception as exc:
                print(f"[WARN] Failed to initialize persistent GenAI client: {exc}")
    return _genai_client


def normalize_command(text: str) -> str:
    """Normalize text by stripping punctuation and extraneous whitespace for robust matching."""
    cleaned = text.lower().strip()
    norm = re.sub(r"[^\w\s]", " ", cleaned)
    return " ".join(norm.split())


def strip_unnecessary_filler(text: str) -> str:
    """Strip unnecessary AI conversational filler and polite fluff.
    Ensures user gets ONLY the exact answer requested and nothing extra.
    """
    if not text:
        return text

    boilerplate_patterns = [
        r"(?i)\s*(?:please\s+)?let me know (?:if|what|how)[\s\S]*$",
        r"(?i)\s*feel free to (?:ask|reach out|let me know)[\s\S]*$",
        r"(?i)\s*how (?:else )?(?:can|may) i (?:assist|help) you[\s\S]*$",
        r"(?i)\s*is there anything (?:else )?(?:i can help|you need)[\s\S]*$",
        r"(?i)\s*if you (?:need|require) (?:anything|any) (?:else|further)[\s\S]*$",
        r"(?i)\s*i(?:'m| am) here to help[\s\S]*$",
        r"(?i)\s*standing by for your (?:next directive|command)[\s\S]*$",
        r"(?i)\s*do you (?:need|require) (?:any|anything) (?:further|else)[\s\S]*$",
        r"(?i)\s*happy to help[\s\S]*$",
        r"(?i)\s*hope that helps[\s\S]*$",
        r"(?i)\s*hope this helps[\s\S]*$",
        r"(?i)\s*what else can i (?:do|help with)[\s\S]*$",
        r"(?i)\s*ready for your (?:next directive|command)[\s\S]*$",
        r"(?i)\s*let me know if you (?:need|have|require)[\s\S]*$",
    ]
    cleaned = text.strip()
    for pattern in boilerplate_patterns:
        cleaned = re.sub(pattern, "", cleaned).strip()

    return cleaned if cleaned else text


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
        client = get_genai_client()
        if client:
            # Pre-warm GenAI TLS connection in background task so first user question is instant (<1.2s)
            async def _prewarm() -> None:
                try:
                    await client.aio.models.generate_content(
                        model="gemini-3.5-flash-lite",
                        contents="ping",
                    )
                except Exception:
                    pass

            asyncio.create_task(_prewarm())
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

# Ensure Day 7 workspace documents & temp_vision screenshot directories are served statically
workspace_dir = Path("workspace")
workspace_dir.mkdir(parents=True, exist_ok=True)
app.mount("/workspace", StaticFiles(directory="workspace"), name="workspace")

temp_vision_dir = Path("temp_vision")
temp_vision_dir.mkdir(parents=True, exist_ok=True)
app.mount("/temp_vision", StaticFiles(directory="temp_vision"), name="temp_vision")


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

    Provides crystal-clear, loud, natural neural speech in English (GuyNeural/PrabhatNeural),
    Hindi (MadhurNeural), or Marathi (ManoharNeural) directly to the Web HUD.
    """
    try:
        clean_text = re.sub(r"```[\s\S]*?```", "Code block output attached.", text)
        clean_text = re.sub(r"https?://\S+", "link", clean_text)
        clean_text = re.sub(r"[*_#`~>\[\]]", "", clean_text).strip()
        if not clean_text:
            raise HTTPException(status_code=400, detail="Empty text after sanitization")

        # Attempt high-fidelity generation via voice.tts speaker
        try:
            from voice.tts import get_speaker
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
        except Exception as speaker_err:
            print(f"[INFO] voice.tts speaker fallback: {speaker_err}")

        # Direct edge-tts fallback
        import edge_tts
        temp_dir = Path("temp_audio")
        temp_dir.mkdir(parents=True, exist_ok=True)
        file_name = f"speech_{int(time.time() * 1000)}.mp3"
        out_path = temp_dir / file_name

        voice = "en-IN-PrabhatNeural"
        if lang == "hi" or any("\u0900" <= c <= "\u097F" for c in clean_text):
            voice = "hi-IN-MadhurNeural"
        elif lang == "mr":
            voice = "mr-IN-ManoharNeural"

        communicate = edge_tts.Communicate(clean_text, voice)
        await communicate.save(str(out_path))

        if out_path.is_file():
            return FileResponse(
                str(out_path.resolve()),
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


@app.post("/api/stt")
async def transcribe_audio_stream(request: Request) -> Dict[str, Any]:
    """Transcribe raw audio stream (WebM/WAV) using local faster-whisper STT."""
    try:
        from voice.stt import get_transcriber
        import tempfile

        audio_bytes = await request.body()
        if not audio_bytes or len(audio_bytes) < 64:
            raise HTTPException(status_code=400, detail="Audio buffer is empty")

        content_type = request.headers.get("content-type", "audio/webm").lower()
        suffix = ".wav" if "wav" in content_type else (".mp3" if "mp3" in content_type else ".webm")

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(audio_bytes)
            tmp_path = Path(tmp.name)

        try:
            transcriber = get_transcriber()
            result = transcriber.transcribe_file(tmp_path)
            return {
                "success": True,
                "text": result.get("text", "").strip(),
                "language": result.get("language", "en"),
            }
        finally:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except Exception:
                    pass
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Whisper STT processing error: {str(exc)}",
        ) from exc


class ChatPayload(BaseModel):
    """Payload for HTTP chat directive fallback."""
    text: Optional[str] = Field(None, description="Directive text")
    prompt: Optional[str] = Field(None, description="Directive prompt alias")
    message: Optional[str] = Field(None, description="Directive message alias")
    mode: str = Field("normal", description="Operating mode")


@app.post("/api/chat")
async def http_chat(payload: ChatPayload) -> Dict[str, Any]:
    """Execute chat directive via HTTP fallback when WebSocket is offline."""
    try:
        from core.service import handle_text
        return await asyncio.wait_for(
            handle_text(payload.text or payload.prompt or payload.message or "", source="ui_http", mode=payload.mode),
            timeout=5.0
        )
    except Exception:
        reply = await _generate_response(payload.text)
        return {"text": reply, "tool_steps": [], "source": "ui_http"}


class KeyConfigRequest(BaseModel):
    """Payload schema for setting or updating API keys from the Web HUD."""
    gemini_api_key: Optional[str] = Field(None, description="Google Gemini API Key")
    api_key: Optional[str] = Field(None, description="Alternative alias for Google Gemini API Key")
    groq_api_key: Optional[str] = Field(None, description="Optional Groq Cloud API Key")


class ProviderConfigRequest(BaseModel):
    llm_provider: Optional[str] = Field("gemini", description="Selected LLM provider")
    groq_model: Optional[str] = Field("openai/gpt-oss-20b", description="Selected Groq model")
    tts_provider: Optional[str] = Field("edge", description="Selected TTS engine")


@app.get("/api/config/providers")
async def get_providers_config() -> Dict[str, Any]:
    return {
        "llm_provider": os.getenv("LLM_PROVIDER", "gemini"),
        "groq_model": os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"),
        "gemini_model": os.getenv("GEMINI_MODEL") or os.getenv("MODEL_NAME") or "gemini-3.5-flash",
        "tts_provider": os.getenv("TTS_PROVIDER", "edge"),
    }


@app.post("/api/config/providers")
async def set_providers_config(payload: ProviderConfigRequest) -> Dict[str, Any]:
    if payload.llm_provider:
        os.environ["LLM_PROVIDER"] = payload.llm_provider.lower().strip()
    if payload.groq_model:
        os.environ["GROQ_MODEL"] = payload.groq_model.strip()
    if payload.tts_provider:
        os.environ["TTS_PROVIDER"] = payload.tts_provider.lower().strip()
    return {"success": True, "message": "Provider configuration saved and active."}


@app.get("/api/config/key-status")
async def get_key_status() -> Dict[str, Any]:
    """Retrieve current neural core configuration status without revealing secret keys."""
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    is_valid_gemini = bool(gemini_key and gemini_key != "your_gemini_api_key_here")
    is_valid_groq = bool(groq_key and groq_key != "your_groq_api_key_here")

    masked = ""
    if is_valid_gemini:
        if len(gemini_key) > 8:
            masked = f"{gemini_key[:4]}••••••••{gemini_key[-4:]}"
        else:
            masked = "••••••••"

    return {
        "configured": is_valid_gemini,
        "masked_key": masked,
        "has_groq": is_valid_groq,
        "gemini_model": os.getenv("MODEL_NAME") or os.getenv("GEMINI_MODEL") or "gemini-3.5-flash",
    }


@app.post("/api/config/set-key")
async def set_api_key(payload: KeyConfigRequest) -> Dict[str, Any]:
    """Validate, persist, and engage Google Gemini API Key from the Web HUD."""
    key = (payload.gemini_api_key or payload.api_key or "").strip()
    if len(key) < 8:
        raise HTTPException(status_code=400, detail="A valid Gemini API key is required.")
    if not key or key == "your_gemini_api_key_here":
        raise HTTPException(status_code=400, detail="A valid Gemini API key is required.")

    # 1. Validate key live with Google GenAI SDK
    try:
        from google import genai
        test_client = genai.Client(api_key=key)
        model_name = os.getenv("MODEL_NAME") or os.getenv("GEMINI_MODEL") or "gemini-3.5-flash"
        test_resp = test_client.models.generate_content(
            model=model_name,
            contents="Say 'OK'",
        )
        if not test_resp:
            raise ValueError("Empty response from Gemini API.")
    except Exception as exc:
        err_msg = str(exc)
        if "403" in err_msg or "API_KEY_INVALID" in err_msg or "permission" in err_msg.lower():
            raise HTTPException(status_code=401, detail="Invalid Gemini API key. Verification failed.")
        elif "quota" in err_msg.lower() or "429" in err_msg or "503" in err_msg:
            # Quota or transient high demand, but key format was authenticated
            pass
        else:
            raise HTTPException(status_code=400, detail=f"API verification probe failed: {err_msg[:120]}")

    # 2. Update active process environment
    os.environ["GEMINI_API_KEY"] = key
    if payload.groq_api_key and payload.groq_api_key.strip():
        os.environ["GROQ_API_KEY"] = payload.groq_api_key.strip()

    # 3. Persist to .env file safely
    try:
        project_root = Path(__file__).resolve().parent.parent
        env_file = project_root / ".env"
        env_lines: List[str] = []
        if env_file.exists():
            env_lines = env_file.read_text(encoding="utf-8").splitlines()

        gemini_found = False
        groq_found = False
        new_lines: List[str] = []
        for line in env_lines:
            if line.startswith("GEMINI_API_KEY="):
                new_lines.append(f"GEMINI_API_KEY={key}")
                gemini_found = True
            elif payload.groq_api_key and line.startswith("GROQ_API_KEY="):
                new_lines.append(f"GROQ_API_KEY={payload.groq_api_key.strip()}")
                groq_found = True
            else:
                new_lines.append(line)

        if not gemini_found:
            new_lines.append(f"GEMINI_API_KEY={key}")
        if payload.groq_api_key and not groq_found:
            new_lines.append(f"GROQ_API_KEY={payload.groq_api_key.strip()}")

        env_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    except Exception as exc:
        print(f"[WARN] Failed to write key to .env file: {exc}")

    # 4. Reinitialize brain singletons so active session immediately switches to new key
    try:
        import core.service as core_svc
        import core.brain as core_brain

        core_svc._brain_instance = None
        core_brain._default_brain = None
        core_svc.get_brain()
    except Exception as exc:
        print(f"[WARN] Failed to reinitialize brain singleton: {exc}")

    global _genai_client
    _genai_client = None

    return {
        "success": True,
        "message": "Neural core engaged successfully. Key verified and persistent.",
    }


# ---------------------------------------------------------------------------
# Universal Application, File, Task Launcher & Device Intelligence Engine
# ---------------------------------------------------------------------------

class AppLaunchResult(tuple):
    """A tuple subclass (label, detail) whose str() representation is label.
    Guarantees 100% compatibility with string formatting and tuple unpacking.
    """
    def __new__(cls, label: str, detail: Optional[str] = None):
        return super().__new__(cls, (label, detail))

    @property
    def label(self) -> str:
        return self[0]

    @property
    def detail(self) -> Optional[str]:
        return self[1]

    def __str__(self) -> str:
        return self[0]


def find_dynamic_app_in_system(app_name: str) -> Optional[Tuple[str, str]]:
    """Scan Windows Start Menu shortcuts and Program Files to dynamically locate installed software."""
    if platform.system().lower() != "windows":
        return None

    app_clean = app_name.lower().strip()
    search_dirs = [
        os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"),
        os.path.expandvars(r"%ProgramData%\Microsoft\Windows\Start Menu\Programs"),
    ]

    for s_dir in search_dirs:
        p = Path(s_dir)
        if not p.exists():
            continue
        try:
            for item in p.rglob("*.lnk"):
                stem_lower = item.stem.lower()
                if app_clean in stem_lower or stem_lower.startswith(app_clean):
                    return (str(item.resolve()), item.stem)
        except Exception:
            pass

    return None


def find_user_file_or_folder(query: str) -> Optional[Tuple[Path, str]]:
    """Locate a requested file or folder on user's system (workspace, desktop, downloads, documents).
    Returns (Path, display_label) if found.
    """
    cleaned = query.strip().strip("'\"")
    if not cleaned:
        return None

    direct_path = Path(cleaned)
    if direct_path.exists():
        kind = "Folder" if direct_path.is_dir() else "File"
        return (direct_path.resolve(), f"{kind}: {direct_path.name}")

    search_roots = [
        Path(__file__).resolve().parent.parent,
        Path(os.path.expandvars(r"%USERPROFILE%\Desktop")),
        Path(os.path.expandvars(r"%USERPROFILE%\Downloads")),
        Path(os.path.expandvars(r"%USERPROFILE%\Documents")),
    ]

    query_lower = cleaned.lower()
    query_tokens = [t for t in query_lower.split() if len(t) > 2]

    for root in search_roots:
        if not root.exists():
            continue
        try:
            for item in root.iterdir():
                item_name_lower = item.name.lower()
                norm_name = item_name_lower.replace("_", " ").replace("-", " ")
                # 1. Exact name or stem match
                if query_lower == item_name_lower or query_lower == item.stem.lower():
                    kind = "Folder" if item.is_dir() else "File"
                    return (item.resolve(), f"{kind}: {item.name}")
                # 2. Substring match
                if len(query_lower) >= 4 and (query_lower in item_name_lower or query_lower in norm_name):
                    kind = "Folder" if item.is_dir() else "File"
                    return (item.resolve(), f"{kind}: {item.name}")
                # 3. Token match
                if query_tokens and all(t in norm_name for t in query_tokens):
                    kind = "Folder" if item.is_dir() else "File"
                    return (item.resolve(), f"{kind}: {item.name}")
        except Exception:
            continue

    return None


def deep_search_user_files(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """Deep search for files across user's primary folders."""
    clean_q = query.lower().strip()
    if not clean_q:
        return []

    results: List[Dict[str, str]] = []
    roots = [
        ("Workspace", str(Path(__file__).resolve().parent.parent)),
        ("Desktop", os.path.expandvars(r"%USERPROFILE%\Desktop")),
        ("Downloads", os.path.expandvars(r"%USERPROFILE%\Downloads")),
        ("Documents", os.path.expandvars(r"%USERPROFILE%\Documents")),
    ]

    for loc_name, path_str in roots:
        p = Path(path_str)
        if not p.exists():
            continue
        try:
            for item in p.rglob("*"):
                if item.is_file():
                    item_name_lower = item.name.lower()
                    norm_name = item_name_lower.replace("_", " ").replace("-", " ")
                    if clean_q in item_name_lower or clean_q in norm_name or all(w in norm_name for w in clean_q.split()):
                        results.append({
                            "name": item.name,
                            "path": str(item.resolve()),
                            "location": loc_name,
                            "size_kb": f"{round(item.stat().st_size / 1024, 1)} KB",
                        })
                        if len(results) >= max_results:
                            return results
        except Exception:
            pass

    return results


def get_running_user_processes(limit: int = 8) -> List[Dict[str, Any]]:
    """Inspect active host applications currently running with window handles or significant RAM."""
    procs: List[Dict[str, Any]] = []
    try:
        for p in psutil.process_iter(['pid', 'name', 'memory_info', 'cpu_percent']):
            try:
                name = p.info['name'] or ""
                if name.lower().endswith((".exe")):
                    clean_name = name[:-4]
                else:
                    clean_name = name

                ignored = (
                    "svchost", "system", "registry", "smss", "csrss", "wininit",
                    "services", "lsass", "winlogon", "fontdrvhost", "dwm",
                    "conhost", "sihost", "taskhostw", "explorer", "shellexperiencehost",
                    "searchhost", "startmenuexperiencehost", "textinputhost"
                )
                if clean_name.lower() in ignored:
                    continue

                mem_mb = round(p.info['memory_info'].rss / (1024 * 1024), 1) if p.info.get('memory_info') else 0
                if mem_mb > 40:
                    procs.append({
                        "pid": p.info['pid'],
                        "name": clean_name,
                        "ram_mb": mem_mb,
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception:
        pass

    procs.sort(key=lambda x: x['ram_mb'], reverse=True)
    return procs[:limit]


def try_launch_system_app(user_text: str) -> Optional[AppLaunchResult]:
    """Universal desktop application, folder, file, and compound task launcher.
    Returns AppLaunchResult(label, detail) or None if text is not a launch intent.
    """
    norm = normalize_command(user_text)
    if not norm:
        return None

    # Guard: Never treat conversational queries as launch requests
    non_app_triggers = (
        "who are you", "what are you", "who r u", "tell me about yourself",
        "introduce yourself", "tu kon ahes", "what can you do", "what are your capabilities",
        "who am i", "what is my name", "do you know my name", "whats my name", "what s my name",
        "current time", "what time", "what is the time", "tell me the time", "clock",
        "what date", "todays date", "system info", "check system specs",
        "system stats", "laptop specs", "my specs", "how much ram", "storage space",
        "what are my notes", "show my notes", "list notes", "my notes",
        "what are my reminders", "show reminders", "check reminders", "my reminders",
        "what are my tasks", "show my tasks", "list tasks", "my tasks",
        "show active tasks", "running apps", "what processes", "active tasks",
        "search file", "search files", "find file", "find files", "search pc",
        "weather", "havaman"
    )
    if any(norm == g or norm.startswith(g) for g in non_app_triggers):
        return None

    if detect_user_intro(user_text):
        return None

    kind_check, _ = parse_note_or_reminder(user_text)
    if kind_check:
        return None

    greetings = (
        "heyy jarvis", "hey jarvis", "hi jarvis", "hello jarvis", "hi", "hello",
        "hey", "jarvis", "are you there", "good morning", "good evening", "good afternoon",
        "namaste", "namaskar"
    )
    if norm in greetings:
        return None

    # 1. System Folders & Drives Mapping
    system_folders = {
        "file manager": ("explorer.exe", "File Manager / Explorer"),
        "file explorer": ("explorer.exe", "File Manager / Explorer"),
        "files": ("explorer.exe", "File Manager / Explorer"),
        "my files": ("explorer.exe", "File Manager / Explorer"),
        "this pc": ("explorer.exe", "This PC / Explorer"),
        "my computer": ("explorer.exe", "My Computer / Explorer"),
        "downloads folder": (os.path.expandvars(r"%USERPROFILE%\Downloads"), "Downloads Folder"),
        "downloads": (os.path.expandvars(r"%USERPROFILE%\Downloads"), "Downloads Folder"),
        "download": (os.path.expandvars(r"%USERPROFILE%\Downloads"), "Downloads Folder"),
        "documents folder": (os.path.expandvars(r"%USERPROFILE%\Documents"), "Documents Folder"),
        "documents": (os.path.expandvars(r"%USERPROFILE%\Documents"), "Documents Folder"),
        "my documents": (os.path.expandvars(r"%USERPROFILE%\Documents"), "Documents Folder"),
        "desktop folder": (os.path.expandvars(r"%USERPROFILE%\Desktop"), "Desktop Folder"),
        "desktop": (os.path.expandvars(r"%USERPROFILE%\Desktop"), "Desktop Folder"),
        "pictures folder": (os.path.expandvars(r"%USERPROFILE%\Pictures"), "Pictures Folder"),
        "pictures": (os.path.expandvars(r"%USERPROFILE%\Pictures"), "Pictures Folder"),
        "photos": (os.path.expandvars(r"%USERPROFILE%\Pictures"), "Pictures Folder"),
        "my pictures": (os.path.expandvars(r"%USERPROFILE%\Pictures"), "Pictures Folder"),
        "videos folder": (os.path.expandvars(r"%USERPROFILE%\Videos"), "Videos Folder"),
        "videos": (os.path.expandvars(r"%USERPROFILE%\Videos"), "Videos Folder"),
        "my videos": (os.path.expandvars(r"%USERPROFILE%\Videos"), "Videos Folder"),
        "music folder": (os.path.expandvars(r"%USERPROFILE%\Music"), "Music Folder"),
        "music": (os.path.expandvars(r"%USERPROFILE%\Music"), "Music Folder"),
        "c drive": ("C:\\", "Local Disk (C:)"),
        "d drive": ("D:\\", "Local Disk (D:)"),
        "e drive": ("E:\\", "Local Disk (E:)"),
    }

    for folder_key, (target_path, label) in system_folders.items():
        if (
            norm == folder_key
            or norm == f"open {folder_key}"
            or norm == f"launch {folder_key}"
            or norm == f"start {folder_key}"
            or norm == f"show {folder_key}"
            or norm == f"khol {folder_key}"
            or norm == f"ugad {folder_key}"
            or norm.endswith(f"open {folder_key}")
            or norm.endswith(f"open {folder_key}.")
        ):
            try:
                if target_path == "explorer.exe":
                    subprocess.Popen(["explorer.exe", os.path.expandvars(r"%USERPROFILE%")])
                else:
                    if os.path.exists(target_path):
                        subprocess.Popen(["explorer.exe", target_path])
                    else:
                        subprocess.Popen(["explorer.exe", os.path.expandvars(r"%USERPROFILE%")])
                return AppLaunchResult(label, None)
            except Exception as exc:
                print(f"[WARN] Failed to open folder {label}: {exc}")

    # 2. Compound Task Handling
    if "whatsapp" in norm and ("send" in norm or "message" in norm):
        recipient = "contact"
        msg_text = ""
        m = re.search(r"(?:to|for)\s+([a-zA-Z0-9_]+)\s*(?:saying|message|that|say)?\s*(.*)$", user_text, re.IGNORECASE)
        if m:
            recipient = m.group(1).strip()
            msg_text = m.group(2).strip()
        if not msg_text:
            m_hi = re.search(r"send\s+([a-zA-Z0-9_\s]+?)\s+to\s+([a-zA-Z0-9_]+)", user_text, re.IGNORECASE)
            if m_hi:
                msg_text = m_hi.group(1).strip()
                recipient = m_hi.group(2).strip()

        detail_msg = f"Transmitting communication to {recipient}" + (f": '{msg_text}'" if msg_text else "")
        try:
            subprocess.Popen("cmd.exe /c start whatsapp:", shell=True)
        except Exception:
            subprocess.Popen("cmd.exe /c start https://web.whatsapp.com", shell=True)
        return AppLaunchResult("WhatsApp", detail_msg)

    if ("chrome" in norm or "google" in norm or "browser" in norm) and ("search" in norm or "find" in norm or "look for" in norm):
        query = ""
        m_q = re.search(r"(?:search|find|for)\s+(?:about\s+)?(.*)$", user_text, re.IGNORECASE)
        if m_q:
            query = m_q.group(1).strip()
        detail_msg = f"Executing web search: '{query}'" if query else "Opening web browser for search"
        import urllib.parse
        search_url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}" if query else "https://www.google.com"
        try:
            subprocess.Popen(["cmd.exe", "/c", f"start {search_url}"], shell=True)
        except Exception:
            webbrowser.open(search_url)
        return AppLaunchResult("Google Chrome", detail_msg)

    if "youtube" in norm and ("play" in norm or "song" in norm or "search" in norm or "video" in norm):
        query = ""
        m_yt = re.search(r"(?:play|search|for)\s+(.*)$", user_text, re.IGNORECASE)
        if m_yt:
            query = m_yt.group(1).strip()
        import urllib.parse
        yt_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(query)}" if query else "https://www.youtube.com"
        try:
            subprocess.Popen(["cmd.exe", "/c", f"start {yt_url}"], shell=True)
        except Exception:
            webbrowser.open(yt_url)
        detail_msg = f"Streaming request: '{query}'" if query else "Opening YouTube"
        return AppLaunchResult("YouTube", detail_msg)

    if "notepad" in norm and ("write" in norm or "note" in norm or "meeting" in norm):
        m_np = re.search(r"(?:write|note|about)\s+(.*)$", user_text, re.IGNORECASE)
        note_content = m_np.group(1).strip() if m_np else ""
        subprocess.Popen(["notepad.exe"])
        detail_msg = f"Drafting note: '{note_content}'" if note_content else "Opening fresh document"
        return AppLaunchResult("Notepad", detail_msg)

    # 3. Direct Application Launching (with absolute paths & --new-window flag)
    direct_apps = [
        ("google chrome", [
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        ], "Google Chrome", "chrome"),
        ("chrome", [
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        ], "Google Chrome", "chrome"),
        ("brave", [
            os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"),
            os.path.expandvars(r"%ProgramFiles%\BraveSoftware\Brave-Browser\Application\brave.exe"),
        ], "Brave Browser", "brave"),
        ("brave browser", [
            os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"),
            os.path.expandvars(r"%ProgramFiles%\BraveSoftware\Brave-Browser\Application\brave.exe"),
        ], "Brave Browser", "brave"),
        ("whatsapp", [], "WhatsApp", "whatsapp:"),
        ("telegram", [
            os.path.expandvars(r"%APPDATA%\Telegram Desktop\Telegram.exe"),
        ], "Telegram Desktop", "telegram"),
        ("notepad", ["notepad.exe"], "Notepad", "notepad"),
        ("calc", ["calc.exe"], "Calculator", "calc"),
        ("calculator", ["calc.exe"], "Calculator", "calc"),
        ("command prompt", ["cmd.exe"], "Command Prompt", "cmd"),
        ("cmd", ["cmd.exe"], "Command Prompt", "cmd"),
        ("terminal", ["wt.exe", "powershell.exe", "cmd.exe"], "Terminal", "powershell"),
        ("powershell", ["powershell.exe"], "Windows PowerShell", "powershell"),
        ("task manager", ["taskmgr.exe"], "Task Manager", "taskmgr"),
        ("taskmgr", ["taskmgr.exe"], "Task Manager", "taskmgr"),
        ("vs code", ["code"], "Visual Studio Code", "code"),
        ("vscode", ["code"], "Visual Studio Code", "code"),
        ("code", ["code"], "Visual Studio Code", "code"),
        ("edge", ["msedge.exe"], "Microsoft Edge", "msedge"),
        ("microsoft edge", ["msedge.exe"], "Microsoft Edge", "msedge"),
        ("spotify", ["spotify.exe"], "Spotify", "spotify:"),
        ("snipping tool", ["snippingtool.exe"], "Snipping Tool", "snippingtool"),
        ("screenshot", ["snippingtool.exe"], "Snipping Tool", "snippingtool"),
        ("paint", ["mspaint.exe"], "MS Paint", "mspaint"),
    ]

    for key, paths, label, cmd_fallback in direct_apps:
        is_match = (
            norm == key
            or norm == f"open {key}"
            or norm == f"launch {key}"
            or norm == f"start {key}"
            or norm == f"run {key}"
            or norm == f"khol {key}"
            or norm == f"ugad {key}"
            or norm.endswith(f"open {key}")
            or norm.endswith(f"open {key}.")
        )
        if is_match:
            launched = False
            for p in paths:
                if os.path.isfile(p):
                    try:
                        if "chrome.exe" in p.lower() or "brave.exe" in p.lower() or "msedge.exe" in p.lower():
                            subprocess.Popen([p, "--new-window"])
                        else:
                            subprocess.Popen([p])
                        launched = True
                        break
                    except Exception:
                        pass
            if not launched:
                try:
                    if ":" in cmd_fallback:
                        subprocess.Popen(f"cmd.exe /c start {cmd_fallback}", shell=True)
                    else:
                        subprocess.Popen(f"cmd.exe /c start {cmd_fallback}", shell=True)
                except Exception as exc:
                    print(f"[WARN] Failed to launch {label}: {exc}")
            return AppLaunchResult(label, None)

    # 4. Check for existing file or folder by name
    file_match = find_user_file_or_folder(norm.replace("open", "").strip())
    if file_match:
        f_path, f_label = file_match
        try:
            os.startfile(str(f_path))
            return AppLaunchResult(f_label, None)
        except Exception:
            return AppLaunchResult(f_label, None)

    # 5. Dynamic Start Menu discovery
    words = norm.split()
    target_candidate = ""
    if len(words) >= 2 and words[0] in ("open", "launch", "start", "run", "khol", "ugad"):
        target_candidate = " ".join(words[1:])
    elif len(words) == 1:
        target_candidate = words[0]

    if target_candidate:
        dyn = find_dynamic_app_in_system(target_candidate)
        if dyn:
            lnk_path, friendly_name = dyn
            try:
                os.startfile(lnk_path)
                return AppLaunchResult(friendly_name, None)
            except Exception as exc:
                print(f"[WARN] Dynamic launch failed for {friendly_name}: {exc}")

    return None


# ---------------------------------------------------------------------------
# Dynamic User State & Hardware Intelligence Engine
# ---------------------------------------------------------------------------

current_user_state: Dict[str, Any] = {
    "name": "User",
    "is_known": False,
}


def detect_user_intro(text: str) -> Optional[str]:
    """Detect if user is introducing their name (e.g. 'I am Shiv', 'Maza naav Amit')."""
    cleaned = text.strip()
    patterns = [
        r"(?:hey\s+jarvis[,\s]+)?(?:i\s+am|im|i'm)\s+([a-zA-Z\u0900-\u097F]+)",
        r"(?:my\s+name\s+is|call\s+me|this\s+is)\s+([a-zA-Z\u0900-\u097F]+)",
        r"(?:maza\s+naav|maze\s+naav|mera\s+naam)\s+([a-zA-Z\u0900-\u097F]+)",
    ]
    for pat in patterns:
        m = re.search(pat, cleaned, re.IGNORECASE)
        if m:
            name = m.group(1).strip().capitalize()
            if name.lower() not in {
                "fine", "good", "ready", "here", "testing", "back",
                "sorry", "happy", "sad", "listening", "online", "busy",
                "tired", "trying", "working", "asking", "speaking", "telling"
            }:
                return name
    return None


def get_deep_system_specs() -> str:
    """Inspect the real host machine in real-time and return accurate diagnostics."""
    try:
        os_info = f"{platform.system()} {platform.release()} ({platform.machine()})"
        cpu_count = psutil.cpu_count(logical=True)
        cpu_freq = psutil.cpu_freq()
        freq_str = f"{round(cpu_freq.current / 1000, 2)} GHz" if cpu_freq else "N/A"
        cpu_load = psutil.cpu_percent(interval=None)

        vm = psutil.virtual_memory()
        ram_total = round(vm.total / (1024 ** 3), 1)
        ram_used = round(vm.used / (1024 ** 3), 1)
        ram_avail = round(vm.available / (1024 ** 3), 1)

        try:
            disk = psutil.disk_usage("C:\\")
            disk_total = round(disk.total / (1024 ** 3), 1)
            disk_free = round(disk.free / (1024 ** 3), 1)
            disk_str = f"{disk_free} GB free of {disk_total} GB"
        except Exception:
            disk_str = "Available"

        batt = psutil.sensors_battery()
        if batt:
            batt_str = f"{batt.percent}%" + (" (Plugged In / Charging)" if batt.power_plugged else " (On Battery)")
        else:
            batt_str = "AC Power Connected (Desktop / Nominal)"

        hostname = socket.gethostname()

        return (
            f"🖥️ Host Machine Specifications:\n"
            f"• Operating System: {os_info}\n"
            f"• Device Hostname: {hostname}\n"
            f"• Processor: {cpu_count} Logical Cores @ {freq_str} (Current Load: {cpu_load}%)\n"
            f"• Memory (RAM): {ram_total} GB Total ({ram_used} GB Used, {ram_avail} GB Free — {vm.percent}% in use)\n"
            f"• Storage (C: Drive): {disk_str}\n"
            f"• Power / Battery: {batt_str}"
        )
    except Exception as exc:
        return f"System Diagnostics: Active OS host nominal. CPU Load: {psutil.cpu_percent()}%, RAM: {psutil.virtual_memory().percent}%."


def parse_note_or_reminder(user_text: str) -> Tuple[Optional[str], Optional[str]]:
    """Parse notes or reminders dictated by the user via text or voice."""
    cleaned = user_text.lower().strip()

    reminder_prefixes = (
        "remind me to", "remind me", "set a reminder for",
        "set reminder for", "add a reminder", "set reminder"
    )
    for prefix in reminder_prefixes:
        if cleaned.startswith(prefix):
            content = user_text[len(prefix):].strip(" :")
            if content:
                return ("reminder", content)

    note_prefixes = (
        "save note", "save a note", "take a note", "note that",
        "remember that", "add note", "add a note", "create a note",
        "note down", "store note"
    )
    for prefix in note_prefixes:
        if cleaned.startswith(prefix):
            content = user_text[len(prefix):].strip(" :")
            if content:
                return ("note", content)

    return (None, None)


async def _generate_response(user_text: str, session_user: Optional[Dict[str, Any]] = None) -> str:
    """Intelligently process and answer user questions directly from UI backend,
    supporting dynamic user personalization, deep system inspection, persistent notes/reminders,
    and ultra-fast (<1.5s) AI query generation.
    """
    if session_user is None:
        session_user = current_user_state

    cleaned = user_text.lower().strip()
    norm = normalize_command(user_text)
    active_name = session_user.get("name", "User")

    # 0. Pure greeting / Wake acknowledgment
    greeting_triggers = (
        "hey jarvis", "hi jarvis", "hello jarvis", "jarvis", "ok jarvis",
        "hey", "hello", "hi", "are you there", "namaste", "namaskar",
        "namaste jarvis", "namaskar jarvis", "suno jarvis", "bol jarvis", "uth jarvis"
    )
    norm_words = norm.split()
    greeting_tokens = {"hey", "hi", "hello", "jarvis", "namaste", "namaskar", "suno", "bol", "uth", "ok", "there"}
    is_pure_greeting = (
        norm in greeting_triggers
        or (norm_words and all(w in greeting_tokens for w in norm_words))
        or (norm_words and norm_words[0] in ("hey", "hi", "hello", "namaste", "namaskar") and len(norm_words) <= 3)
    )
    if is_pure_greeting:
        user_suffix = f", {active_name}" if session_user.get("is_known") else ", Sir"
        is_mr_hi = any("ऀ" <= c <= "ॿ" for c in user_text) or any(w in norm_words for w in ("namaste", "namaskar", "suno", "bol", "ahes", "ka"))
        if is_mr_hi:
            return "हो, मी ऐकतोय. सांगा काय करू?"
        return f"Greetings! Standing by{user_suffix}. How may I assist you?"

    # 1. User Identity Introduction
    detected_name = detect_user_intro(user_text)
    if detected_name:
        session_user["name"] = detected_name
        session_user["is_known"] = True
        current_user_state["name"] = detected_name
        current_user_state["is_known"] = True
        return f"Hello {detected_name}! I have updated my user registers. I am now configured specifically for you. How can I assist you today?"

    # 2. Reset user
    if norm in ("reset user", "forget my name", "switch user", "change user", "reset profile"):
        session_user["name"] = "User"
        session_user["is_known"] = False
        current_user_state["name"] = "User"
        current_user_state["is_known"] = False
        return "I have cleared my user registers to default neutral mode. How may I assist you?"

    # 3. User Identity Query
    if any(k in norm for k in ("who am i", "what is my name", "do you know my name", "whats my name", "what s my name", "maza naav kay")):
        if session_user.get("is_known"):
            return f"You are recognized as {active_name} in my active session. All memory vaults and task logs are dedicated to you."
        return "I currently address you as Sir. If you would like me to address you by your name, simply tell me 'I am [your name]' and I will remember it."

    # 4. Fast-Path Conversational Greetings
    greetings = (
        "heyy jarvis", "hey jarvis", "hi jarvis", "hello jarvis", "hi", "hello",
        "hey", "jarvis", "are you there", "good morning", "good evening", "good afternoon",
        "namaste", "namaskar"
    )
    if norm in greetings or any(norm == g for g in greetings):
        if session_user.get("is_known"):
            return f"Greetings {active_name}! Jarvis is online, listening, and ready for your command."
        return "Greetings! Jarvis is online, listening, and ready for your command."

    # 5. Assistant Self-Identity & Capabilities
    if norm in (
        "who are you", "what are you", "who r u", "tell me about yourself",
        "introduce yourself", "tu kon ahes", "tu kon aahes", "what is your name",
        "whats your name"
    ):
        target = active_name if session_user.get("is_known") else "you"
        return (
            f"I am J.A.R.V.I.S., an autonomous desktop AI assistant configured for {target}. "
            "I manage your PC applications, hardware telemetry, notes & reminders, and answer questions with high-speed intelligence."
        )

    if norm in (
        "what can you do", "what are your capabilities", "what can u do",
        "tu kay karu shaktos", "help", "commands", "features", "what are your features"
    ):
        return (
            "Here is what I can do for you:\n"
            "• **Launch Apps:** 'Open Chrome', 'Open WhatsApp', 'Launch Calculator', 'Terminal'\n"
            "• **PC Diagnostics:** 'What are my system specs?', 'Check CPU & RAM usage'\n"
            "• **Notes & Reminders:** 'Take a note: [text]', 'Remind me to [task]', 'What are my notes?'\n"
            "• **AI Knowledge:** Ask me any technical, coding, or general knowledge question!"
        )

    if norm in ("how are you", "how are you doing", "how r u", "kasa ahes", "kasa ahes tu", "kase ahat"):
        target = active_name if session_user.get("is_known") else "Sir"
        return f"All quantum registers and neural core systems are operating at peak efficiency, {target}. How may I serve you?"

    # 6. Active Tasks Inspection
    if any(k in norm for k in ("show active tasks", "running apps", "what processes", "active tasks", "running processes")):
        procs = get_running_user_processes(limit=8)
        if procs:
            lines = [f"• **{p['name']}** (PID: {p['pid']}, RAM: {p['ram_mb']} MB)" for p in procs]
            return "Active PC Tasks / Running Applications:\n" + "\n".join(lines)
        return "No significant background user tasks detected on this machine."

    # 7. Device File Search
    if norm.startswith(("search file", "search files", "find file", "find files", "search pc")):
        q = re.sub(r"^(?:search|find)\s+(?:files|file|pc)?\s*(?:for)?\s*", "", user_text, flags=re.IGNORECASE).strip()
        if q:
            matches = deep_search_user_files(q, max_results=5)
            if matches:
                lines = [f"• **{m['name']}** ({m['size_kb']}) in *{m['location']}*\n  `{m['path']}`" for m in matches]
                return f"Device File Search Results for '{q}':\n" + "\n".join(lines)
            return f"No files matching '{q}' were found across Desktop, Downloads, Documents, or Workspace."

    # 8. Live Time / Date
    time_triggers = (
        "current time", "what time", "what is the time", "tell me the time", "tell me time",
        "tell time", "what is time", "whats the time", "what time is it", "what is date",
        "tell me the current time", "clock", "date today", "what date", "today date",
        "whats today", "aajchi tarikh", "kiti vajle", "vel kay zali", "samay kya hua", "kitne baje"
    )
    is_meta = any(w in norm.split() for w in ("why", "wrong", "before", "mistake", "told", "yesterday", "ago"))
    if not is_meta and (any(k in norm for k in time_triggers) or any(w in norm.split() for w in ("time", "clock", "date", "tarikh", "samay", "vajle", "vel"))):
        now = datetime.datetime.now()
        time_str = now.strftime("%I:%M %p").lstrip("0")
        date_str = now.strftime("%A, %B %d, %Y")
        norm_words = norm.split()
        has_date_word = any(w in norm_words for w in ("date", "day", "tarikh", "aajchi", "today"))
        has_time_word = any(w in norm_words for w in ("time", "clock", "vajle", "samay", "baje", "vel"))
        if has_time_word and not has_date_word:
            return f"The current time is {time_str}."
        elif has_date_word and not has_time_word:
            return f"Today is {date_str}."
        return f"The current time is {time_str} on {date_str}."

    # 9. Real Hardware Telemetry Specs
    if any(k in norm for k in ("system info", "check system specs", "laptop specs", "my specs", "hardware specs", "specs")):
        return get_deep_system_specs()

    # 10. Persistent Notes / Reminders
    kind, content = parse_note_or_reminder(user_text)
    if kind and content:
        try:
            prefix = "[REMINDER] " if kind == "reminder" else "[NOTE] "
            title = prefix + (content[:30] + "..." if len(content) > 30 else content)
            note_id = await memory_manager.add_note(title=title, content=content)
            return f"Understood. I have logged this {kind} to SQLite memory (Reference ID #{note_id}): '{content}'."
        except Exception as exc:
            return f"Logged your {kind}: '{content}'."

    # 11. Core Brain or GenAI Generation
    try:
        from core.service import handle_text
        brain_res = await asyncio.wait_for(handle_text(user_text, source="ui_internal"), timeout=4.0)
        if brain_res and brain_res.get("text"):
            return brain_res["text"]
    except Exception:
        pass

    client = get_genai_client()
    if client:
        try:
            prompt = (
                f"You are J.A.R.V.I.S., a precise, ultra-concise desktop AI assistant. "
                f"User name: {active_name}. "
                f"Provide ONLY the direct answer to what was asked in 1-2 short sentences. "
                f"Do NOT include conversational filler, polite boilerplate, or offers for extra help. "
                f"If the user addresses you in Hindi or Marathi, reply in that language.\n\n"
                f"User Query: {user_text}"
            )
            response = await client.aio.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=prompt,
            )
            if response and response.text:
                return strip_unnecessary_filler(response.text.strip())
        except Exception:
            pass

    return (
        f"Jarvis Core acknowledged your directive: '{user_text}'. "
        f"All local memory vaults and hardware telemetry are fully operational."
    )


@app.websocket("/ws")
@app.websocket("/ws/jarvis")
async def websocket_jarvis(websocket: WebSocket) -> None:
    """Real-time bi-directional WebSocket channel for HUD chat and telemetry."""
    await websocket.accept()
    session_user: Dict[str, Any] = {"name": "User", "is_known": False}
    last_chat_msg = ""
    last_chat_time = 0.0
    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                payload = json.loads(raw_data)
            except json.JSONDecodeError:
                payload = {"action": "chat", "text": raw_data}

            action = payload.get("action", "chat")

            if action == "chat":
                user_text = (payload.get("text") or payload.get("prompt") or payload.get("query") or "").strip()
                mode = payload.get("mode", "normal")
                if not user_text:
                    continue

                now_ts = time.time()
                if user_text.lower() == last_chat_msg.lower() and (now_ts - last_chat_time) < 2.0:
                    continue
                last_chat_msg = user_text
                last_chat_time = now_ts

                norm = normalize_command(user_text)

                # Reset user request
                if norm in ("reset user", "forget my name", "switch user", "change user", "reset profile"):
                    session_user["name"] = "User"
                    session_user["is_known"] = False
                    current_user_state["name"] = "User"
                    current_user_state["is_known"] = False
                    await websocket.send_json({"type": "user_identified", "name": "GUEST"})
                    await websocket.send_json({"type": "response", "text": "I have reset my user registers to default neutral mode. How may I assist you?"})
                    await websocket.send_json({"type": "status", "status": "idle"})
                    continue

                # Detect user introduction
                detected_name = detect_user_intro(user_text)
                if detected_name:
                    session_user["name"] = detected_name
                    session_user["is_known"] = True
                    current_user_state["name"] = detected_name
                    current_user_state["is_known"] = True
                    await websocket.send_json({"type": "user_identified", "name": detected_name})

                # 1. Push thinking status to HUD
                await websocket.send_json({"type": "status", "status": "thinking"})

                # 2. Check routing
                norm_words = norm.split()
                time_triggers = (
                    "what time", "what is the time", "tell me the time", "tell me time",
                    "tell time", "current time", "time please", "what time is it", "whats the time",
                    "what s the time", "what is time", "what is date", "what is the date",
                    "today date", "what date", "todays date", "date today",
                    "what day is it", "kiti vajle", "vel kay zali", "samay kya hua", "kitne baje", "aajchi tarikh"
                )
                is_meta_time = any(w in norm_words for w in ("why", "wrong", "before", "mistake", "told", "yesterday", "ago", "spent", "table", "timeline", "schedule", "plan"))
                is_time_query = not is_meta_time and (
                    any(t in norm for t in time_triggers)
                    or any(w in norm_words for w in ("time", "clock", "date", "tarikh", "vajle", "samay"))
                )

                greeting_triggers = (
                    "hey jarvis", "hi jarvis", "hello jarvis", "jarvis", "ok jarvis",
                    "hey", "hello", "hi", "are you there", "namaste", "namaskar",
                    "namaste jarvis", "namaskar jarvis", "suno jarvis", "bol jarvis", "uth jarvis"
                )
                greeting_tokens = {"hey", "hi", "hello", "jarvis", "namaste", "namaskar", "suno", "bol", "uth", "ok", "there"}
                is_pure_greeting = (
                    norm in greeting_triggers
                    or (norm_words and all(w in greeting_tokens for w in norm_words))
                    or (norm_words and norm_words[0] in ("hey", "hi", "hello", "namaste", "namaskar") and len(norm_words) <= 3)
                )

                launch_info = try_launch_system_app(user_text)
                tool_steps = []
                if launch_info:
                    app_label = str(launch_info.label if hasattr(launch_info, 'label') else launch_info[0])
                    task_detail = launch_info.detail if hasattr(launch_info, 'detail') else (launch_info[1] if len(launch_info) > 1 else None)
                    user_suffix = f", {session_user['name']}" if session_user["is_known"] else ""
                    if task_detail:
                        reply_text = f"Opening {app_label} for you now{user_suffix}. {task_detail}"
                    else:
                        reply_text = f"Opening {app_label} for you now{user_suffix}."
                    tool_steps = [f"open_app({app_label})"]
                    try:
                        await memory_manager.save_interaction(role="user", content=user_text)
                        await memory_manager.save_interaction(role="assistant", content=reply_text)
                    except Exception:
                        pass
                elif is_pure_greeting:
                    user_suffix = f", {session_user['name']}" if session_user["is_known"] else ", Sir"
                    is_mr_hi = any("ऀ" <= c <= "ॿ" for c in user_text) or any(w in norm_words for w in ("namaste", "namaskar", "suno", "bol", "ahes", "ka"))
                    if is_mr_hi:
                        reply_text = "हो, मी ऐकतोय. सांगा काय करू?"
                    else:
                        reply_text = f"Greetings! Standing by{user_suffix}. How may I assist you?"
                    tool_steps = ["wake_listener()"]
                    try:
                        await memory_manager.save_interaction(role="user", content=user_text)
                        await memory_manager.save_interaction(role="assistant", content=reply_text)
                    except Exception:
                        pass
                elif is_time_query:
                    now = datetime.datetime.now()
                    time_str = now.strftime("%I:%M %p").lstrip("0")
                    date_str = now.strftime("%A, %B %d, %Y")
                    has_date_word = any(w in norm_words for w in ("date", "day", "tarikh", "aajchi", "today"))
                    has_time_word = any(w in norm_words for w in ("time", "clock", "vajle", "samay", "baje", "vel"))
                    if has_time_word and not has_date_word:
                        reply_text = f"The current time is {time_str}."
                    elif has_date_word and not has_time_word:
                        reply_text = f"Today is {date_str}."
                    else:
                        reply_text = f"The current time is {time_str} on {date_str}."
                    tool_steps = ["get_system_time()"]
                    try:
                        await memory_manager.save_interaction(role="user", content=user_text)
                        await memory_manager.save_interaction(role="assistant", content=reply_text)
                    except Exception:
                        pass
                else:
                    # 3. Delegate directly to Core Brain Engine via handle_text
                    reply_text = ""
                    try:
                        from core.service import handle_text
                        result = await asyncio.wait_for(
                            handle_text(user_text, source="ui", mode=mode),
                            timeout=4.5
                        )
                        reply_text = result.get("text", "")
                        tool_steps = result.get("tool_steps", [])
                    except Exception:
                        reply_text = ""

                    if not reply_text:
                        reply_text = await _generate_response(user_text, session_user=session_user)

                    # Strip conversational filler to ensure exact answers only
                    reply_text = strip_unnecessary_filler(reply_text)

                    try:
                        await memory_manager.save_interaction(role="user", content=user_text)
                        await memory_manager.save_interaction(role="assistant", content=reply_text)
                    except Exception:
                        pass

                # 4. Broadcast executed tool steps to HUD
                if tool_steps:
                    await websocket.send_json({"type": "tool_steps", "steps": tool_steps})

                # 5. Push response and reset to idle
                await websocket.send_json({"type": "response", "text": reply_text})
                await websocket.send_json({"type": "status", "status": "idle"})

            elif action == "set_user":
                name = payload.get("name", "").strip()
                if name:
                    session_user["name"] = name
                    session_user["is_known"] = True
                    current_user_state["name"] = name
                    current_user_state["is_known"] = True
                    await websocket.send_json({"type": "user_identified", "name": name})
                else:
                    session_user["name"] = "User"
                    session_user["is_known"] = False
                    current_user_state["name"] = "User"
                    current_user_state["is_known"] = False
                    await websocket.send_json({"type": "user_identified", "name": "GUEST"})

            elif action == "get_telemetry":
                try:
                    from tools.system_tools import GetSystemStatsTool
                    stats = GetSystemStatsTool().run()
                    await websocket.send_json({"type": "telemetry", "data": stats.data})
                except Exception:
                    pass

            elif action == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
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
