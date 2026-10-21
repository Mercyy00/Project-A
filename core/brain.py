"""Jarvis Core Brain Engine.

Orchestrates multi-turn conversational reasoning, system prompt personas,
and autonomous function calling (ReAct loop) using Google Gemini.
Adheres strictly to Project Jarvis architecture and module contracts.
"""

from __future__ import annotations

import datetime
import os
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types


DEFAULT_SYSTEM_PROMPT: str = (
    "You are Jarvis, an ultra-fast AI desktop assistant. "
    "Reply in the same language as the user (English, Hindi, Marathi, or Hinglish). "
    "When the user speaks Hindi or Marathi, always reply in Devanagari script so text-to-speech can pronounce it properly. "
    "CRITICAL CONVERSATIONAL RULE: Keep your response under 15 words in a single crisp sentence suitable for immediate voice output. Never write paragraphs of conversational fluff. "
    "You are helpful, witty, technically precise, and proactive. "
    "Always ask for confirmation before executing any tool that deletes files, overwrites data, or sends messages. "
    "If a tool fails, say so honestly."
)


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
        api_key: str = load_api_key()
        self.model_name: str = (
            model_name or os.getenv("GEMINI_MODEL") or os.getenv("MODEL_NAME") or "gemini-3.8-flash"
        )
        self.system_prompt: str = system_prompt or DEFAULT_SYSTEM_PROMPT
        self.enable_tools: bool = enable_tools
        self.history: List[Dict[str, str]] = []
        self.last_tool_steps: List[str] = []

        self.groq_api_key: Optional[str] = os.getenv("GROQ_API_KEY")
        self.groq_model: str = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")
        self.llm_provider: str = os.getenv("LLM_PROVIDER", "gemini").lower()

        self.client: genai.Client = genai.Client(api_key=api_key)
        self.tools: List[Callable[..., Any]] = self._discover_tools() if enable_tools else []
        if load_memory:
            self._load_memory_history()
        self._init_chat_session()

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
            """Writes text content to a file inside workspace/ or temp_ directories.

            Args:
                file_path: Target file path to write to.
                content: Text content to write into the file.
            """
            self.last_tool_steps.append(f"write_file({file_path})")
            try:
                from tools.registry import execute_tool
                result = execute_tool("write_file", {"file_path": file_path, "content": content})
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
                from tools.registry import execute_tool
                args = {"command": command}
                if cwd:
                    args["cwd"] = cwd
                return execute_tool("run_command", args).to_llm_string()
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
                from tools.registry import execute_tool
                args = {}
                if code:
                    args["code"] = code
                if file_path:
                    args["file_path"] = file_path
                return execute_tool("run_python", args).to_llm_string()
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

        return discovered

    def _init_chat_session(self) -> None:
        """Initialize or reset the Gemini multi-turn chat session."""
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

    def chat(self, user_message: str, mode: str = "normal") -> str:
        """Process a user message and return the assistant response.

        Maintains full multi-turn conversational history and executes any
        invoked tool calls transparently.

        Args:
            user_message: Spoken or typed user input string.
            mode: Operating mode ('normal', 'silent', 'attentive', 'combat').

        Returns:
            The assistant's natural language response.
        """
        cleaned_input: str = user_message.strip()
        if not cleaned_input:
            return "I am listening. How can I assist you?"

        self.last_tool_steps = []

        # Handle verbal mode switching
        lower_input = cleaned_input.lower()
        if any(k in lower_input for k in ("engage combat mode", "combat mode", "switch to combat mode", "enter combat mode")):
            return "Combat protocol engaged. All neural nodes running at maximum clock. Directives will be executed with extreme speed and precision."
        if any(k in lower_input for k in ("exit combat mode", "disengage combat", "disable combat mode")):
            return "Combat protocol disengaged. Returning to standard standby."
        if any(k in lower_input for k in ("go to silent mode", "switch to silent mode", "silent mode", "standby mode")):
            return "Silent mode engaged. Awaiting wake word directive."
        if any(k in lower_input for k in ("go to attentive mode", "attentive mode", "always listen", "continuous mode", "listen continuously")):
            return "Attentive mode activated. Always listening."

        # Fast Sub-Millisecond Contextual Shortcuts (Zero Cloud Latency)
        stripped_lower = lower_input.strip("?.!")
        time_triggers = (
            "what time is it", "current time", "what is the time", "tell me the time",
            "time please", "what date", "today's date", "which day is it",
            "kiti vajle", "vel kay zali", "samay kya hai", "kitne baje"
        )
        if any(t in stripped_lower for t in time_triggers) or stripped_lower in ("time", "date"):
            now = datetime.datetime.now()
            t = now.strftime("%I:%M %p")
            d = now.strftime("%A, %B %d, %Y")
            return f"The current time is {t} on {d}."

        if stripped_lower in ("system info", "system stats", "cpu usage", "ram usage", "battery", "telemetry", "hardware status", "status report"):
            try:
                from tools.system_tools import GetSystemStatsTool
                stats = GetSystemStatsTool().run()
                if stats.success and stats.data:
                    d = stats.data
                    cpu = d.get("cpu_percent", "N/A")
                    ram = d.get("ram_used_pct", "N/A")
                    batt = d.get("battery_pct", "Plugged in")
                    return f"System Telemetry: CPU load is {cpu}%, RAM usage is {ram}%, Battery at {batt}%. All systems nominal."
            except Exception:
                pass

        # Fast Weather Shortcut (avoid slow DuckDuckGo scraping for location-agnostic weather)
        weather_triggers = ("what is the weather", "what's the weather", "how is the weather", "weather today", "current weather", "aaj mausam kaisa hai", "havaman kase ahe")
        if any(w in stripped_lower for w in weather_triggers) and not any(city in stripped_lower for city in (" in ", " at ", " for ")):
            return "Please specify your city or region, and I will check the live forecast for you." 

        # High-speed Combat Mode or Groq provider
        if (mode == "combat" or self.llm_provider == "groq") and self.groq_api_key:
            return self._chat_with_groq(cleaned_input, is_combat=(mode == "combat"))

        try:
            response = self.chat_session.send_message(cleaned_input)
            response_text: str = response.text.strip() if response.text else ""

            # Record turn in history buffer
            self.history.append({"role": "user", "content": cleaned_input})
            self.history.append({"role": "model", "content": response_text})

            return response_text

        except errors.APIError as err:
            err_str: str = str(err).lower()
            if "gemini-2.5-flash" in self.model_name and ("no longer available" in err_str or "not found" in err_str):
                self.model_name = "gemini-3.8-flash"
                self._init_chat_session()
                return self.chat(user_message)
            if any(k in err_str for k in ("quota", "rate", "429", "resource_exhausted", "503", "high demand", "unavailable")):
                if self.groq_api_key:
                    print(
                        f"[*] Gemini limit encountered ({err.message}). Seamlessly failing over to Groq ({self.groq_model})...",
                        file=sys.stderr,
                    )
                    return self._chat_with_groq(cleaned_input)
                error_msg: str = f"Gemini API rate/quota limit reached: {err.message}"
                print(f"[!] {error_msg}", file=sys.stderr)
                return "Gemini API quota limit reached. Please add GROQ_API_KEY to .env as auto-fallback or retry in a moment."
            error_msg = f"Gemini API error occurred: {err.message}"
            print(f"[!] {error_msg}", file=sys.stderr)
            return "I encountered an error communicating with my neural core."
        except Exception as err:
            error_msg = f"Unexpected error during chat processing: {err}"
            print(f"[!] {error_msg}", file=sys.stderr)
            return "I encountered an internal error processing your request."

    def _chat_with_groq(self, user_message: str, is_combat: bool = False) -> str:
        """Execute chat directive using Groq Cloud API as high-speed fallback or primary engine.

        Maintains conversation history buffer and executes tools autonomously.

        Args:
            user_message: Cleaned user prompt string.
            is_combat: If True, uses tactical high-speed instructions with strict brevity.

        Returns:
            Assistant response string.
        """
        try:
            import json
            from groq import Groq

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
                    tools_param = [
                        {
                            "type": "function",
                            "function": {
                                "name": s["name"],
                                "description": s["description"],
                                "parameters": s.get("parameters", {}),
                            },
                        }
                        for s in schemas
                    ]
                except Exception as exc:
                    print(f"[WARN] Failed to load tool schemas for Groq: {exc}", file=sys.stderr)

            extra_params: Dict[str, Any] = {}
            if tools_param:
                extra_params["tools"] = tools_param
                extra_params["tool_choice"] = "auto"

            candidate_models = [self.groq_model, "openai/gpt-oss-120b", "openai/gpt-oss-20b"]
            completion = None
            used_model = self.groq_model
            for m in candidate_models:
                try:
                    completion = client.chat.completions.create(
                        model=m,
                        messages=messages,
                        temperature=0.4 if is_combat else 0.7,
                        max_tokens=256 if is_combat else 1024,
                        **extra_params,
                    )
                    used_model = m
                    break
                except Exception as m_err:
                    if "429" in str(m_err) or "rate" in str(m_err).lower():
                        continue
                    raise

            if completion is None:
                raise RuntimeError("All Groq models currently experiencing rate limits.")

            msg = completion.choices[0].message
            if msg.tool_calls:
                messages.append(msg)
                from tools.registry import execute_tool
                for tool_call in msg.tool_calls:
                    fn_name = tool_call.function.name
                    fn_args = {}
                    if tool_call.function.arguments:
                        try:
                            fn_args = json.loads(tool_call.function.arguments)
                        except Exception:
                            fn_args = {}
                    self.last_tool_steps.append(f"{fn_name}({fn_args})")
                    tool_res = execute_tool(fn_name, fn_args)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": fn_name,
                        "content": tool_res.to_llm_string(),
                    })

                follow_up = client.chat.completions.create(
                    model=used_model,
                    messages=messages,
                    max_tokens=64 if is_combat else 128,
                    temperature=0.3 if is_combat else 0.5,
                )
                final_text = (follow_up.choices[0].message.content or "").strip()
            else:
                final_text = (msg.content or "").strip()

            self.history.append({"role": "user", "content": user_message})
            self.history.append({"role": "model", "content": final_text})
            return final_text

        except Exception as exc:
            error_msg = f"Groq execution notice: {str(exc)}"
            print(f"[*] {error_msg}. Failing over to Gemini...", file=sys.stderr)
            if self.chat_session:
                try:
                    response = self.chat_session.send_message(user_message)
                    return response.text.strip() if response.text else "Directive acknowledged."
                except Exception as gemini_err:
                    print(f"[!] Gemini failover error: {gemini_err}", file=sys.stderr)
            return "I encountered an issue processing your directive. Please try again."

    def process_input(self, text: str) -> str:
        """Unified interface contract for Voice engine (Aryan) and UI (Rohit).

        Conforms to ARCHITECTURE.md Section 4.1.

        Args:
            text: Input text string from speech-to-text or UI HUD.

        Returns:
            Assistant response text for speech synthesis or UI display.
        """
        return self.chat(text)

    def reset(self) -> None:
        """Clear conversation history and reinitialize the chat session."""
        self.history.clear()
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
    print("=" * 60)
    print(" PROJECT JARVIS - TERMINAL COMMAND CENTER")
    print(" Type your command, or type 'exit' or 'quit' to end session.")
    print("=" * 60)

    try:
        brain: JarvisBrain = JarvisBrain()
    except ValueError as err:
        print(f"\n[!] Initialization Error: {err}\n", file=sys.stderr)
        sys.exit(1)
    except Exception as err:
        print(f"\n[!] Unexpected Error: {err}\n", file=sys.stderr)
        sys.exit(1)

    print("[*] Jarvis Core online. Ready for directives.\n")

    while True:
        try:
            user_input: str = input("Jay > ").strip()
            if not user_input:
                continue

            if user_input.lower() in ("exit", "quit", "q"):
                print("Jarvis > Powering down. Have a productive day, Jay.")
                break

            if user_input.lower() == "reset":
                brain.reset()
                print("Jarvis > Conversation history cleared.")
                continue

            response: str = brain.chat(user_input)
            print(f"Jarvis > {response}\n")

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
