"""Jarvis Core Brain Engine.

Orchestrates multi-turn conversational reasoning, system prompt personas,
and autonomous function calling (ReAct loop) using Google Gemini.
Adheres strictly to Project Jarvis architecture and module contracts.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types


DEFAULT_SYSTEM_PROMPT: str = (
    "You are Jarvis, an ultra-efficient desktop assistant. "
    "Speak concisely in 1-2 sentences suitable for voice. "
    "You are helpful, witty, technically precise, and proactive."
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
    ) -> None:
        """Initialize JarvisBrain with API client, chat session, and tool registry.

        Args:
            model_name: Optional Gemini model name identifier (defaults to MODEL_NAME env or 'gemini-3.8-flash').
            system_prompt: Optional custom persona instructions.
            enable_tools: Whether to auto-discover and register tools for function calling.
        """
        api_key: str = load_api_key()
        self.model_name: str = model_name or os.getenv("MODEL_NAME", "gemini-3.5-flash-lite")
        self.system_prompt: str = system_prompt or DEFAULT_SYSTEM_PROMPT
        self.enable_tools: bool = enable_tools
        self.history: List[Dict[str, str]] = []

        self.client: genai.Client = genai.Client(api_key=api_key)
        self.tools: List[Callable[..., Any]] = self._discover_tools() if enable_tools else []
        self._init_chat_session()

    def _discover_tools(self) -> List[Callable[..., Any]]:
        """Discover and wrap available tools for Gemini automatic function calling.

        Returns:
            List of callable tool functions.
        """
        discovered: List[Callable[..., Any]] = []

        try:
            from tools.system_tools import GetSystemStatsTool, OpenAppTool, ListDirectoryTool

            stats_tool = GetSystemStatsTool()
            app_tool = OpenAppTool()
            list_tool = ListDirectoryTool()

            def get_system_stats() -> str:
                """Retrieves current laptop telemetry including CPU usage percentage, RAM usage, and battery status."""
                result = stats_tool.run()
                return result.to_llm_string()

            def open_app(app_name: str) -> str:
                """Opens a desktop application such as chrome, notepad, calc, or spotify."""
                result = app_tool.run(app_name=app_name)
                return result.to_llm_string()

            def list_directory(directory_path: str = ".") -> str:
                """Lists files and folders inside a given directory path."""
                result = list_tool.run(directory_path=directory_path)
                return result.to_llm_string()

            def save_note(title: str, content: str) -> str:
                """Saves an important note, reminder, or memory to SQLite."""
                from memory.tools import SaveNoteTool
                return SaveNoteTool().run(title=title, content=content).to_llm_string()

            def search_notes(query: str) -> str:
                """Searches through saved notes in SQLite using keyword query."""
                from memory.tools import SearchNotesTool
                return SearchNotesTool().run(query=query).to_llm_string()

            discovered.extend([get_system_stats, open_app, list_directory, save_note, search_notes])
        except Exception as e:
            print(f"[!] Tool discovery warning: {e}", file=sys.stderr)

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

    def chat(self, user_message: str) -> str:
        """Process a user message and return the assistant response.

        Maintains full multi-turn conversational history and executes any
        invoked tool calls transparently.

        Args:
            user_message: Spoken or typed user input string.

        Returns:
            The assistant's natural language response.
        """
        cleaned_input: str = user_message.strip()
        if not cleaned_input:
            return "I am listening. How can I assist you?"

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
            error_msg: str = f"Gemini API error occurred: {err.message}"
            print(f"[!] {error_msg}", file=sys.stderr)
            return "I encountered an error communicating with my neural core."
        except Exception as err:
            error_msg = f"Unexpected error during chat processing: {err}"
            print(f"[!] {error_msg}", file=sys.stderr)
            return "I encountered an internal error processing your request."

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


def main() -> None:
    """Module entry point."""
    run_interactive_cli()


if __name__ == "__main__":
    main()
