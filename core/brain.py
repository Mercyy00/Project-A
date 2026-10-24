"""Jarvis Core Brain Engine.

Orchestrates multi-turn conversational reasoning, system prompt personas,
and autonomous function calling (ReAct loop) using Google Gemini.
Adheres strictly to Project Jarvis architecture and module contracts.
"""

from __future__ import annotations

import datetime
import ast
import inspect
import operator
import json
import os
import re
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, Generator, Iterator, List, Optional

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types


DEFAULT_SYSTEM_PROMPT: str = (
    "You are JARVIS, the ultra-fast, highly sophisticated AI desktop assistant inspired by Tony Stark's JARVIS. "
    "Address the user respectfully as 'sir' with a razor-sharp, cool, and subtly witty British cadence. "
    "CRITICAL CONVERSATIONAL RULE: Keep responses under 20 words in 1 or 2 punchy, spoken sentences suitable for instant voice synthesis. Never write conversational filler, long disclaimers, or paragraphs. "
    "STRICT TOOL EXECUTION MANDATE: Whenever the user requests an action on their computer (opening apps, opening settings, setting volume or brightness, locking screen, managing windows, running commands, controlling browsers like opening browser, new tab, closing tab, closing browser with browser_control, inspecting what is on screen with describe_screen/capture_screen, organizing desktop with organize_desktop, reading/writing/opening files, creating documents/presentations, checking weather with weather_report, dispatching to Antigravity with antigravity_prompt, sending Telegram or WhatsApp messages, searching saved WhatsApp contacts, or taking notes), YOU MUST INVOKE THE APPROPRIATE TOOL. "
    "DOCUMENT CREATION: For current or recent factual documents, research with search_web first and pass the verified findings into the creator. Use create_document for a topic-driven original outline or create_pdf for your own tailored sections; do not use a template unless requested. Match the selected visual theme to the user's style direction. "
    "ZERO-PHANTOM RULE: NEVER claim, simulate, or hallucinate that you performed any action unless you actually invoked the corresponding tool and received a successful response. If a tool call fails, state the failure honestly and crisply. "
    "STATE AWARENESS: You possess ZERO psychic knowledge of the computer state. You do not know what windows are active, what files exist, what is on the clipboard, or what the telemetry is until you call the respective inspection tool (list_windows, list_directory, clipboard_read, get_system_stats, battery). Never invent or guess desktop states. "
    "MULTILINGUAL RULE: Respond in the user's language (English, Hindi, Marathi, or Hinglish). When speaking Hindi or Marathi, always output in native Devanagari script so the speech synthesizer pronounces it flawlessly. "
    "CONFIRMATION FLOW: For Telegram/WhatsApp message sends (including attachments), file overwrites, or destructive commands, still invoke the requested tool so JARVIS can prepare an explicit confirmation token; the tool gate will not perform the action yet. Show the exact 'CONFIRM <token>' request and wait for the user to provide that token. Do not replace the token flow with a vague yes/no question. "
    "SAFETY: Never execute destructive actions until the user provides the exact confirmation token returned by the tool gate."
)


def _compact_json_schema(value: Any) -> Any:
    """Remove verbose schema metadata while preserving model-callable structure."""
    if isinstance(value, dict):
        compacted: Dict[str, Any] = {}
        for key, item in value.items():
            if key in {"description", "title", "default", "examples", "example"}:
                continue
            if key == "enum" and isinstance(item, list) and len(item) > 16:
                continue
            compacted[key] = _compact_json_schema(item)
        return compacted
    if isinstance(value, list):
        return [_compact_json_schema(item) for item in value]
    return value


def _groq_tool_definitions(schemas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert registry schemas to compact Groq-compatible function tools."""
    definitions: List[Dict[str, Any]] = []
    for schema in schemas:
        definitions.append(
            {
                "type": "function",
                "function": {
                    "name": schema["name"],
                    "description": (schema.get("description") or "")[:100],
                    "parameters": _compact_json_schema(
                        schema.get("parameters", {"type": "object", "properties": {}})
                    ),
                },
            }
        )
    return definitions


def load_api_key(env_path: Optional[Path] = None) -> str:
    """Retrieve GEMINI_API_KEY from environment or .env file.

    Args:
        env_path: Optional explicit filesystem path to the .env file.

    Returns:
        The validated Gemini API key string.

    Raises:
        ValueError: If GEMINI_API_KEY is not configured or uses placeholder text.
    """
    if env_path is not None:
        load_dotenv(dotenv_path=env_path)
    else:
        project_root: Path = Path(__file__).resolve().parent.parent
        default_env: Path = project_root / ".env"
        if default_env.exists():
            load_dotenv(dotenv_path=default_env)
        else:
            load_dotenv()

    api_key: Optional[str] = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key.strip() == "" or api_key.strip() == "your_gemini_api_key_here":
        raise ValueError(
            "GEMINI_API_KEY is missing or invalid. "
            "Please copy .env.example to .env and configure your GEMINI_API_KEY."
        )
    return api_key.strip()


class JarvisBrain:
    """Core brain and conversation orchestrator for Project Jarvis."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        system_prompt: Optional[str] = None,
        enable_tools: bool = True,
        load_memory: bool = False,
    ) -> None:
        """Initialize JarvisBrain with API client, chat session, and tool registry.

        Args:
            model_name: Optional Gemini model name identifier (defaults to MODEL_NAME env or 'gemini-3.8-flash').
            system_prompt: Optional custom persona instructions.
            enable_tools: Whether to auto-discover and register tools for function calling.
        """
        gemini_key_error: Optional[ValueError] = None
        try:
            api_key: Optional[str] = load_api_key()
        except ValueError as exc:
            gemini_key_error = exc
            api_key = None
        self.groq_api_key: Optional[str] = os.getenv("GROQ_API_KEY")
        if self.groq_api_key and self.groq_api_key.strip() in (
            "",
            "your_groq_api_key_here",
        ):
            self.groq_api_key = None
        if not api_key and not self.groq_api_key:
            raise ValueError(
                "JARVIS needs at least one valid provider key: GEMINI_API_KEY or GROQ_API_KEY."
            ) from gemini_key_error
        self.model_name: str = (
            model_name or os.getenv("GEMINI_MODEL") or os.getenv("MODEL_NAME") or "gemini-3.8-flash"
        )
        self.system_prompt: str = system_prompt or DEFAULT_SYSTEM_PROMPT
        self.enable_tools: bool = enable_tools
        self.history: List[Dict[str, str]] = []
        self.max_history_entries: int = int(os.getenv("MAX_HISTORY_ENTRIES", "20"))
        self.last_tool_steps: List[str] = []

        self.groq_model: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
        self.llm_provider: str = os.getenv("LLM_PROVIDER", "gemini").lower()
        if not api_key:
            self.llm_provider = "groq"
        self._cancel_event: Optional[Any] = None

        self.client: Optional[genai.Client] = genai.Client(api_key=api_key) if api_key else None
        self.tools: List[Callable[..., Any]] = self._discover_tools() if enable_tools else []
        if load_memory:
            self._load_memory_history()
        self._init_chat_session()

    def _execute_registered_tool(
        self,
        name: str,
        args: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Dispatch a registered tool, requiring user confirmation for risky actions."""
        from tools.registry import execute_tool

        call_args = args or {}
        confirmation_reason: Optional[str] = None
        if name == "send_telegram":
            message = str(call_args.get("text", "")).strip()
            confirmation_reason = f"Send this Telegram message to the configured owner: {message}"
            attachment = str(call_args.get("file_path", "")).strip()
            if attachment:
                confirmation_reason += f" Attach file: {attachment}"
        elif name == "send_whatsapp":
            contact = str(call_args.get("contact", "")).strip()
            message = str(call_args.get("message", "")).strip()
            confirmation_reason = f"Send this WhatsApp message to saved contact '{contact}': {message}"
        elif name == "write_file" and call_args.get("overwrite") is True:
            confirmation_reason = (
                f"Overwrite file '{call_args.get('file_path', '')}' with the requested content."
            )
        elif name == "run_command" and re.search(
            r"\b(?:del|erase|rm|rmdir|remove-item|format)\b",
            str(call_args.get("command", "")),
            flags=re.IGNORECASE,
        ):
            confirmation_reason = f"Run this potentially destructive command: {call_args.get('command', '')}"
        elif name == "run_python" and re.search(
            r"\.(?:remove|unlink|rmdir)\s*\(|\b(?:rmtree|remove|unlink)\s*\(",
            str(call_args.get("code", "")),
            flags=re.IGNORECASE,
        ):
            confirmation_reason = "Run Python code that may delete or remove files."

        if confirmation_reason:
            from core.confirm import requires_confirmation
            from tools.base import ToolResult

            prompt = requires_confirmation(
                operation=name,
                description=confirmation_reason,
                callback=execute_tool,
                name=name,
                args=call_args,
            )
            return ToolResult(
                success=False,
                data={"confirmation_required": True},
                message=prompt,
            )

        return execute_tool(name, call_args)

    def _execute_compound_local_request(self, text: str) -> Optional[str]:
        """Execute clearly phrased desktop/search/math sub-actions without an LLM.

        This narrow parser is a resilience path for common compound requests; it
        only recognizes explicit searches, known local apps/folders, time, and
        arithmetic. Unsupported or ambiguous requests remain with the reasoning model.
        """
        if not re.search(r"\b(?:and then|and also|then|also)\b", text, re.IGNORECASE):
            return None

        search_pattern = re.compile(
            r"\bsearch\s+(?:(?:about|for)\s+)?(.+?)"
            r"(?=\s+(?:and\s+then|then|and\s+also|also)\s+|[,;]|$)",
            re.IGNORECASE,
        )
        searches = [match.group(1).strip(" .?!'“”") for match in search_pattern.finditer(text)]
        actions: List[tuple[str, Dict[str, Any]]] = []
        browser_match = re.search(r"\b(?:on|in|open)\s+(chrome|google chrome|edge|firefox|brave)\b", text, re.IGNORECASE)
        requested_browser = browser_match.group(1).lower().replace("google ", "") if browser_match else None
        for query in searches:
            if query:
                args: Dict[str, Any] = {"action": "search", "query": query}
                if requested_browser:
                    args["browser"] = requested_browser
                actions.append(("browser_control", args))

        normalized = text.lower()
        if re.search(r"\b(?:downloads? folder|my downloads|open downloads)\b", normalized):
            actions.append(("open_file", {"file_path": "Downloads"}))
        if re.search(r"\b(?:open )?(?:the )?calculator\b", normalized):
            actions.append(("open_app", {"app_name": "calculator"}))

        has_time = bool(re.search(r"\b(?:what(?:'s| is) the time|what time|tell me the time)\b", normalized))
        if has_time:
            now = datetime.datetime.now().astimezone()
            actions.append(("__time__", {"value": now.strftime("%I:%M %p").lstrip("0")}))

        expression_match = re.search(
            r"\bwhat(?:'s| is)\s+((?:\d+(?:\.\d+)?\s*(?:\+|-|\*|/|plus|minus|times|into|multiplied\s+by|divided\s+by)\s*)+\d+(?:\.\d+)?)",
            text,
            re.IGNORECASE,
        )
        if expression_match:
            expression = expression_match.group(1)
            for word, symbol in (("plus", "+"), ("minus", "-"), ("times", "*"),
                                 ("into", "*"), ("multiplied by", "*"), ("divided by", "/")):
                expression = re.sub(rf"\b{word}\b", symbol, expression, flags=re.IGNORECASE)
            try:
                result = self._evaluate_arithmetic(expression)
                actions.append(("__math__", {"expression": expression, "value": result}))
            except (ValueError, ZeroDivisionError):
                pass

        if len(actions) < 2:
            return None

        outcomes: List[str] = []
        all_tools_succeeded = True
        for tool_name, args in actions:
            if self.is_interrupted:
                break
            if tool_name == "__time__":
                outcomes.append(f"It is {args['value']}.")
                continue
            if tool_name == "__math__":
                value = args["value"]
                shown = int(value) if isinstance(value, float) and value.is_integer() else value
                outcomes.append(f"{args['expression']} = {shown}.")
                continue
            result = self._execute_registered_tool(tool_name, args)
            self.last_tool_steps.append(f"{tool_name}({args})")
            if getattr(result, "success", False):
                outcomes.append(str(getattr(result, "message", "Action completed.")))
            else:
                all_tools_succeeded = False
                outcomes.append(f"Could not complete {tool_name}: {getattr(result, 'message', 'unknown error')}.")

        if not outcomes:
            return None
        prefix = "Completed the requested steps: " if all_tools_succeeded else "Some requested steps failed: "
        response = prefix + " ".join(outcomes)
        self.history.extend([
            {"role": "user", "content": text},
            {"role": "model", "content": response},
        ])
        self.compact_history()
        return response

    def _execute_local_document_request(self, text: str) -> Optional[str]:
        """Use the document generator directly for explicit create-file requests."""
        match = re.search(
            r"\b(?:create|make|generate|build)\s+(?:me\s+)?(?:a\s+)?"
            r"(pdf|pptx|powerpoint(?:\s+presentation)?|presentation|docx|word(?:\s+document)?)"
            r"\s+(?:about|on|for)\s+(.+?)\s*[.!?]*$",
            text,
            re.IGNORECASE,
        )
        if not match:
            return None

        requested_format = match.group(1).lower()
        topic = match.group(2).strip()
        if not topic:
            return None
        kind = "pdf" if requested_format == "pdf" else (
            "docx" if requested_format.startswith("word") or requested_format == "docx" else "pptx"
        )
        theme = "dark_pro" if re.search(r"\b(?:dark|modern warfare|mw style|sci.?fi|futuristic)\b", topic, re.I) else "clean_light"
        topic = re.sub(r"\s+(?:in|with)\s+(?:a\s+)?(?:dark|mw|modern warfare|sci.?fi|futuristic)\s+style\s*$", "", topic, flags=re.I).strip()

        reference_material: List[Dict[str, str]] = []
        wants_current_facts = bool(re.search(r"\b(?:latest|current|recent|newest|today)\b", topic, re.I))
        if wants_current_facts:
            try:
                from ddgs import DDGS

                search_results = DDGS().text(topic[:240], max_results=5)
                for item in search_results[:5]:
                    if not isinstance(item, dict):
                        continue
                    reference_material.append({
                        "title": str(item.get("title", ""))[:240],
                        "body": str(item.get("body", ""))[:900],
                        "href": str(item.get("href", ""))[:500],
                    })
            except Exception as search_exc:
                logger.warning("Could not retrieve current document sources: %s", search_exc)

        try:
            args: Dict[str, Any] = {
                "topic": topic,
                "kind": kind,
                "theme": theme,
                "auto_open": True,
            }
            if reference_material:
                args["reference_material"] = json.dumps(reference_material, ensure_ascii=False)
            result = self._execute_registered_tool(
                "create_document",
                args,
            )
            self.last_tool_steps.append(f"create_document(topic={topic!r}, kind={kind!r})")
            message = str(getattr(result, "message", ""))
            if not getattr(result, "success", False):
                response = f"I couldn't create the {kind.upper()} document: {message or 'the document tool failed.'}"
            else:
                path = getattr(result, "data", None) or {}
                file_path = path.get("file_path") if isinstance(path, dict) else None
                response = f"Created the {kind.upper()} document."
                if file_path:
                    response += f" Saved at {file_path}."
                if reference_material:
                    response += f" It includes {len(reference_material)} live search sources."
                elif wants_current_facts:
                    response += " I could not retrieve live sources, so verify current details before relying on it."
        except Exception as exc:
            response = f"I couldn't create the {kind.upper()} document: {exc}"

        self.history.extend([
            {"role": "user", "content": text},
            {"role": "model", "content": response},
        ])
        self.compact_history()
        return response

    @staticmethod
    def _evaluate_arithmetic(expression: str) -> float:
        """Evaluate a basic arithmetic expression without executing arbitrary code."""
        binary_ops: Dict[type, Callable[[Any, Any], Any]] = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
        }

        def visit(node: ast.AST) -> float:
            if isinstance(node, ast.Expression):
                return visit(node.body)
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                return float(node.value)
            if isinstance(node, ast.BinOp) and type(node.op) in binary_ops:
                return float(binary_ops[type(node.op)](visit(node.left), visit(node.right)))
            if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
                value = visit(node.operand)
                return value if isinstance(node.op, ast.UAdd) else -value
            raise ValueError("Only basic arithmetic is supported.")

        return visit(ast.parse(expression, mode="eval"))

    def _load_memory_history(self, limit: int = 6) -> None:
        """Load recent interaction history from SQLite memory vault if available."""
        try:
            import asyncio
            from memory.storage import MemoryManager
            mem = MemoryManager()

            async def _fetch():
                return await mem.get_recent_history(limit=limit)

            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                        rows = pool.submit(asyncio.run, _fetch()).result(timeout=2)
                else:
                    rows = loop.run_until_complete(_fetch())
            except Exception:
                rows = asyncio.run(_fetch())

            if rows:
                for row in rows:
                    role = "user" if row.get("role") == "user" else "model"
                    content = row.get("content", "").strip()
                    if content:
                        self.history.append({"role": role, "content": content})
        except Exception:
            pass

    def interrupt(self) -> bool:
        """Instantly aborts any active streaming generation in progress.

        Returns:
            bool: True if an active stream was signaled to cancel, False otherwise.
        """
        if self._cancel_event is not None and hasattr(self._cancel_event, "set") and not self._cancel_event.is_set():
            self._cancel_event.set()
            return True
        return False

    def abort(self) -> bool:
        """Alias for interrupt()."""
        return self.interrupt()

    @property
    def is_interrupted(self) -> bool:
        """Returns True if the active cancellation token has been triggered."""
        return self._cancel_event is not None and getattr(self._cancel_event, "is_set", lambda: False)()

    def _discover_tools(self) -> List[Callable[..., Any]]:
        """Discover and wrap available tools for Gemini automatic function calling.

        Returns:
            List of callable tool functions.
        """
        discovered: List[Callable[..., Any]] = []

        def get_system_stats() -> str:
            """Retrieves current laptop telemetry including CPU usage percentage, RAM usage, and battery status."""
            self.last_tool_steps.append("get_system_stats")
            try:
                from tools.registry import execute_tool
                result = execute_tool("get_system_stats")
                return result.to_llm_string()
            except Exception as exc:
                return f"[FAILED] Failed to get system stats: {exc}"

        discovered.append(get_system_stats)

        def open_app(app_name: str) -> str:
            """Launches an installed desktop application or utility on the host machine.

            Args:
                app_name: Name of the application to open (e.g. 'notepad', 'calculator', 'paint', 'cmd', 'explorer', 'task manager').
            """
            self.last_tool_steps.append(f"open_app({app_name})")
            try:
                from tools.registry import execute_tool
                result = execute_tool("open_app", {"app_name": app_name})
                return result.to_llm_string()
            except Exception as exc:
                return f"[FAILED] Failed to open app '{app_name}': {exc}"

        discovered.append(open_app)

        def list_directory(directory_path: str = ".") -> str:
            """Lists files and folders inside the specified directory path.

            Args:
                directory_path: Path of the directory to list (defaults to current directory '.').
            """
            self.last_tool_steps.append(f"list_directory({directory_path})")
            try:
                from tools.registry import execute_tool
                result = execute_tool("list_directory", {"directory_path": directory_path})
                return result.to_llm_string()
            except Exception as exc:
                return f"[FAILED] Failed to list directory '{directory_path}': {exc}"

        discovered.append(list_directory)

        def open_website(site: str) -> str:
            """Opens a website shortcut (e.g. 'youtube', 'google', 'gmail', 'github') or full HTTP/HTTPS URL in the default browser.

            Args:
                site: Shortcut name or full URL to open.
            """
            self.last_tool_steps.append(f"open_website({site})")
            try:
                from tools.registry import execute_tool
                result = execute_tool("open_website", {"site": site})
                return result.to_llm_string()
            except Exception as exc:
                return f"[FAILED] Failed to open website '{site}': {exc}"

        discovered.append(open_website)

        def search_web(query: str, site: str = "google") -> str:
            """Searches the web or YouTube for a query using the default web browser.

            Args:
                query: Search keyword or query string.
                site: Target search engine ('google' or 'youtube'). Defaults to 'google'.
            """
            self.last_tool_steps.append(f"search_web({query}, site={site})")
            try:
                from tools.registry import execute_tool
                result = execute_tool("search_web", {"query": query, "site": site})
                return result.to_llm_string()
            except Exception as exc:
                return f"[FAILED] Failed to search web for '{query}': {exc}"

        discovered.append(search_web)

        def read_file(file_path: str) -> str:
            """Reads the contents of a text file inside workspace/ or temp_ directories.

            Args:
                file_path: Relative or absolute path to the file to read.
            """
            self.last_tool_steps.append(f"read_file({file_path})")
            try:
                from tools.registry import execute_tool
                result = execute_tool("read_file", {"file_path": file_path})
                return result.to_llm_string()
            except Exception as exc:
                return f"[FAILED] Failed to read file '{file_path}': {exc}"

        discovered.append(read_file)

        def write_file(file_path: str, content: str) -> str:
            """Writes text content to a file inside Desktop, Documents, Downloads, workspace/, or temp_ directories.

            Args:
                file_path: Target file path to write to (e.g. 'Desktop/note.txt', 'workspace/file.txt').
                content: Text content to write into the file.
            """
            self.last_tool_steps.append(f"write_file({file_path})")
            try:
                result = self._execute_registered_tool(
                    "write_file", {"file_path": file_path, "content": content}
                )
                return result.to_llm_string()
            except Exception as exc:
                return f"[FAILED] Failed to write file '{file_path}': {exc}"

        discovered.append(write_file)

        def type_text(text: str, press_enter: bool = False) -> str:
            """Types text using keyboard automation.

            Args:
                text: The text string to type.
                press_enter: Whether to press Enter after typing.
            """
            self.last_tool_steps.append(f"type_text('{text}')")
            try:
                from tools.registry import execute_tool
                result = execute_tool("type_text", {"text": text, "press_enter": press_enter})
                return result.to_llm_string()
            except Exception as exc:
                return f"[FAILED] Failed to type text: {exc}"

        discovered.append(type_text)

        def press_keys(keys: str) -> str:
            """Simulates pressing a key or key combination (e.g. 'ctrl+s', 'enter').

            Args:
                keys: Key or key combination string.
            """
            self.last_tool_steps.append(f"press_keys('{keys}')")
            try:
                from tools.registry import execute_tool
                result = execute_tool("press_keys", {"keys": keys})
                return result.to_llm_string()
            except Exception as exc:
                return f"[FAILED] Failed to press keys '{keys}': {exc}"

        discovered.append(press_keys)

        def click(x: Optional[int] = None, y: Optional[int] = None) -> str:
            """Clicks mouse at coordinates (x, y) or at current cursor position if omitted."""
            self.last_tool_steps.append(f"click({x}, {y})")
            try:
                from tools.registry import execute_tool
                args = {}
                if x is not None:
                    args["x"] = x
                if y is not None:
                    args["y"] = y
                return execute_tool("click", args).to_llm_string()
            except Exception as exc:
                return f"[FAILED] Failed to click: {exc}"

        discovered.append(click)

        def scroll(clicks: int = 3) -> str:
            """Scrolls mouse wheel up (positive integer) or down (negative integer)."""
            self.last_tool_steps.append(f"scroll({clicks})")
            try:
                from tools.registry import execute_tool
                return execute_tool("scroll", {"clicks": clicks}).to_llm_string()
            except Exception as exc:
                return f"[FAILED] Failed to scroll: {exc}"

        discovered.append(scroll)

        def run_command(command: str, cwd: Optional[str] = None) -> str:
            """Executes a shell command (such as npm, pip, python, node, git, build commands) inside safe project directory."""
            self.last_tool_steps.append(f"run_command('{command}')")
            try:
                args = {"command": command}
                if cwd:
                    args["cwd"] = cwd
                return self._execute_registered_tool("run_command", args).to_llm_string()
            except Exception as exc:
                return f"[FAILED] Failed to run command: {exc}"

        discovered.append(run_command)

        def edit_file(file_path: str, target_text: str, replacement_text: str) -> str:
            """Edits a file by replacing target_text with replacement_text."""
            self.last_tool_steps.append(f"edit_file('{file_path}')")
            try:
                from tools.registry import execute_tool
                return execute_tool("edit_file", {
                    "file_path": file_path,
                    "target_text": target_text,
                    "replacement_text": replacement_text,
                }).to_llm_string()
            except Exception as exc:
                return f"[FAILED] Failed to edit file: {exc}"

        discovered.append(edit_file)

        def run_python(code: Optional[str] = None, file_path: Optional[str] = None) -> str:
            """Executes inline Python code or runs a Python script file."""
            self.last_tool_steps.append("run_python")
            try:
                args = {}
                if code:
                    args["code"] = code
                if file_path:
                    args["file_path"] = file_path
                return self._execute_registered_tool("run_python", args).to_llm_string()
            except Exception as exc:
                return f"[FAILED] Failed to run python: {exc}"

        discovered.append(run_python)

        def take_screenshot() -> str:
            """Captures a full screenshot of the active desktop screen."""
            self.last_tool_steps.append("take_screenshot")
            try:
                from tools.registry import execute_tool
                return execute_tool("take_screenshot").to_llm_string()
            except Exception as exc:
                return f"[FAILED] Failed to take screenshot: {exc}"

        discovered.append(take_screenshot)

        def describe_screen(question: str) -> str:
            """Analyzes the computer screen and answers a question about what is currently visible."""
            self.last_tool_steps.append(f"describe_screen('{question}')")
            try:
                from tools.registry import execute_tool
                return execute_tool("describe_screen", {"question": question}).to_llm_string()
            except Exception as exc:
                return f"[FAILED] Failed to describe screen: {exc}"

        discovered.append(describe_screen)

        def save_note(title: str, content: str) -> str:
            """Saves an important note, reminder, or piece of information into persistent memory."""
            self.last_tool_steps.append(f"save_note('{title}')")
            try:
                from tools.registry import execute_tool
                return execute_tool("save_note", {"title": title, "content": content}).to_llm_string()
            except Exception as exc:
                return f"[FAILED] Failed to save note: {exc}"

        discovered.append(save_note)

        def search_notes(query: str) -> str:
            """Searches previously saved notes and memory for a keyword or topic."""
            self.last_tool_steps.append(f"search_notes('{query}')")
            try:
                from tools.registry import execute_tool
                return execute_tool("search_notes", {"query": query}).to_llm_string()
            except Exception as exc:
                return f"[FAILED] Failed to search notes: {exc}"

        discovered.append(search_notes)

        def set_volume(level: int) -> str:
            """Sets the Windows master audio volume to a specified percentage between 0 and 100.

            Args:
                level: Volume percentage from 0 (mute) to 100 (maximum).
            """
            self.last_tool_steps.append(f"set_volume({level})")
            try:
                from tools.registry import execute_tool
                return execute_tool("set_volume", {"level": level}).to_llm_string()
            except Exception as exc:
                return f"[FAILED] Failed to set volume: {exc}"

        discovered.append(set_volume)

        def set_brightness(level: int) -> str:
            """Sets the display screen brightness to a percentage between 0 and 100.

            Args:
                level: Brightness percentage from 0 to 100.
            """
            self.last_tool_steps.append(f"set_brightness({level})")
            try:
                from tools.registry import execute_tool
                return execute_tool("set_brightness", {"level": level}).to_llm_string()
            except Exception as exc:
                return f"[FAILED] Failed to set brightness: {exc}"

        discovered.append(set_brightness)

        def lock_screen() -> str:
            """Immediately locks the Windows workstation screen."""
            self.last_tool_steps.append("lock_screen")
            try:
                from tools.registry import execute_tool
                return execute_tool("lock_screen").to_llm_string()
            except Exception as exc:
                return f"[FAILED] Failed to lock screen: {exc}"

        discovered.append(lock_screen)

        def battery() -> str:
            """Retrieves battery charge percentage, charging status, and remaining power time."""
            self.last_tool_steps.append("battery")
            try:
                from tools.registry import execute_tool
                return execute_tool("battery").to_llm_string()
            except Exception as exc:
                return f"[FAILED] Failed to inspect battery: {exc}"

        discovered.append(battery)

        def list_windows(include_empty: bool = False) -> str:
            """Lists all visible and active application windows on the desktop.

            Args:
                include_empty: Whether to include windows without titles.
            """
            self.last_tool_steps.append("list_windows")
            try:
                from tools.registry import execute_tool
                return execute_tool("list_windows", {"include_empty": include_empty}).to_llm_string()
            except Exception as exc:
                return f"[FAILED] Failed to list windows: {exc}"

        discovered.append(list_windows)

        def focus_window(title: str) -> str:
            """Brings an open application window matching the title to the foreground.

            Args:
                title: Window title or substring to search for.
            """
            self.last_tool_steps.append(f"focus_window('{title}')")
            try:
                from tools.registry import execute_tool
                return execute_tool("focus_window", {"title": title}).to_llm_string()
            except Exception as exc:
                return f"[FAILED] Failed to focus window: {exc}"

        discovered.append(focus_window)

        def minimize_window(title: str) -> str:
            """Minimizes an open application window matching the given title substring.

            Args:
                title: Window title or substring to search for.
            """
            self.last_tool_steps.append(f"minimize_window('{title}')")
            try:
                from tools.registry import execute_tool
                return execute_tool("minimize_window", {"title": title}).to_llm_string()
            except Exception as exc:
                return f"[FAILED] Failed to minimize window: {exc}"

        discovered.append(minimize_window)

        def clipboard_read() -> str:
            """Reads and returns the current text content stored in the system clipboard."""
            self.last_tool_steps.append("clipboard_read")
            try:
                from tools.registry import execute_tool
                return execute_tool("clipboard_read").to_llm_string()
            except Exception as exc:
                return f"[FAILED] Failed to read clipboard: {exc}"

        discovered.append(clipboard_read)

        def clipboard_write(text: str) -> str:
            """Copies the given text into the system clipboard.

            Args:
                text: Text string to copy to the clipboard.
            """
            self.last_tool_steps.append(f"clipboard_write('{text}')")
            try:
                from tools.registry import execute_tool
                return execute_tool("clipboard_write", {"text": text}).to_llm_string()
            except Exception as exc:
                return f"[FAILED] Failed to write clipboard: {exc}"

        discovered.append(clipboard_write)

        def explain_screen_error(question: Optional[str] = None) -> str:
            """Analyzes the screen specifically for error messages, stack traces, or dialogs."""
            self.last_tool_steps.append("explain_screen_error")
            try:
                from tools.registry import execute_tool
                args = {"question": question} if question else {}
                return execute_tool("explain_screen_error", args).to_llm_string()
            except Exception as exc:
                return f"[FAILED] Failed to explain screen error: {exc}"

        discovered.append(explain_screen_error)

        def click_element(description: str) -> str:
            """Visually locates a UI element on screen by natural language description and clicks it.

            Args:
                description: Visual description of the target UI button, icon, or text to click.
            """
            self.last_tool_steps.append(f"click_element('{description}')")
            try:
                from tools.registry import execute_tool
                return execute_tool("click_element", {"description": description}).to_llm_string()
            except Exception as exc:
                return f"[FAILED] Failed to click element: {exc}"

        discovered.append(click_element)

        def open_file(file_path: str) -> str:
            """Opens a document, image, or file using its default associated desktop application.

            Args:
                file_path: Path to the file to open (e.g. 'workspace/report.pdf'). Must be inside workspace/ or allowed safe directories.
            """
            self.last_tool_steps.append(f"open_file('{file_path}')")
            try:
                from tools.registry import execute_tool
                return execute_tool("open_file", {"file_path": file_path}).to_llm_string()
            except Exception as exc:
                return f"[FAILED] Failed to open file '{file_path}': {exc}"

        discovered.append(open_file)

        def open_settings_page(page: str) -> str:
            """Opens a specific Windows Settings page (e.g. 'display', 'sound', 'bluetooth', 'wifi', 'network', 'battery', 'apps').

            Args:
                page: Name of the settings page to open.
            """
            self.last_tool_steps.append(f"open_settings_page('{page}')")
            try:
                from tools.registry import execute_tool
                return execute_tool("open_settings_page", {"page": page}).to_llm_string()
            except Exception as exc:
                return f"[FAILED] Failed to open settings page '{page}': {exc}"

        discovered.append(open_settings_page)

        def do_on_screen(goal: str, max_steps: int = 5) -> str:
            """Autonomously performs a multi-step task on the desktop screen using the Look-Decide-Act agent loop.

            Args:
                goal: The goal or task to achieve on screen (e.g. 'open the File menu in Notepad', 'scroll down').
                max_steps: Maximum number of visual action steps to attempt (default: 5).
            """
            self.last_tool_steps.append(f"do_on_screen('{goal}')")
            try:
                from tools.registry import execute_tool
                return execute_tool("do_on_screen", {"goal": goal, "max_steps": max_steps}).to_llm_string()
            except Exception as exc:
                return f"[FAILED] Failed to execute task on screen: {exc}"

        discovered.append(do_on_screen)

        def explain_code_on_screen(task: str = "explain", active_window: bool = True) -> str:
            """Analyzes source code or terminal output visible on the screen, providing explanations or bug fixes.

            Args:
                task: Action type: 'explain' to explain the code, or 'fix' to diagnose and provide corrected code.
                active_window: Whether to crop capture to the active editor window (default: True).
            """
            self.last_tool_steps.append(f"explain_code_on_screen(task='{task}')")
            try:
                from tools.registry import execute_tool
                return execute_tool("explain_code_on_screen", {"task": task, "active_window": active_window}).to_llm_string()
            except Exception as exc:
                return f"[FAILED] Failed to explain code on screen: {exc}"

        discovered.append(explain_code_on_screen)

        def create_pdf(
            title: str,
            sections: List[Dict[str, Any]],
            theme: str = "clean_light",
            auto_open: bool = True,
            out_dir: str = "workspace",
            **kwargs: Any,
        ) -> str:
            """Generates a professionally styled PDF document with cover page, bento grids, and typography.

            Args:
                title: Title of the PDF document.
                sections: List of sections, each a dict with 'heading' and optional 'text', 'bullets', 'metrics', or 'table'.
                theme: Visual theme: 'clean_light', 'dark_pro', or 'colourful'.
                auto_open: Whether to automatically launch the generated PDF in the default viewer.
                out_dir: Output directory (e.g. 'Desktop' to save directly to user's desktop, or 'workspace').
            """
            self.last_tool_steps.append(f"create_pdf('{title}')")
            try:
                from tools.registry import execute_tool
                args = {
                    "title": title,
                    "sections": sections,
                    "theme": theme,
                    "auto_open": auto_open,
                    "out_dir": out_dir,
                }
                args.update(kwargs)
                return execute_tool("create_pdf", args).to_llm_string()
            except Exception as exc:
                return f"[FAILED] Failed to create PDF '{title}': {exc}"

        discovered.append(create_pdf)

        def create_docx(
            title: str,
            sections: List[Dict[str, Any]],
            theme: str = "clean_light",
            auto_open: bool = True,
            out_dir: str = "workspace",
            **kwargs: Any,
        ) -> str:
            """Generates an executive Word document (.docx) with structured tables, callouts, and typography.

            Args:
                title: Title of the Word document.
                sections: List of sections with 'heading' and optional 'text', 'bullets', 'metrics', or 'table'.
                theme: Visual theme: 'clean_light', 'dark_pro', or 'colourful'.
                auto_open: Whether to automatically open the generated document in Microsoft Word.
                out_dir: Output directory (e.g. 'Desktop' to save directly to user's desktop, or 'workspace').
            """
            self.last_tool_steps.append(f"create_docx('{title}')")
            try:
                from tools.registry import execute_tool
                args = {
                    "title": title,
                    "sections": sections,
                    "theme": theme,
                    "auto_open": auto_open,
                    "out_dir": out_dir,
                }
                args.update(kwargs)
                return execute_tool("create_docx", args).to_llm_string()
            except Exception as exc:
                return f"[FAILED] Failed to create Word document '{title}': {exc}"

        discovered.append(create_docx)

        def create_pptx(
            title: str,
            sections: List[Dict[str, Any]],
            theme: str = "clean_light",
            auto_open: bool = True,
            out_dir: str = "workspace",
            **kwargs: Any,
        ) -> str:
            """Generates a high-impact PowerPoint presentation deck (.pptx) with modern layout and slides.

            Args:
                title: Title of the presentation.
                sections: List of slide sections with 'heading' and optional 'text', 'bullets', 'metrics', or 'table'.
                theme: Visual theme: 'clean_light', 'dark_pro', or 'colourful'.
                auto_open: Whether to automatically open the generated deck in PowerPoint.
                out_dir: Output directory (e.g. 'Desktop' to save directly to user's desktop, or 'workspace').
            """
            self.last_tool_steps.append(f"create_pptx('{title}')")
            try:
                from tools.registry import execute_tool
                args = {
                    "title": title,
                    "sections": sections,
                    "theme": theme,
                    "auto_open": auto_open,
                    "out_dir": out_dir,
                }
                args.update(kwargs)
                return execute_tool("create_pptx", args).to_llm_string()
            except Exception as exc:
                return f"[FAILED] Failed to create PowerPoint presentation '{title}': {exc}"

        discovered.append(create_pptx)

        def create_document(
            topic: str = "",
            kind: str = "pdf",
            language: str = "en",
            theme: str = "clean_light",
            auto_open: bool = True,
            out_dir: str = "workspace",
            **kwargs: Any,
        ) -> str:
            """Generates a complete, multi-section document (PDF, DOCX, PPTX, or Web) from a high-level topic or prompt.

            Args:
                topic: Topic or theme of the document (e.g. 'Core Java Important Concepts', 'AI in Education').
                kind: Document format to generate: 'pdf', 'docx', 'pptx', or 'web'.
                language: Language code: 'en' (English), 'hi' (Hindi), or 'mr' (Marathi).
                theme: Visual theme: 'clean_light', 'dark_pro', or 'colourful'.
                auto_open: Whether to automatically open the document upon creation.
                out_dir: Output directory (e.g. 'Desktop' to save directly to user's desktop, or 'workspace').
            """
            clean_t = (topic or kwargs.get("title") or kwargs.get("prompt") or "").strip()
            self.last_tool_steps.append(f"create_document('{clean_t}', kind='{kind}')")
            try:
                from tools.registry import execute_tool
                args = {
                    "topic": clean_t,
                    "kind": kind,
                    "language": language,
                    "theme": theme,
                    "auto_open": auto_open,
                    "out_dir": out_dir,
                }
                args.update(kwargs)
                return execute_tool("create_document", args).to_llm_string()
            except Exception as exc:
                return f"[FAILED] Failed to create document for '{clean_t}': {exc}"

        discovered.append(create_document)

        def send_telegram(text: str, file_path: str = "") -> str:
            """Sends an instant message notification or status alert to the owner's phone via Telegram.

            Args:
                text: The message content to send to the owner.
            """
            self.last_tool_steps.append("send_telegram")
            try:
                args: Dict[str, Any] = {"text": text}
                if file_path:
                    args["file_path"] = file_path
                return self._execute_registered_tool("send_telegram", args).to_llm_string()
            except Exception as exc:
                return f"[FAILED] Failed to send Telegram message: {exc}"

        discovered.append(send_telegram)

        # Keep Gemini and Groq capabilities aligned with the registry while
        # preserving each tool's real JSON schema for both model providers.
        try:
            from tools.registry import (
                auto_load_module_tools,
                get_registered_tools,
                get_tools_schema,
            )

            auto_load_module_tools()
            schema_by_name = {
                schema["name"]: schema for schema in get_tools_schema()
            }

            for registered_tool in get_registered_tools():
                if registered_tool.name in {tool.__name__ for tool in discovered}:
                    continue

                def invoke_registered_tool(
                    _tool_name: str = registered_tool.name,
                    **kwargs: Any,
                ) -> str:
                    """Invoke a registered JARVIS capability by its canonical name."""
                    self.last_tool_steps.append(f"{_tool_name}({kwargs})")
                    try:
                        return self._execute_registered_tool(
                            _tool_name, kwargs
                        ).to_llm_string()
                    except Exception as exc:
                        return f"[FAILED] Failed to execute {_tool_name}: {exc}"

                invoke_registered_tool.__name__ = registered_tool.name
                tool_schema = schema_by_name.get(registered_tool.name, {})
                properties = tool_schema.get("parameters", {}).get("properties", {})
                required = set(tool_schema.get("parameters", {}).get("required", []))
                parameter_docs = []
                schema_parameters: List[inspect.Parameter] = []
                python_types = {
                    "string": str,
                    "integer": int,
                    "number": float,
                    "boolean": bool,
                    "array": List[Any],
                    "object": Dict[str, Any],
                }
                for parameter_name, parameter_schema in properties.items():
                    description = parameter_schema.get("description", "").strip()
                    if description:
                        parameter_docs.append(f"{parameter_name}: {description}")
                    parameter_type = python_types.get(
                        parameter_schema.get("type", "string"), Any
                    )
                    default_value = (
                        inspect.Parameter.empty
                        if parameter_name in required
                        else parameter_schema.get("default", None)
                    )
                    schema_parameters.append(
                        inspect.Parameter(
                            parameter_name,
                            inspect.Parameter.KEYWORD_ONLY,
                            default=default_value,
                            annotation=parameter_type,
                        )
                    )
                invoke_registered_tool.__signature__ = inspect.Signature(
                    schema_parameters
                )
                invoke_registered_tool.__doc__ = registered_tool.description
                if parameter_docs:
                    invoke_registered_tool.__doc__ += "\nParameters:\n" + "\n".join(
                        parameter_docs
                    )
                discovered.append(invoke_registered_tool)
        except Exception as exc:
            print(f"[WARN] Failed to expose all registered tools to Gemini: {exc}", file=sys.stderr)

        return discovered

    def _init_chat_session(self) -> None:
        """Initialize or reset the Gemini multi-turn chat session."""
        if self.client is None:
            self.chat_session = None
            return

        config_kwargs: Dict[str, Any] = {
            "system_instruction": self.system_prompt,
        }
        if self.tools:
            config_kwargs["tools"] = self.tools

        config = types.GenerateContentConfig(**config_kwargs)
        try:
            self.chat_session = self.client.chats.create(
                model=self.model_name,
                config=config,
            )
        except errors.APIError as err:
            err_str = str(err).lower()
            if "gemini-2.5-flash" in self.model_name and ("no longer available" in err_str or "not found" in err_str):
                self.model_name = "gemini-3.8-flash"
                self.chat_session = self.client.chats.create(
                    model=self.model_name,
                    config=config,
                )
            else:
                raise

    def chat_stream(
        self,
        user_message: str,
        mode: str = "normal",
        cancel_event: Optional[Any] = None,
    ) -> Generator[str, None, None]:
        """Process a user message and stream the assistant response tokens.

        Executes autonomous tool calls transparently, with exponential backoff
        retry on rate limits (429/503), automatic dual-engine failover, and
        real-time cancellation support (<100ms response).

        Args:
            user_message: Spoken or typed user input string.
            mode: Operating mode ('normal', 'silent', 'attentive', 'combat').
            cancel_event: Optional cancellation token (threading.Event or asyncio.Event)
                to abort token generation mid-stream.

        Yields:
            Response text tokens/chunks in real time.
        """
        if cancel_event is not None:
            self._cancel_event = cancel_event
        else:
            self._cancel_event = threading.Event()

        if self.is_interrupted:
            return

        cleaned_input: str = user_message.strip()
        if not cleaned_input:
            yield "I am listening. How can I assist you?"
            return

        self.last_tool_steps = []

        confirmation_match = re.fullmatch(
            r"CONFIRM\s+([A-F0-9]{16})", cleaned_input, flags=re.IGNORECASE
        )
        if confirmation_match:
            from core.confirm import execute_confirmation

            confirmation = execute_confirmation(confirmation_match.group(1))
            result = confirmation.get("result")
            if confirmation.get("success") and getattr(result, "success", True):
                response_text = getattr(result, "message", confirmation["message"])
            else:
                response_text = confirmation.get("message", "Confirmation could not be completed.")
            self.history.extend(
                [
                    {"role": "user", "content": cleaned_input},
                    {"role": "model", "content": response_text},
                ]
            )
            self.compact_history()
            yield response_text
            return

        # Handle verbal mode switching
        lower_input = cleaned_input.lower()
        if any(k in lower_input for k in ("engage combat mode", "combat mode", "switch to combat mode", "enter combat mode")):
            yield "Combat protocol engaged. All neural nodes running at maximum clock. Directives will be executed with extreme speed and precision."
            return
        if any(k in lower_input for k in ("exit combat mode", "disengage combat", "disable combat mode")):
            yield "Combat protocol disengaged. Returning to standard standby."
            return
        if any(k in lower_input for k in ("go to silent mode", "switch to silent mode", "silent mode", "standby mode")):
            yield "Silent mode engaged. Awaiting wake word directive."
            return
        if any(k in lower_input for k in ("go to attentive mode", "attentive mode", "always listen", "continuous mode", "listen continuously")):
            yield "Attentive mode activated. Always listening."
            return

        # Keep explicit multi-action desktop requests useful during cloud outages.
        local_compound_response = self._execute_compound_local_request(cleaned_input)
        if local_compound_response is not None:
            yield local_compound_response
            return

        local_document_response = self._execute_local_document_request(cleaned_input)
        if local_document_response is not None:
            yield local_document_response
            return

        # Fast Sub-Millisecond Contextual Shortcuts (Zero Cloud Latency)
        stripped_lower = lower_input.strip("?.!")
        time_triggers = (
            "what time is it", "current time", "what is the time", "tell me the time",
            "time please", "what date", "today's date", "which day is it", "what is the date",
            "kiti vajle", "vel kay zali", "samay kya hai", "kitne baje", "aaj ki tarikh"
        )
        words = set(stripped_lower.split())
        if any(t in stripped_lower for t in time_triggers) or "time" in words or "date" in words:
            now = datetime.datetime.now()
            t = now.strftime("%I:%M %p")
            d = now.strftime("%A, %B %d, %Y")
            if not self.is_interrupted:
                yield f"Today's date is {d}, and the current time is {t}."
            return

        system_stat_triggers = (
            "system info", "system stats", "system status", "report system status",
            "cpu usage", "ram usage", "battery", "telemetry",
            "hardware status", "status report"
        )
        cleaned_cmd = stripped_lower.removeprefix("jarvis").strip(", ")
        if cleaned_cmd in system_stat_triggers:
            if self.is_interrupted:
                return
            try:
                from tools.system_tools import GetSystemStatsTool
                stats = GetSystemStatsTool().run()
                if stats.success and stats.data:
                    d = stats.data
                    cpu = d.get("cpu_percent") if d.get("cpu_percent") is not None else d.get("cpu_usage_percent", 0)
                    ram = d.get("ram_used_pct") if d.get("ram_used_pct") is not None else d.get("ram_usage_percent", 0)
                    battery_str = d.get("battery")
                    if not self.is_interrupted:
                        if battery_str:
                            yield f"System Telemetry: CPU load is {cpu}%, RAM usage is {ram}%, Battery at {battery_str}. All systems nominal."
                            return
                        batt_pct = d.get("battery_pct", 100)
                        yield f"System Telemetry: CPU load is {cpu}%, RAM usage is {ram}%, Battery at {batt_pct}%. All systems nominal."
                    return
            except Exception:
                pass

        # Fast Weather Shortcut (avoid slow DuckDuckGo scraping for location-agnostic weather)
        weather_triggers = ("what is the weather", "what's the weather", "how is the weather", "weather today", "current weather", "aaj mausam kaisa hai", "havaman kase ahe")
        if any(w in stripped_lower for w in weather_triggers) and not any(city in stripped_lower for city in (" in ", " at ", " for ")):
            if not self.is_interrupted:
                yield "Please specify your city or region, and I will check the live forecast for you."
            return

        if self.is_interrupted:
            return

        # High-speed Combat Mode or Groq provider
        if (mode == "combat" or self.llm_provider == "groq") and self.groq_api_key:
            yield from self._chat_stream_with_groq(
                cleaned_input,
                is_combat=(mode == "combat"),
                cancel_event=self._cancel_event,
            )
            return

        yield from self._chat_stream_with_gemini(cleaned_input, cancel_event=self._cancel_event)

    def stream_chat(
        self,
        user_message: str,
        mode: str = "normal",
        cancel_event: Optional[Any] = None,
    ) -> Generator[str, None, None]:
        """Stream assistant response tokens with full cancellation token support.

        Conforms to Day 8 Full-Duplex Voice interface specification.
        """
        yield from self.chat_stream(user_message, mode=mode, cancel_event=cancel_event)

    def chat(
        self,
        user_message: str,
        mode: str = "normal",
        cancel_event: Optional[Any] = None,
    ) -> str:
        """Process a user message and return the assistant response.

        Maintains full multi-turn conversational history and executes any
        invoked tool calls transparently. Supports stream cancellation.

        Args:
            user_message: Spoken or typed user input string.
            mode: Operating mode ('normal', 'silent', 'attentive', 'combat').
            cancel_event: Optional cancellation token to abort generation.

        Returns:
            The assistant's natural language response.
        """
        return "".join(self.chat_stream(user_message, mode=mode, cancel_event=cancel_event))

    def _chat_stream_with_groq(
        self,
        user_message: str,
        is_combat: bool = False,
        is_failover: bool = False,
        cancel_event: Optional[Any] = None,
    ) -> Generator[str, None, None]:
        """Execute chat directive using Groq Cloud API with real-time token streaming.

        Handles tool execution, exponential backoff on 429/503, cancellation aborts,
        and automatic failover to Gemini.
        """
        try:
            import json
            from groq import Groq

            if cancel_event and cancel_event.is_set():
                return

            client = Groq(api_key=self.groq_api_key)
            combat_sys = (
                "COMBAT PROTOCOL ENGAGED. Tactical maximum speed mode. "
                "CRITICAL: Keep your response under 10 words in a single crisp sentence. Directives only. Zero filler.\n\n"
            ) if is_combat else ""
            messages: List[Dict[str, Any]] = [
                {"role": "system", "content": combat_sys + self.system_prompt}
            ]
            for turn in self.history[-6:]:
                role = "assistant" if turn.get("role") == "model" else "user"
                messages.append({"role": role, "content": turn.get("content", "")})
            messages.append({"role": "user", "content": user_message})

            tools_param = None
            if self.enable_tools:
                try:
                    from tools.registry import get_tools_schema
                    schemas = get_tools_schema()
                    tools_param = _groq_tool_definitions(schemas)
                except Exception as exc:
                    print(f"[WARN] Failed to load tool schemas for Groq: {exc}", file=sys.stderr)

            extra_params: Dict[str, Any] = {}
            if tools_param:
                extra_params["tools"] = tools_param
                extra_params["tool_choice"] = "auto"

            # Only attempt models that support tool schemas if tools are requested
            candidate_models = [self.groq_model] if tools_param else [self.groq_model, "openai/gpt-oss-120b", "openai/gpt-oss-20b"]
            used_model = self.groq_model
            stream = None
            backoff_delays = [0.5, 1.0]
            last_exception = None

            for attempt in range(len(backoff_delays) + 1):
                if cancel_event and cancel_event.is_set():
                    return
                for m in candidate_models:
                    if cancel_event and cancel_event.is_set():
                        return
                    try:
                        stream = client.chat.completions.create(
                            model=m,
                            messages=messages,
                            temperature=0.2 if is_combat else 0.3,
                            max_tokens=256 if is_combat else 1024,
                            stream=True,
                            **extra_params,
                        )
                        used_model = m
                        break
                    except Exception as m_err:
                        last_exception = m_err
                        err_str = str(m_err).lower()

                        if "429" in err_str or "rate" in err_str or "503" in err_str or "limit" in err_str or "quota" in err_str:
                            continue
                        raise

                if stream is not None:
                    break

                if cancel_event and cancel_event.is_set():
                    return

                if attempt < len(backoff_delays):
                    delay = backoff_delays[attempt]
                    print(f"[*] Groq 429/503 encountered. Retrying in {delay}s...", file=sys.stderr)
                    if cancel_event and hasattr(cancel_event, "wait"):
                        cancel_event.wait(timeout=delay)
                    else:
                        time.sleep(delay)
                    if cancel_event and cancel_event.is_set():
                        return

            if stream is None:
                if cancel_event and cancel_event.is_set():
                    return
                if not is_failover:
                    print(f"[!] Groq rate limit reached ({last_exception}). Failing over to Gemini...", file=sys.stderr)
                    yield from self._chat_stream_with_gemini(user_message, is_failover=True, cancel_event=cancel_event)
                    return
                yield "All neural computing nodes are temporarily rate-limited, sir. Please retry shortly."
                return

            tool_calls_map: Dict[int, Dict[str, Any]] = {}
            has_tool_calls: bool = False
            first_turn_chunks: List[str] = []

            for chunk in stream:
                if cancel_event and cancel_event.is_set():
                    if hasattr(stream, "close"):
                        try:
                            stream.close()
                        except Exception:
                            pass
                    return
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if getattr(delta, "tool_calls", None) and delta.tool_calls:
                    has_tool_calls = True
                    for tc in delta.tool_calls:
                        idx = tc.index
                        if idx not in tool_calls_map:
                            tool_calls_map[idx] = {
                                "id": tc.id or "",
                                "name": "",
                                "arguments": "",
                            }
                        if tc.id:
                            tool_calls_map[idx]["id"] = tc.id
                        if tc.function and tc.function.name:
                            tool_calls_map[idx]["name"] += tc.function.name
                        if tc.function and tc.function.arguments:
                            tool_calls_map[idx]["arguments"] += tc.function.arguments
                elif not has_tool_calls and getattr(delta, "content", None):
                    if delta.content:
                        first_turn_chunks.append(delta.content)
                        yield delta.content

            if cancel_event and cancel_event.is_set():
                return

            if has_tool_calls:
                from tools.registry import execute_tool
                final_text = ""
                tool_rounds = 0
                while has_tool_calls and tool_rounds < 5:
                    tool_rounds += 1
                    assistant_tool_calls = []
                    for idx in sorted(tool_calls_map.keys()):
                        t_info = tool_calls_map[idx]
                        assistant_tool_calls.append({
                            "id": t_info["id"] or f"call_{idx}",
                            "type": "function",
                            "function": {
                                "name": t_info["name"],
                                "arguments": t_info["arguments"],
                            },
                        })
                    messages.append({"role": "assistant", "tool_calls": assistant_tool_calls})

                    for tc in assistant_tool_calls:
                        if cancel_event and cancel_event.is_set():
                            return
                        fn_name = tc["function"]["name"]
                        raw_args = tc["function"]["arguments"]
                        try:
                            fn_args = json.loads(raw_args) if raw_args else {}
                        except (TypeError, ValueError):
                            fn_args = {}
                        self.last_tool_steps.append(f"{fn_name}({fn_args})")
                        tool_res = self._execute_registered_tool(fn_name, fn_args)
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "name": fn_name,
                            "content": tool_res.to_llm_string(),
                        })

                    follow_up_stream = None
                    follow_up_error = None
                    for attempt in range(len(backoff_delays) + 1):
                        if cancel_event and cancel_event.is_set():
                            return
                        try:
                            follow_up_stream = client.chat.completions.create(
                                model=used_model,
                                messages=messages,
                                max_tokens=256 if is_combat else 1024,
                                temperature=0.2,
                                stream=True,
                                **extra_params,
                            )
                            break
                        except Exception as fu_err:
                            follow_up_error = fu_err
                            err_text = str(fu_err).lower()
                            if any(code in err_text for code in ("429", "rate", "503", "limit", "quota")) and attempt < len(backoff_delays):
                                delay = backoff_delays[attempt]
                                if cancel_event and hasattr(cancel_event, "wait"):
                                    cancel_event.wait(timeout=delay)
                                else:
                                    time.sleep(delay)
                                continue
                            break
                    if follow_up_stream is None:
                        raise RuntimeError(f"Groq tool follow-up request failed: {follow_up_error}")

                    next_tool_calls: Dict[int, Dict[str, Any]] = {}
                    follow_up_chunks: List[str] = []
                    has_tool_calls = False
                    for chunk in follow_up_stream:
                        if cancel_event and cancel_event.is_set():
                            if hasattr(follow_up_stream, "close"):
                                try:
                                    follow_up_stream.close()
                                except Exception:
                                    pass
                            return
                        if not chunk.choices:
                            continue
                        delta = chunk.choices[0].delta
                        if getattr(delta, "tool_calls", None):
                            has_tool_calls = True
                            for tc in delta.tool_calls:
                                idx = tc.index
                                if idx not in next_tool_calls:
                                    next_tool_calls[idx] = {"id": tc.id or "", "name": "", "arguments": ""}
                                if tc.id:
                                    next_tool_calls[idx]["id"] = tc.id
                                if tc.function and tc.function.name:
                                    next_tool_calls[idx]["name"] += tc.function.name
                                if tc.function and tc.function.arguments:
                                    next_tool_calls[idx]["arguments"] += tc.function.arguments
                        elif getattr(delta, "content", None):
                            follow_up_chunks.append(delta.content)
                    if has_tool_calls:
                        tool_calls_map = next_tool_calls
                    else:
                        final_text = "".join(follow_up_chunks).strip()

                if has_tool_calls:
                    final_text = "I completed five action steps, but the request needs more. Please tell me what to do next."
                elif not final_text:
                    final_text = "Directive executed successfully, sir."
                for line in (line.strip() for line in final_text.splitlines()):
                    if line:
                        yield line
                        break
                final_text = next((line.strip() for line in final_text.splitlines() if line.strip()), final_text)
            else:
                final_text = "".join(first_turn_chunks).strip()

            if not (cancel_event and cancel_event.is_set()):
                self.history.append({"role": "user", "content": user_message})
                self.history.append({"role": "model", "content": final_text})
                self.compact_history()

        except Exception as exc:
            if cancel_event and cancel_event.is_set():
                return
            if is_failover:
                print(f"[!] Groq failover execution exception: {exc}", file=sys.stderr)
                yield "The backup reasoning service is unavailable, sir. Please retry shortly."
                return
            else:
                print(f"[!] Groq execution exception: {exc}. Failing over to Gemini...", file=sys.stderr)
                if hasattr(self, "chat_session") and self.chat_session:
                    try:
                        yield from self._chat_stream_with_gemini(user_message, is_failover=True, cancel_event=cancel_event)
                        return
                    except Exception as gemini_err:
                        print(f"[!] Gemini failover also encountered an error: {gemini_err}", file=sys.stderr)
            print(f"[!] Groq execution failed: {exc}", file=sys.stderr)
            yield f"I was unable to execute your directive, sir: {exc}"

    def _chat_with_groq(
        self,
        user_message: str,
        is_combat: bool = False,
        cancel_event: Optional[Any] = None,
    ) -> str:
        """Execute chat directive using Groq Cloud API as high-speed fallback or primary engine.

        Maintains conversation history buffer and executes tools autonomously.
        """
        return "".join(self._chat_stream_with_groq(user_message, is_combat=is_combat, cancel_event=cancel_event))

    def _chat_stream_with_gemini(
        self,
        user_message: str,
        is_failover: bool = False,
        cancel_event: Optional[Any] = None,
    ) -> Generator[str, None, None]:
        """Execute chat directive using Gemini API with real-time streaming, backoff, and AFC."""
        backoff_delays = [0.5, 1.0]
        cleaned_input = user_message.strip()

        for attempt in range(len(backoff_delays) + 1):
            if cancel_event and cancel_event.is_set():
                return
            try:
                chunks: List[str] = []
                if hasattr(self.chat_session, "send_message_stream"):
                    try:
                        response_stream = self.chat_session.send_message_stream(cleaned_input)
                        for chunk in response_stream:
                            if cancel_event and cancel_event.is_set():
                                return
                            chunk_text = ""
                            if hasattr(chunk, "candidates") and chunk.candidates:
                                for cand in chunk.candidates:
                                    if hasattr(cand, "content") and cand.content and hasattr(cand.content, "parts"):
                                        for p in cand.content.parts:
                                            if hasattr(p, "text") and p.text:
                                                chunk_text += p.text
                            elif hasattr(chunk, "text") and chunk.text:
                                chunk_text = chunk.text
                            if chunk_text:
                                chunks.append(chunk_text)
                                yield chunk_text
                    except (TypeError, AttributeError):
                        chunks = []

                if cancel_event and cancel_event.is_set():
                    return

                if chunks:
                    response_text = "".join(chunks).strip()
                    self.history.append({"role": "user", "content": cleaned_input})
                    self.history.append({"role": "model", "content": response_text})
                    self.compact_history()
                    return

                # Fallback to send_message if streaming produced no chunks or send_message was mocked
                if cancel_event and cancel_event.is_set():
                    return
                response = self.chat_session.send_message(cleaned_input)
                if cancel_event and cancel_event.is_set():
                    return
                response_text = response.text.strip() if hasattr(response, "text") and response.text else ""
                self.history.append({"role": "user", "content": cleaned_input})
                self.history.append({"role": "model", "content": response_text})
                self.compact_history()
                if response_text:
                    yield response_text
                return

            except errors.APIError as err:
                if cancel_event and cancel_event.is_set():
                    return
                err_str = str(err).lower()
                if "gemini-2.5-flash" in self.model_name and ("no longer available" in err_str or "not found" in err_str):
                    self.model_name = "gemini-3.8-flash"
                    self._init_chat_session()
                    continue

                if any(k in err_str for k in ("quota", "rate", "429", "resource_exhausted", "503", "high demand", "unavailable")):
                    if attempt < len(backoff_delays):
                        delay = backoff_delays[attempt]
                        print(f"[*] Gemini limit encountered ({err.message}). Retrying in {delay}s...", file=sys.stderr)
                        if cancel_event and hasattr(cancel_event, "wait"):
                            cancel_event.wait(timeout=delay)
                        else:
                            time.sleep(delay)
                        continue

                    # Exhausted Gemini retries; failover to Groq if key exists and not already failed over
                    if self.groq_api_key and not is_failover:
                        print(
                            f"[*] Gemini limit encountered ({err.message}). Seamlessly failing over to Groq ({self.groq_model})...",
                            file=sys.stderr,
                        )
                        yield from self._chat_stream_with_groq(cleaned_input, is_failover=True, cancel_event=cancel_event)
                        return

                    if is_failover:
                        yield "The backup reasoning service is rate-limited, sir. Please retry shortly."
                    else:
                        yield "Gemini API quota limit reached, sir. Please retry in a few moments."
                    return

                if self.groq_api_key and not is_failover:
                    print(
                        f"[!] Gemini API error ({err.message}). Failing over to Groq ({self.groq_model})...",
                        file=sys.stderr,
                    )
                    yield from self._chat_stream_with_groq(
                        cleaned_input, is_failover=True, cancel_event=cancel_event
                    )
                    return

                print(f"[!] Gemini API error occurred: {err.message}", file=sys.stderr)
                yield "I encountered an error communicating with my neural core."
                return

            except Exception as err:
                if cancel_event and cancel_event.is_set():
                    return
                print(f"[!] Unexpected error during Gemini streaming: {err}", file=sys.stderr)
                if self.groq_api_key and not is_failover:
                    yield from self._chat_stream_with_groq(
                        cleaned_input, is_failover=True, cancel_event=cancel_event
                    )
                    return
                yield "I encountered an internal error processing your request."
                return

    def process_input(self, text: str) -> str:
        """Unified interface contract for Voice engine (Aryan) and UI (Rohit).

        Conforms to ARCHITECTURE.md Section 4.1.

        Args:
            text: Input text string from speech-to-text or UI HUD.

        Returns:
            Assistant response text for speech synthesis or UI display.
        """
        return self.chat(text)

    def compact_history(self, max_entries: Optional[int] = None) -> int:
        """Compact conversation history buffer using a sliding window.

        Retains the most recent N message entries to prevent context overflow
        and preserve sub-second response latency.

        Args:
            max_entries: Maximum number of message dictionaries to retain.
                Defaults to self.max_history_entries.

        Returns:
            int: Number of older turns pruned from history buffer.
        """
        limit = max_entries if max_entries is not None else self.max_history_entries
        if len(self.history) <= limit:
            return 0
        pruned = len(self.history) - limit
        self.history = self.history[-limit:]
        return pruned

    def reset(self) -> None:
        """Clear conversation history and reinitialize the chat session."""
        self.history.clear()
        self.last_tool_steps.clear()
        self._cancel_event = None
        self._init_chat_session()

    def get_history(self) -> List[Dict[str, str]]:
        """Retrieve copy of multi-turn conversation history buffer.

        Returns:
            List of message dictionaries with 'role' and 'content' keys.
        """
        return list(self.history)


def run_interactive_cli() -> None:
    """Launch an interactive terminal REPL session with Jarvis."""
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    print("=" * 68)
    print("       PROJECT JARVIS - TACTICAL TERMINAL COMMAND CENTER")
    print(" Type a command or question. Enter '/help' for slash commands.")
    print(" Type 'exit' or 'quit' to terminate session.")
    print("=" * 68)

    try:
        brain: JarvisBrain = JarvisBrain()
    except ValueError as err:
        print(f"\n[!] Initialization Error: {err}\n", file=sys.stderr)
        sys.exit(1)
    except Exception as err:
        print(f"\n[!] Unexpected Error: {err}\n", file=sys.stderr)
        sys.exit(1)

    current_mode: str = "normal"
    print(f"[*] Jarvis Core online (mode: {current_mode.upper()}). Ready for directives.\n")

    while True:
        try:
            prompt_str = f"Jay [{current_mode}] > " if current_mode != "normal" else "Jay > "
            user_input: str = input(prompt_str).strip()
            if not user_input:
                continue

            lowered = user_input.lower()
            if lowered in ("exit", "quit", "q", "/exit", "/quit", "/q"):
                print("Jarvis > Powering down. Have a productive day, Jay.")
                break

            if lowered in ("reset", "/reset", "/clear"):
                brain.reset()
                print("Jarvis > Conversation history cleared and session reinitialized.")
                continue

            if lowered in ("/help", "/h", "help"):
                print("\n" + "=" * 58)
                print("           JARVIS TERMINAL COMMAND DIRECTORY")
                print("=" * 58)
                print(" /help, /h               - Display this command directory")
                print(" /doctor, /check         - Run full pre-flight system diagnostics")
                print(" /mode <normal|combat>   - Transition operational persona")
                print(" /tools                  - List all registered autonomous tools")
                print(" /stats                  - View CPU, RAM, battery & session stats")
                print(" /history                - View active conversation history buffer")
                print(" /compact                - Compact conversation context window")
                print(" /clear, /reset          - Reset conversation memory buffer")
                print(" /quit, /exit, q         - Shutdown terminal session")
                print("=" * 58 + "\n")
                continue

            if lowered in ("/doctor", "/check"):
                from core.doctor import run_doctor
                print("\n[*] Initializing system diagnostic sequence...")
                run_doctor(verbose=True, run_live_llm_ping=False)
                continue

            if lowered.startswith("/mode"):
                parts = user_input.split()
                if len(parts) > 1 and parts[1].lower() in ("normal", "stealth", "combat"):
                    current_mode = parts[1].lower()
                    print(f"Jarvis > Mode transitioned to {current_mode.upper()}. Protocol updated.")
                else:
                    print(f"Jarvis > Current mode: {current_mode.upper()}. Available: normal, stealth, combat.")
                continue

            if lowered == "/tools":
                try:
                    from tools.registry import get_registered_tools
                    tools = get_registered_tools()
                    print(f"\n[*] Registered Autonomous Tools ({len(tools)} active):")
                    print("-" * 68)
                    for idx, tool in enumerate(sorted(tools, key=lambda t: t.name), start=1):
                        desc = (tool.description or "").split(".")[0]
                        print(f" {idx:2d}. {tool.name:<26} | {desc[:36]}")
                    print("-" * 68 + "\n")
                except Exception as exc:
                    print(f"Jarvis > Error querying tool registry: {exc}")
                continue

            if lowered == "/stats":
                try:
                    import psutil
                    cpu = psutil.cpu_percent(interval=0.1)
                    ram = psutil.virtual_memory().percent
                    battery = psutil.sensors_battery()
                    batt_info = f"{battery.percent}%" if battery else "N/A (Desktop/AC)"
                    print("\n" + "-" * 52)
                    print("           LIVE SYSTEM TELEMETRY & STATS")
                    print("-" * 52)
                    print(f" CPU Load:        {cpu}%")
                    print(f" Memory Usage:    {ram}%")
                    print(f" Battery Level:   {batt_info}")
                    print(f" Operating Mode:  {current_mode.upper()}")
                    print(f" LLM Provider:    {brain.llm_provider.upper()} ({brain.model_name})")
                    print(f" History Turns:   {len(brain.history)} entries")
                    print("-" * 52 + "\n")
                except Exception as exc:
                    print(f"Jarvis > Telemetry query failed: {exc}")
                continue

            if lowered == "/history":
                hist = brain.get_history()
                if not hist:
                    print("Jarvis > Conversation history buffer is currently empty.")
                else:
                    print(f"\n[*] Conversation History ({len(hist)} entries):")
                    print("-" * 60)
                    for idx, msg in enumerate(hist, start=1):
                        role = "Jay" if msg.get("role") == "user" else "Jarvis"
                        content = msg.get("content", "")
                        print(f"[{idx:2d}] {role}: {content[:80]}{'...' if len(content) > 80 else ''}")
                    print("-" * 60 + "\n")
                continue

            if lowered == "/compact":
                pruned = brain.compact_history(max_entries=10)
                print(f"Jarvis > Context buffer compacted. Pruned {pruned} older turns. Retained {len(brain.history)} active entries.")
                continue

            # Standard chat directive streaming
            print("Jarvis > ", end="", flush=True)
            for chunk in brain.chat_stream(user_input, mode=current_mode):
                sys.stdout.write(chunk)
                sys.stdout.flush()
            print("\n")

        except (KeyboardInterrupt, EOFError):
            print("\nJarvis > Emergency shutdown requested. Goodbye, Jay.")
            break


_default_brain = None


def get_brain():
    """Retrieve or initialize the shared singleton JarvisBrain instance."""
    global _default_brain
    if _default_brain is None:
        _default_brain = JarvisBrain()
    return _default_brain


def main() -> None:
    """Module entry point."""
    run_interactive_cli()


if __name__ == "__main__":
    main()
