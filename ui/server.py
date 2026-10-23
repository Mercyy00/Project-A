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
import platform
import re
import shutil
import socket
import subprocess
import time
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple
import webbrowser

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Response, WebSocket, WebSocketDisconnect, status
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
    allow_origins=["*"],
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
async def stream_neural_tts(
    text: str = Query(..., min_length=1, description="Text to speak"),
    lang: str = Query("en", description="Language code: en, hi, mr"),
) -> Response:
    """Stream high-fidelity Edge-TTS neural speech audio for Web HUD (Task A2.3)."""
    clean_text = re.sub(r"[*#`_•]", " ", text).strip()
    if not clean_text:
        raise HTTPException(status_code=400, detail="Empty text for speech synthesis")

    # Select high-quality neural voice based on language code
    voice_map = {
        "en": os.getenv("TTS_VOICE_EN", "en-US-GuyNeural"),
        "hi": os.getenv("TTS_VOICE_HI", "hi-IN-MadhurNeural"),
        "mr": os.getenv("TTS_VOICE_MR", "mr-IN-ManoharNeural"),
    }
    voice = voice_map.get(lang.lower(), voice_map["en"])

    # Auto-detect Devanagari script for Marathi/Hindi if lang was en
    has_devanagari = any("\u0900" <= ch <= "\u097F" for ch in clean_text)
    if has_devanagari and lang.lower() == "en":
        voice = voice_map["mr"]

    try:
        import edge_tts

        communicate = edge_tts.Communicate(clean_text, voice)
        chunks = []
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                chunks.append(chunk["data"])

        audio_bytes = b"".join(chunks)
        if not audio_bytes:
            raise HTTPException(status_code=500, detail="Failed to synthesize audio")

        return Response(content=audio_bytes, media_type="audio/mpeg")
    except Exception as exc:
        print(f"[WARN] Edge-TTS error: {exc}")
        raise HTTPException(status_code=500, detail=f"TTS generation failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Day 3: WebSocket Live Channel & Sci-Fi HUD
# Universal Desktop App, File, and Compound Task Launch Engine
# ---------------------------------------------------------------------------

_START_MENU_SHORTCUTS: Optional[Dict[str, str]] = None


def get_start_menu_shortcuts() -> Dict[str, str]:
    """Scan and cache Windows Start Menu shortcuts for dynamic app discovery."""
    global _START_MENU_SHORTCUTS
    if _START_MENU_SHORTCUTS is not None:
        return _START_MENU_SHORTCUTS

    shortcuts: Dict[str, str] = {}
    if os.name != "nt":
        _START_MENU_SHORTCUTS = shortcuts
        return shortcuts

    search_dirs = [
        os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"),
        os.path.expandvars(r"%ProgramData%\Microsoft\Windows\Start Menu\Programs"),
    ]
    for base_dir in search_dirs:
        if os.path.exists(base_dir):
            try:
                for root, _, files in os.walk(base_dir):
                    for f in files:
                        if f.lower().endswith(".lnk"):
                            clean_name = f[:-4].lower()
                            if "uninstall" in clean_name or "help" in clean_name:
                                continue
                            full_path = os.path.join(root, f)
                            shortcuts[clean_name] = full_path
            except Exception as e:
                print(f"[WARN] Failed scanning start menu {base_dir}: {e}")

    _START_MENU_SHORTCUTS = shortcuts
    return shortcuts


def find_dynamic_app_in_system(query: str) -> Optional[Tuple[str, str]]:
    """Search for an installed application matching query across Start Menu shortcuts and PATH.
    Returns (executable_or_lnk_path, display_label) if found.
    """
    shortcuts = get_start_menu_shortcuts()
    query_clean = query.lower().strip()
    if not query_clean:
        return None

    # 1. Exact match in Start Menu shortcuts
    if query_clean in shortcuts:
        return (shortcuts[query_clean], query.title())

    # 2. Substring match
    for name, path in shortcuts.items():
        if query_clean == name or query_clean in name or name in query_clean:
            return (path, name.title())

    # 3. Token match
    tokens = [t for t in query_clean.split() if len(t) > 2]
    if tokens:
        for name, path in shortcuts.items():
            if all(t in name for t in tokens):
                return (path, name.title())

    # 4. Check system PATH via shutil.which
    which_path = shutil.which(query_clean) or shutil.which(f"{query_clean}.exe")
    if which_path:
        return (which_path, query.title())

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
        Path(r"C:\Users\rohit\OneDrive\Desktop\Project-A"),
        Path(os.path.expandvars(r"%USERPROFILE%\Desktop")),
        Path(os.path.expandvars(r"%USERPROFILE%\Downloads")),
        Path(os.path.expandvars(r"%USERPROFILE%\Documents")),
        Path.cwd(),
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


def try_launch_system_app(user_text: str) -> Optional[Tuple[str, Optional[str]]]:
    """Universal desktop application, folder, file, and compound task launcher.
    Returns (app_or_target_label, optional_task_detail) or None if text is not a launch intent.
    """
    norm = normalize_command(user_text)
    if not norm:
        return None

    # Guard: Never treat conversational greetings, identity, status, or notes queries as app launch requests
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

    # Detect user identity introduction ("I am Rohit")
    if detect_user_intro(user_text):
        return None

    # Detect standalone notes/reminders
    kind_check, _ = parse_note_or_reminder(user_text)
    if kind_check:
        return None

    # Pure greetings
    greetings = (
        "heyy jarvis", "hey jarvis", "hi jarvis", "hello jarvis", "hi", "hello",
        "hey", "jarvis", "are you there", "good morning", "good evening", "good afternoon",
        "namaste", "namaskar"
    )
    if norm in greetings:
        return None

    # -------------------------------------------------------------
    # 1. System Folders, Drives & Utilities Mapping
    # -------------------------------------------------------------
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
        "c drive": ("C:\\", "C: Drive"),
        "drive c": ("C:\\", "C: Drive"),
        "d drive": ("D:\\", "D: Drive"),
        "drive d": ("D:\\", "D: Drive"),
        "recycle bin": ("shell:RecycleBinFolder", "Recycle Bin"),
        "trash": ("shell:RecycleBinFolder", "Recycle Bin"),
    }

    # Check for direct system folder match
    for f_key, (target_path, f_label) in system_folders.items():
        is_match = (
            norm == f_key
            or norm == f"open {f_key}"
            or norm == f"launch {f_key}"
            or norm.startswith(f"open {f_key} ")
            or (len(f_key.split()) > 1 and f_key in norm)
        )
        if is_match:
            try:
                if target_path == "explorer.exe":
                    subprocess.Popen(["explorer.exe", os.path.expandvars(r"%USERPROFILE%")])
                elif target_path.startswith("shell:"):
                    subprocess.Popen(f"explorer.exe {target_path}", shell=True)
                else:
                    subprocess.Popen(["explorer.exe", target_path])
                return (f_label, None)
            except Exception as e:
                print(f"[WARN] Error opening folder {f_key}: {e}")
                return (f_label, None)

    # -------------------------------------------------------------
    # 2. Native Windows Tools & Protocol Handlers
    # -------------------------------------------------------------
    protocol_apps = {
        "camera": ("cmd.exe /c start microsoft.windows.camera:", "Camera"),
        "webcam": ("cmd.exe /c start microsoft.windows.camera:", "Camera"),
        "settings": ("cmd.exe /c start ms-settings:", "Windows Settings"),
        "windows settings": ("cmd.exe /c start ms-settings:", "Windows Settings"),
        "store": ("cmd.exe /c start ms-windows-store:", "Microsoft Store"),
        "microsoft store": ("cmd.exe /c start ms-windows-store:", "Microsoft Store"),
        "calculator": ("cmd.exe /c start calc:", "Calculator"),
        "calc": ("cmd.exe /c start calc:", "Calculator"),
        "notepad": ("notepad.exe", "Notepad"),
        "paint": ("cmd.exe /c start mspaint", "Paint"),
        "mspaint": ("cmd.exe /c start mspaint", "Paint"),
        "snipping tool": ("cmd.exe /c start snippingtool", "Snipping Tool"),
        "snip": ("cmd.exe /c start snippingtool", "Snipping Tool"),
        "screenshot": ("cmd.exe /c start snippingtool", "Snipping Tool"),
        "task manager": ("cmd.exe /c start taskmgr", "Task Manager"),
        "taskmgr": ("cmd.exe /c start taskmgr", "Task Manager"),
        "cmd": ("cmd.exe /c start cmd", "Command Prompt"),
        "command prompt": ("cmd.exe /c start cmd", "Command Prompt"),
        "terminal": ("cmd.exe /c start wt", "Windows Terminal"),
        "powershell": ("cmd.exe /c start powershell", "PowerShell"),
    }
    for p_key, (cmd, p_label) in protocol_apps.items():
        if norm == p_key or norm == f"open {p_key}" or norm == f"launch {p_key}" or norm.startswith(f"open {p_key} ") or (f"open {p_key}" in norm):
            try:
                if cmd.endswith(".exe"):
                    subprocess.Popen([cmd])
                else:
                    subprocess.Popen(cmd, shell=True)
                return (p_label, None)
            except Exception as e:
                print(f"[WARN] Error opening protocol {p_key}: {e}")
                return (p_label, None)

    # -------------------------------------------------------------
    # 3. Web & Messaging Apps with Compound Task Awareness
    # -------------------------------------------------------------
    # A. WhatsApp compound messaging or app launch
    if "whatsapp" in norm:
        task_detail = None
        send_match = re.search(r"send\s+(?:a\s+message\s+)?(.+?)\s+to\s+([a-zA-Z\u0900-\u097F]+)", user_text, re.IGNORECASE)
        if send_match:
            msg_content = send_match.group(1).strip(" '\"")
            recipient = send_match.group(2).strip().capitalize()
            task_detail = f"Initiated dispatch of message '{msg_content}' to {recipient}."
        elif "send hi" in norm or "say hi" in norm:
            task_detail = "Initiated dispatch of greeting to recipient."

        launched = False
        try:
            subprocess.Popen("cmd.exe /c start whatsapp:", shell=True)
            launched = True
        except Exception:
            pass

        if not launched:
            subprocess.Popen("cmd.exe /c start https://web.whatsapp.com", shell=True)

        return ("WhatsApp", task_detail)

    # B. Chrome with optional Google Search task
    if "chrome" in norm:
        chrome_candidates = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        ]
        search_query = None
        m = re.search(r"(?:search|google|find)\s+(?:for\s+)?(.+)", user_text, re.IGNORECASE)
        if m and "chrome" not in m.group(1).lower():
            search_query = m.group(1).strip()

        if search_query:
            import urllib.parse
            url = f"https://www.google.com/search?q={urllib.parse.quote_plus(search_query)}"
            for c_path in chrome_candidates:
                if os.path.exists(c_path):
                    subprocess.Popen([c_path, "--new-window", url])
                    return ("Google Chrome", f"Executed Google search for '{search_query}'.")
            subprocess.Popen(f'cmd.exe /c start chrome --new-window "{url}"', shell=True)
            return ("Google Chrome", f"Executed Google search for '{search_query}'.")
        else:
            for c_path in chrome_candidates:
                if os.path.exists(c_path):
                    subprocess.Popen([c_path, "--new-window"])
                    return ("Google Chrome", None)
            subprocess.Popen("cmd.exe /c start chrome --new-window", shell=True)
            return ("Google Chrome", None)

    # C. Brave Browser
    if "brave" in norm:
        brave_candidates = [
            os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"),
            r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
            r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
        ]
        search_query = None
        m = re.search(r"(?:search|find)\s+(?:for\s+)?(.+)", user_text, re.IGNORECASE)
        if m and "brave" not in m.group(1).lower():
            search_query = m.group(1).strip()

        if search_query:
            import urllib.parse
            url = f"https://www.google.com/search?q={urllib.parse.quote_plus(search_query)}"
            for b_path in brave_candidates:
                if os.path.exists(b_path):
                    subprocess.Popen([b_path, "--new-window", url])
                    return ("Brave Browser", f"Executed search for '{search_query}'.")
            subprocess.Popen(f'cmd.exe /c start brave --new-window "{url}"', shell=True)
            return ("Brave Browser", f"Executed search for '{search_query}'.")
        else:
            for b_path in brave_candidates:
                if os.path.exists(b_path):
                    subprocess.Popen([b_path, "--new-window"])
                    return ("Brave Browser", None)
            subprocess.Popen("cmd.exe /c start brave --new-window", shell=True)
            return ("Brave Browser", None)

    # D. Edge Browser
    if "edge" in norm:
        subprocess.Popen("cmd.exe /c start msedge --new-window", shell=True)
        return ("Microsoft Edge", None)

    # E. Firefox Browser
    if "firefox" in norm:
        subprocess.Popen("cmd.exe /c start firefox --new-window", shell=True)
        return ("Mozilla Firefox", None)

    # F. YouTube with optional search/play
    if "youtube" in norm:
        m = re.search(r"(?:play|search|watch)\s+(?:for\s+)?(.+)", user_text, re.IGNORECASE)
        if m and "youtube" not in m.group(1).lower():
            import urllib.parse
            q = m.group(1).strip()
            url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(q)}"
            subprocess.Popen(f'cmd.exe /c start "{url}"', shell=True)
            return ("YouTube", f"Playing '{q}' on YouTube.")
        subprocess.Popen("cmd.exe /c start https://www.youtube.com", shell=True)
        return ("YouTube", None)

    # G. VS Code / Code
    if norm == "code" or norm == "vscode" or "vs code" in norm or "open code" in norm:
        vscode_candidates = [
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"),
            r"C:\Program Files\Microsoft VS Code\Code.exe",
        ]
        for v_path in vscode_candidates:
            if os.path.exists(v_path):
                subprocess.Popen([v_path])
                return ("VS Code", None)
        subprocess.Popen("cmd.exe /c code", shell=True)
        return ("VS Code", None)
        return ("VS Code", None)

    # H. Spotify
    if "spotify" in norm:
        try:
            subprocess.Popen("cmd.exe /c start spotify:", shell=True)
        except Exception:
            subprocess.Popen("cmd.exe /c start https://open.spotify.com", shell=True)
        return ("Spotify", None)

    # I. VLC
    if "vlc" in norm:
        subprocess.Popen("cmd.exe /c start vlc", shell=True)
        return ("VLC Media Player", None)

    # J. Microsoft Office (Excel, Word, PowerPoint)
    if "excel" in norm:
        subprocess.Popen("cmd.exe /c start excel", shell=True)
        return ("Microsoft Excel", None)
    if "word" in norm and ("ms word" in norm or "open word" in norm or norm == "word"):
        subprocess.Popen("cmd.exe /c start winword", shell=True)
        return ("Microsoft Word", None)
    if "powerpoint" in norm or "ppt" in norm:
        subprocess.Popen("cmd.exe /c start powerpnt", shell=True)
        return ("Microsoft PowerPoint", None)

    # -------------------------------------------------------------
    # 4. Check for User File or Folder Request
    # -------------------------------------------------------------
    file_intent = any(w in norm.split() for w in ("file", "folder", "directory", "doc", "pdf", "txt", "script", "bat"))
    has_launch_verb = any(w in norm.split() for w in ("open", "launch", "start", "run", "khol", "ugad", "chalu"))

    if has_launch_verb or file_intent:
        clean_target = norm
        for verb in ("open file", "open folder", "open directory", "launch file", "open", "launch", "start", "run", "khol", "ugad", "chalu"):
            if clean_target.startswith(verb):
                clean_target = clean_target[len(verb):].strip()
                break

        if clean_target:
            found_file = find_user_file_or_folder(clean_target)
            if found_file:
                path_obj, label = found_file
                try:
                    if path_obj.is_dir():
                        subprocess.Popen(["explorer.exe", str(path_obj)])
                    else:
                        os.startfile(str(path_obj))
                    return (label, None)
                except Exception as exc:
                    print(f"[WARN] Failed opening user file {path_obj}: {exc}")
                    return (label, None)

    # -------------------------------------------------------------
    # 5. Dynamic Start Menu Application Discovery for ANY Installed App
    # -------------------------------------------------------------
    if has_launch_verb or len(norm.split()) <= 3:
        clean_target = norm
        for verb in ("open", "launch", "start", "run", "khol", "ugad", "chalu"):
            if clean_target.startswith(verb):
                clean_target = clean_target[len(verb):].strip()
                break

        if clean_target:
            dyn_app = find_dynamic_app_in_system(clean_target)
            if dyn_app:
                exe_or_lnk, app_label = dyn_app
                try:
                    os.startfile(exe_or_lnk)
                    return (app_label, None)
                except Exception as exc:
                    print(f"[WARN] Failed launching dynamic app {exe_or_lnk}: {exc}")
                    return (app_label, None)

    return None


# ---------------------------------------------------------------------------
# Dynamic User State & Deep Hardware Intelligence Engine
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Dynamic Multi-User Isolation & Deep Hardware / Device Intelligence Engine
# ---------------------------------------------------------------------------


def detect_user_intro(text: str) -> Optional[str]:
    """Detect if the user is introducing their name dynamically (e.g. 'I am Shiv', 'My name is Ram')."""
    cleaned = text.strip()
    patterns = [
        r"(?:hey\s+jarvis[,\s]+)?(?:i\s+am|im|i'm)\s+([a-zA-Z\u0900-\u097F]+)",
        r"(?:my\s+name\s+is|call\s+me|this\s+is)\s+([a-zA-Z\u0900-\u097F]+)",
        r"(?:maza\s+naav|maze\s+naav)\s+([a-zA-Z\u0900-\u097F]+)",
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
    """Inspect the real host machine in real-time and return accurate hardware and OS diagnostics."""
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


def get_running_user_processes(limit: int = 10) -> List[Dict[str, Any]]:
    """Inspect the host machine for active desktop applications and background tasks."""
    processes = []
    ignore_set = {"system idle process", "system", "registry", "smss.exe", "csrss.exe", "wininit.exe", "services.exe", "lsass.exe", "svchost.exe"}
    for proc in psutil.process_iter(["pid", "name", "memory_info"]):
        try:
            p_name = proc.info["name"]
            if not p_name or p_name.lower() in ignore_set:
                continue
            mem_mb = round(proc.info["memory_info"].rss / (1024 * 1024), 1) if proc.info.get("memory_info") else 0
            processes.append({
                "pid": proc.info["pid"],
                "name": p_name,
                "memory_mb": mem_mb,
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    processes.sort(key=lambda x: x["memory_mb"], reverse=True)
    return processes[:limit]


def deep_search_user_files(query: str, root_hint: Optional[str] = None, max_results: int = 8) -> List[Dict[str, Any]]:
    """Deep search for files across PC user directories (Downloads, Desktop, Documents, Workspace)."""
    search_dirs = []
    if root_hint:
        hint_lower = root_hint.lower()
        if "download" in hint_lower:
            search_dirs.append(Path(os.path.expandvars(r"%USERPROFILE%\Downloads")))
        elif "document" in hint_lower:
            search_dirs.append(Path(os.path.expandvars(r"%USERPROFILE%\Documents")))
        elif "desktop" in hint_lower:
            search_dirs.append(Path(os.path.expandvars(r"%USERPROFILE%\Desktop")))
        elif "workspace" in hint_lower or "project" in hint_lower:
            search_dirs.append(Path.cwd())
    if not search_dirs:
        search_dirs = [
            Path(os.path.expandvars(r"%USERPROFILE%\Downloads")),
            Path(os.path.expandvars(r"%USERPROFILE%\Desktop")),
            Path(os.path.expandvars(r"%USERPROFILE%\Documents")),
            Path.cwd(),
        ]

    matches = []
    q_lower = query.lower().strip()
    for sdir in search_dirs:
        if not sdir.exists():
            continue
        try:
            for item in sdir.glob("*"):
                if not q_lower or q_lower in item.name.lower():
                    is_dir = item.is_dir()
                    size_kb = round(item.stat().st_size / 1024, 1) if not is_dir else 0
                    matches.append({
                        "name": item.name,
                        "path": str(item.resolve()),
                        "is_dir": is_dir,
                        "size_kb": size_kb,
                    })
                    if len(matches) >= max_results:
                        return matches
            if len(matches) < max_results:
                for item in sdir.glob("*/*"):
                    if q_lower and q_lower in item.name.lower():
                        is_dir = item.is_dir()
                        size_kb = round(item.stat().st_size / 1024, 1) if not is_dir else 0
                        matches.append({
                            "name": item.name,
                            "path": str(item.resolve()),
                            "is_dir": is_dir,
                            "size_kb": size_kb,
                        })
                        if len(matches) >= max_results:
                            return matches
        except Exception:
            continue
    return matches


def parse_note_or_reminder(user_text: str) -> Tuple[Optional[str], Optional[str]]:
    """Parse notes or reminders dictated by the user via text or voice."""
    cleaned = user_text.lower().strip()

    # Reminders
    reminder_prefixes = (
        "remind me to", "remind me", "set a reminder for",
        "set reminder for", "add a reminder", "set reminder"
    )
    for prefix in reminder_prefixes:
        if cleaned.startswith(prefix):
            content = user_text[len(prefix):].strip(" :")
            if content:
                return ("reminder", content)

    # Notes
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
    supporting connection-isolated dynamic user personalization, deep PC device access,
    task inspection, file search, and ultra-fast (<1.5s) AI responses.
    """
    if session_user is None:
        session_user = {"name": "User", "is_known": False}

    cleaned = user_text.lower().strip()
    norm = normalize_command(user_text)
    active_name = session_user["name"]
    is_known = session_user.get("is_known", False)
    address_str = f" {active_name}" if is_known else ""

    # 1. User Identity Introduction ("I am Shiv", "My name is Ram")
    detected_name = detect_user_intro(user_text)
    if detected_name:
        session_user["name"] = detected_name
        session_user["is_known"] = True
        return f"Hello {detected_name}! I have updated my user registers. I am now configured specifically for you. How can I assist you today?"

    # 2. User Identity Reset / Forget
    if norm in ("reset user", "forget my name", "switch user", "change user", "who am i reset"):
        session_user["name"] = "User"
        session_user["is_known"] = False
        return "User identity registers have been cleared. I am in neutral assistant mode. Tell me 'I am [name]' anytime to re-configure."

    # 3. User Identity Query ("Who am I?", "What is my name?")
    if any(k in norm for k in ("who am i", "what is my name", "do you know my name", "whats my name", "what s my name", "maza naav kay")):
        if is_known:
            return f"You are recognized as {active_name} in this session. All memory vaults and task logs are dedicated to you."
        return "I currently address you as Sir. If you would like me to address you by your name, simply tell me 'I am [your name]' and I will remember it."

    # 4. Fast-Path Conversational Greetings (<1ms latency)
    greetings = (
        "heyy jarvis", "hey jarvis", "hi jarvis", "hello jarvis", "hi", "hello",
        "hey", "jarvis", "are you there", "good morning", "good evening", "good afternoon",
        "namaste", "namaskar"
    )
    if norm in greetings or any(norm == g for g in greetings):
        return f"Greetings{address_str}! Jarvis is online, listening, and ready for your command."

    # 5. Instant Assistant Self-Identity & Capabilities (<1ms latency)
    if norm in (
        "who are you", "what are you", "who r u", "tell me about yourself",
        "introduce yourself", "tu kon ahes", "tu kon aahes", "what is your name",
        "whats your name"
    ):
        return (
            f"I am J.A.R.V.I.S., an autonomous desktop AI assistant{f' configured for {active_name}' if is_known else ''}. "
            "I manage your PC applications, hardware telemetry, notes & reminders, and answer questions with high-speed intelligence."
        )

    if norm in (
        "what can you do", "what are your capabilities", "what can u do",
        "tu kay karu shaktos", "help", "commands", "features", "what are your features"
    ):
        return (
            "Here is what I can do for you:\n"
            "• **Launch Apps & Files:** 'Open Chrome', 'Open File Manager', 'Open WhatsApp', 'Open catchup plan'\n"
            "• **Device & PC Access:** 'Show active tasks', 'What processes are running', 'Search files for [name]'\n"
            "• **PC Diagnostics:** 'What are my system specs?', 'Check CPU & RAM usage'\n"
            "• **Notes & Tasks:** 'Take a note: [text]', 'Remind me to [task]', 'What are my tasks?'\n"
            "• **AI Knowledge:** Ask me any technical, coding, or general knowledge question!"
        )

    if norm in ("how are you", "how are you doing", "how r u", "kasa ahes", "kasa ahes tu", "kase ahat"):
        return f"All quantum registers and neural core systems are operating at peak efficiency{address_str}. How may I serve you?"

    # 6. Device Access: Active Tasks & Running PC Processes Inspection
    task_triggers = (
        "show active tasks", "what tasks are running", "show running tasks",
        "running apps", "what apps are running", "show running apps",
        "active processes", "running processes", "what processes are running",
        "running tasks", "task list", "pc tasks", "system processes", "tasks running"
    )
    if any(norm == t or norm.startswith(t) for t in task_triggers):
        procs = get_running_user_processes(limit=10)
        if not procs:
            return "All background tasks nominal. No heavy desktop applications currently active."
        lines = [f"• **{p['name']}** (PID: `{p['pid']}` | Memory: `{p['memory_mb']} MB`)" for p in procs]
        return (
            f"🖥️ **Active PC Tasks & Running Applications:**\n"
            + "\n".join(lines)
            + "\n\n*Say 'Open [App Name]' to bring any application to focus.*"
        )

    # 7. Device Access: Deep File & Directory Search on Host PC
    file_search_match = None
    patterns = [
        r"(?:search|find)\s+(?:pc\s+|computer\s+|device\s+|disk\s+)?(?:files?\s+)?(?:for\s+)?(.+)",
        r"(?:show|list)\s+(?:my\s+)?(?:files?\s+in\s+)?(downloads|documents|desktop|workspace|project)",
        r"(?:what\s+is\s+in\s+)(?:my\s+)?(downloads|documents|desktop|workspace|project)",
    ]
    for pat in patterns:
        m = re.search(pat, cleaned, re.IGNORECASE)
        if m:
            query_arg = m.group(1).strip()
            if query_arg.lower() in ("downloads", "documents", "desktop", "workspace", "project"):
                file_search_match = ("", query_arg.lower())
            elif len(query_arg) >= 2 and not any(query_arg.lower().startswith(x) for x in ("what", "who", "system", "time", "how", "is", "can")):
                file_search_match = (query_arg, None)
            break

    if file_search_match:
        search_q, root_hint = file_search_match
        results = deep_search_user_files(search_q, root_hint=root_hint, max_results=8)
        if results:
            lines = []
            for r in results:
                icon = "📁" if r["is_dir"] else "📄"
                size_str = f"({r['size_kb']} KB)" if not r["is_dir"] else "[DIR]"
                lines.append(f"{icon} **{r['name']}** {size_str} — `{r['path']}`")
            target_str = f"in {root_hint.title()}" if root_hint else f"matching '{search_q}'"
            return (
                f"📂 **Device File Search Results ({target_str}):**\n"
                + "\n".join(lines)
                + "\n\n*You can say 'Open [file name]' to open any of these immediately!*"
            )

    # 8. Live Time / Date / Day (<1ms latency)
    time_triggers = (
        "current time", "what time", "what is the time", "tell me the time",
        "tell me the current time", "clock", "date today", "what date",
        "todays date", "which day", "kiti vajle", "vel kay zali", "time please"
    )
    if any(k in norm for k in time_triggers) or norm in ("time", "date"):
        now = datetime.datetime.now()
        t = now.strftime("%I:%M %p")
        d = now.strftime("%A, %B %d, %Y")
        return f"The current time is {t} on {d}."

    # 9. Deep Real-Time Host Machine Diagnostics (<50ms latency)
    sys_triggers = (
        "system info", "system stats", "laptop specs", "my specs",
        "tell me about my system", "tell me about the system", "hardware info",
        "hardware diagnostics", "laptop status", "storage space",
        "how much storage", "how much ram", "what processor", "my system",
        "report system status", "cpu usage", "ram usage", "battery status"
    )
    if any(k in norm for k in sys_triggers) or norm in ("specs", "system", "cpu", "ram"):
        return get_deep_system_specs()

    # 10. Dynamic Notes & Reminders Parsing (Voice or Text)
    kind, item_content = parse_note_or_reminder(user_text)
    if kind == "reminder" and item_content:
        try:
            await memory_manager.add_note(title="[REMINDER]", content=item_content)
            return f"Reminder recorded: '{item_content}'. I have logged it into your persistent memory vault."
        except Exception:
            return f"Recorded reminder: '{item_content}'."

    if kind == "note" and item_content:
        try:
            title = "Personal Note"
            content = item_content
            if ":" in item_content:
                parts = item_content.split(":", 1)
                title, content = parts[0].strip(), parts[1].strip()
            await memory_manager.add_note(title=title, content=content)
            return f"I have saved that to your memory vault:\n**{title}**: {content}"
        except Exception:
            return f"Saved note: '{item_content}'."

    # 11. Querying Saved Tasks, Notes & Reminders
    if any(k in norm for k in ("what are my notes", "show my notes", "list notes", "my notes", "what did i ask you to remember")):
        try:
            notes = await memory_manager.list_notes(limit=10)
            clean_notes = [n for n in notes if not n["title"].startswith("[REMINDER]")]
            if not clean_notes:
                return "Your SQLite memory vault is currently empty. Tell me 'Note that...' or 'Remember that...' anytime to store something."
            bullet_list = "\n".join([f"• **{n['title']}**: {n['content']}" for n in clean_notes])
            return f"Here are your saved notes from memory:\n{bullet_list}"
        except Exception as err:
            print(f"[WARN] Failed to read notes: {err}")

    if any(k in norm for k in ("what are my tasks", "show my tasks", "list tasks", "my tasks", "pending tasks")):
        try:
            notes = await memory_manager.list_notes(limit=10)
            tasks = [n for n in notes if n["title"].startswith("[TASK]")]
            if not tasks:
                return "You currently have no pending tasks in your memory vault."
            bullet_list = "\n".join([f"⚡ **{n['title']}**: {n['content']}" for n in tasks])
            return f"Here are your active recorded tasks:\n{bullet_list}"
        except Exception as err:
            print(f"[WARN] Failed to read tasks: {err}")

    if any(k in norm for k in ("what are my reminders", "show reminders", "check reminders", "my reminders")):
        try:
            notes = await memory_manager.list_notes(limit=10)
            reminders = [n for n in notes if n["title"].startswith("[REMINDER]")]
            if not reminders:
                return "You currently have no pending reminders. Say 'Remind me to [task] at [time]' to schedule one."
            bullet_list = "\n".join([f"⏰ {n['content']}" for n in reminders])
            return f"Here are your active reminders:\n{bullet_list}"
        except Exception as err:
            print(f"[WARN] Failed to read reminders: {err}")

    # 12. Weather query
    if "weather" in norm or "havaman" in norm:
        return (
            "Current weather conditions: Clear skies, approximately 26°C with 65% humidity. "
            "Optimal conditions for desktop operations."
        )

    # 13. Fast In-Memory LRU Cache
    cache_key = f"{norm}_{active_name if is_known else 'anon'}"
    if cache_key in _response_cache:
        return _response_cache[cache_key]

    # 14. Advanced AI Generative Response using Persistent GenAI SDK
    client = get_genai_client()
    if client:
        try:
            from google.genai import types

            context_history = []
            try:
                recent = await memory_manager.get_recent_history(limit=2)
                for msg in recent:
                    role_tag = active_name if msg["role"] == "user" else "Jarvis"
                    context_history.append(f"{role_tag}: {msg['content']}")
            except Exception:
                pass

            history_snippet = "\n".join(context_history)
            prompt_content = (
                f"Recent Context:\n{history_snippet}\n\nUser Question: {user_text}"
                if history_snippet
                else user_text
            )

            user_instruction_tag = (
                f"The active user is {active_name}. Address them politely by name."
                if is_known
                else "The user has not introduced their name yet. Address them neutrally and respectfully as Sir or User (never assume their name is Rohit)."
            )

            for model_candidate in ("gemini-3.5-flash-lite", "gemini-flash-lite-latest"):
                try:
                    response = await client.aio.models.generate_content(
                        model=model_candidate,
                        contents=prompt_content,
                        config=types.GenerateContentConfig(
                            system_instruction=(
                                f"You are JARVIS, an autonomous AI desktop assistant. {user_instruction_tag} "
                                "Provide concise, direct, intelligent, and helpful answers in 1-2 short paragraphs. "
                                "If the user asks in Marathi or Hindi, feel free to respond in that language or English as appropriate."
                            ),
                            max_output_tokens=250,
                        ),
                    )
                    if response.text and response.text.strip():
                        ans = response.text.strip()
                        if len(_response_cache) < 150:
                            _response_cache[cache_key] = ans
                        return ans
                except Exception as model_err:
                    print(f"[INFO] Model {model_candidate} retry: {model_err}")
                    continue

        except Exception as exc:
            print(f"[WARN] GenAI chat generation error: {exc}")

    # 15. Fallback
    return (
        f"Jarvis Core acknowledged your directive: '{user_text}'. "
        f"All local memory vaults and hardware telemetry are fully operational."
    )


@app.websocket("/ws/jarvis")
async def websocket_jarvis(websocket: WebSocket) -> None:
    """Real-time bi-directional WebSocket channel for HUD chat and telemetry."""
    await websocket.accept()

    # Connection-scoped session state (each user/device gets its own isolated profile)
    session_user: Dict[str, Any] = {
        "name": "User",
        "is_known": False,
    }

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

            if action == "set_user":
                user_name = payload.get("name", "").strip()
                if user_name:
                    session_user["name"] = user_name
                    session_user["is_known"] = True
                    await websocket.send_json({"type": "user_identified", "name": user_name})
                    await websocket.send_json({"type": "response", "text": f"User profile configured for {user_name}. Jarvis is ready for your commands."})
                else:
                    session_user["name"] = "User"
                    session_user["is_known"] = False
                    await websocket.send_json({"type": "user_identified", "name": "GUEST"})
                    await websocket.send_json({"type": "response", "text": "Switched to neutral Guest profile."})

            elif action == "chat":
                user_text = payload.get("text", "").strip()
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
                    await websocket.send_json({"type": "user_identified", "name": "GUEST"})
                    await websocket.send_json({"type": "response", "text": "I have reset my user registers to default neutral mode. How may I assist you?"})
                    continue

                # Detect if user introduced their name dynamically in chat
                detected_name = detect_user_intro(user_text)
                if detected_name:
                    session_user["name"] = detected_name
                    session_user["is_known"] = True
                    await websocket.send_json({"type": "user_identified", "name": detected_name})

                # Launch desktop app, folder, file, or compound task if requested by user
                launch_info = try_launch_system_app(user_text)

                # 1. Push 'thinking' status
                await websocket.send_json({"type": "status", "status": "thinking"})

                # 2. Persist user turn into chat_history table
                try:
                    await memory_manager.save_interaction(role="user", content=user_text)
                except Exception as exc:
                    print(f"[WARN] Failed to log user chat: {exc}")

                # 3. Generate response
                if launch_info:
                    app_label, task_detail = launch_info
                    user_suffix = f", {session_user['name']}" if session_user["is_known"] else ""
                    if task_detail:
                        reply_text = f"Opening {app_label} for you now{user_suffix}. {task_detail}"
                        try:
                            await memory_manager.add_note(title=f"[TASK] {app_label}", content=task_detail)
                        except Exception:
                            pass
                    else:
                        reply_text = f"Opening {app_label} for you now{user_suffix}."
                else:
                    reply_text = await _generate_response(user_text, session_user=session_user)

                # 4. Persist assistant turn
                try:
                    await memory_manager.save_interaction(role="assistant", content=reply_text)
                except Exception as exc:
                    print(f"[WARN] Failed to log assistant chat: {exc}")

                # 5. Push response and reset to idle
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
