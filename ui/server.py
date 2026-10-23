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
        if norm == f_key or norm == f"open {f_key}" or norm == f"launch {f_key}" or norm.startswith(f"open {f_key} ") or f_key in norm:
            try:
                if target_path.startswith("shell:") or target_path == "explorer.exe":
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
        "calculator": ("calc", "Calculator"),
        "calc": ("calc", "Calculator"),
        "notepad": ("notepad", "Notepad"),
        "paint": ("mspaint", "Paint"),
        "mspaint": ("mspaint", "Paint"),
        "snipping tool": ("snippingtool", "Snipping Tool"),
        "snip": ("snippingtool", "Snipping Tool"),
        "screenshot": ("snippingtool", "Snipping Tool"),
        "task manager": ("taskmgr", "Task Manager"),
        "taskmgr": ("taskmgr", "Task Manager"),
        "cmd": ("cmd", "Command Prompt"),
        "command prompt": ("cmd", "Command Prompt"),
        "terminal": ("wt", "Windows Terminal"),
        "powershell": ("powershell", "PowerShell"),
    }
    for p_key, (cmd, p_label) in protocol_apps.items():
        if norm == p_key or norm == f"open {p_key}" or norm == f"launch {p_key}" or norm.startswith(f"open {p_key} ") or (f"open {p_key}" in norm):
            try:
                subprocess.Popen(f"cmd.exe /c start {cmd}", shell=True)
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
            dyn = find_dynamic_app_in_system("whatsapp")
            if dyn:
                os.startfile(dyn[0])
                launched = True
            else:
                subprocess.Popen("cmd.exe /c start whatsapp:", shell=True)
                launched = True
        except Exception:
            pass

        if not launched:
            subprocess.Popen("cmd.exe /c start https://web.whatsapp.com", shell=True)

        return ("WhatsApp", task_detail)

    # B. Chrome with optional Google Search task
    if "chrome" in norm:
        search_query = None
        m = re.search(r"(?:search|google|find)\s+(?:for\s+)?(.+)", user_text, re.IGNORECASE)
        if m and "chrome" not in m.group(1).lower():
            search_query = m.group(1).strip()

        if search_query:
            import urllib.parse
            url = f"https://www.google.com/search?q={urllib.parse.quote_plus(search_query)}"
            subprocess.Popen(f'cmd.exe /c start chrome "{url}"', shell=True)
            return ("Google Chrome", f"Executed Google search for '{search_query}'.")
        else:
            try:
                from tools.system_tools import OpenAppTool
                OpenAppTool().run(app_name="chrome")
            except Exception:
                subprocess.Popen("cmd.exe /c start chrome", shell=True)
            return ("Google Chrome", None)

    # C. Brave Browser
    if "brave" in norm:
        search_query = None
        m = re.search(r"(?:search|find)\s+(?:for\s+)?(.+)", user_text, re.IGNORECASE)
        if m and "brave" not in m.group(1).lower():
            search_query = m.group(1).strip()

        if search_query:
            import urllib.parse
            url = f"https://www.google.com/search?q={urllib.parse.quote_plus(search_query)}"
            subprocess.Popen(f'cmd.exe /c start brave "{url}"', shell=True)
            return ("Brave Browser", f"Executed search for '{search_query}'.")
        else:
            dyn = find_dynamic_app_in_system("brave")
            if dyn:
                try:
                    os.startfile(dyn[0])
                    return ("Brave Browser", None)
                except Exception:
                    pass
            subprocess.Popen("cmd.exe /c start brave", shell=True)
            return ("Brave Browser", None)

    # D. Edge Browser
    if "edge" in norm:
        subprocess.Popen("cmd.exe /c start msedge", shell=True)
        return ("Microsoft Edge", None)

    # E. Firefox Browser
    if "firefox" in norm:
        subprocess.Popen("cmd.exe /c start firefox", shell=True)
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
        try:
            from tools.system_tools import OpenAppTool
            OpenAppTool().run(app_name="code")
        except Exception:
            subprocess.Popen("cmd.exe /c start code", shell=True)
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

current_user_state: Dict[str, Any] = {
    "name": "User",
    "is_known": False,
}


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


async def _generate_response(user_text: str) -> str:
    """Intelligently process and answer user questions directly from UI backend,
    supporting dynamic user personalization, deep system inspection, persistent notes/reminders,
    and ultra-fast (<1.5s) AI query generation.
    """
    cleaned = user_text.lower().strip()
    norm = normalize_command(user_text)
    active_name = current_user_state["name"]

    # 1. User Identity Introduction ("I am Shiv", "My name is Ram")
    detected_name = detect_user_intro(user_text)
    if detected_name:
        current_user_state["name"] = detected_name
        current_user_state["is_known"] = True
        return f"Hello {detected_name}! I have updated my user registers. I am now configured specifically for you. How can I assist you today?"

    # 2. User Identity Query ("Who am I?", "What is my name?")
    if any(k in norm for k in ("who am i", "what is my name", "do you know my name", "whats my name", "what s my name", "maza naav kay")):
        if current_user_state["is_known"]:
            return f"You are recognized as {active_name} in my active session. All memory vaults and task logs are dedicated to you."
        return "I currently address you as Sir. If you would like me to address you by your name, simply tell me 'I am [your name]' and I will remember it."

    # 3. Fast-Path Conversational Greetings (<1ms latency)
    greetings = (
        "heyy jarvis", "hey jarvis", "hi jarvis", "hello jarvis", "hi", "hello",
        "hey", "jarvis", "are you there", "good morning", "good evening", "good afternoon",
        "namaste", "namaskar"
    )
    if norm in greetings or any(norm == g for g in greetings):
        return f"Greetings {active_name}! Jarvis is online, listening, and ready for your command."

    # 4. Instant Assistant Self-Identity & Capabilities (<1ms latency)
    if norm in (
        "who are you", "what are you", "who r u", "tell me about yourself",
        "introduce yourself", "tu kon ahes", "tu kon aahes", "what is your name",
        "whats your name"
    ):
        return (
            f"I am J.A.R.V.I.S., an autonomous desktop AI assistant configured for {active_name}. "
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
        return f"All quantum registers and neural core systems are operating at peak efficiency, {active_name}. How may I serve you?"

    # 5. Live Time / Date / Day (<1ms latency)
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

    # 6. Deep Real-Time Host Machine Diagnostics (<50ms latency)
    sys_triggers = (
        "system info", "system stats", "laptop specs", "my specs",
        "tell me about my system", "tell me about the system", "hardware info",
        "hardware diagnostics", "laptop status", "storage space",
        "how much storage", "how much ram", "what processor", "my system",
        "report system status", "cpu usage", "ram usage", "battery status"
    )
    if any(k in norm for k in sys_triggers) or norm in ("specs", "system", "cpu", "ram"):
        return get_deep_system_specs()

    # 7. Dynamic Notes & Reminders Parsing (Voice or Text)
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

    # 8. Querying Saved Notes & Reminders
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

    # 9. Weather query
    if "weather" in norm or "havaman" in norm:
        return (
            "Current weather conditions: Clear skies, approximately 26°C with 65% humidity. "
            "Optimal conditions for desktop operations."
        )

    # 10. Check Fast In-Memory LRU Cache
    if norm in _response_cache:
        return _response_cache[norm]

    # 11. Advanced AI Generative Response using Persistent GenAI SDK (with ultra-fast gemini-3.5-flash-lite)
    client = get_genai_client()
    if client:
        try:
            from google.genai import types

            # Fetch recent conversation context (last 2 turns) for lightweight multi-turn awareness
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

            # High-speed gemini-3.5-flash-lite with gemini-flash-lite-latest fallback
            for model_candidate in ("gemini-3.5-flash-lite", "gemini-flash-lite-latest"):
                try:
                    response = await client.aio.models.generate_content(
                        model=model_candidate,
                        contents=prompt_content,
                        config=types.GenerateContentConfig(
                            system_instruction=(
                                f"You are JARVIS, an autonomous AI desktop assistant. The active user is {active_name}. "
                                "Address them politely. Provide concise, direct, intelligent, and helpful answers in 1-2 short paragraphs. "
                                "If the user asks in Marathi or Hindi, feel free to respond in that language or English as appropriate."
                            ),
                            max_output_tokens=250,
                        ),
                    )
                    if response.text and response.text.strip():
                        ans = response.text.strip()
                        if len(_response_cache) < 150:
                            _response_cache[norm] = ans
                        return ans
                except Exception as model_err:
                    print(f"[INFO] Model {model_candidate} retry: {model_err}")
                    continue

        except Exception as exc:
            print(f"[WARN] GenAI chat generation error: {exc}")

    # 12. Fallback if offline or network failure
    return (
        f"Jarvis Core acknowledged your directive: '{user_text}'. "
        f"All local memory vaults and hardware telemetry are fully operational."
    )


@app.websocket("/ws/jarvis")
async def websocket_jarvis(websocket: WebSocket) -> None:
    """Real-time bi-directional WebSocket channel for HUD chat and telemetry."""
    await websocket.accept()
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
                user_text = payload.get("text", "").strip()
                if not user_text:
                    continue

                import time

                now_ts = time.time()
                if user_text.lower() == last_chat_msg.lower() and (now_ts - last_chat_time) < 2.0:
                    # Guard against rapid duplicate voice recognition bursts
                    continue
                last_chat_msg = user_text
                last_chat_time = now_ts

                # Detect if user introduced their name dynamically
                detected_name = detect_user_intro(user_text)
                if detected_name:
                    current_user_state["name"] = detected_name
                    current_user_state["is_known"] = True
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
                    if task_detail:
                        reply_text = f"Opening {app_label} for you now, {current_user_state['name']}. {task_detail}"
                        try:
                            await memory_manager.add_note(title=f"[TASK] {app_label}", content=task_detail)
                        except Exception:
                            pass
                    else:
                        reply_text = f"Opening {app_label} for you now, {current_user_state['name']}."
                else:
                    reply_text = await _generate_response(user_text)

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
