"""Unit tests for Jarvis Core Brain module."""

from __future__ import annotations

import unittest
import threading
import time
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import MagicMock, patch

from core.brain import DEFAULT_SYSTEM_PROMPT, JarvisBrain, load_api_key


class TestJarvisBrain(unittest.TestCase):
    """Test suite for JarvisBrain initialization, conversation memory, and interfaces."""

    def setUp(self) -> None:
        """Set up mock client and responses for testing."""
        self.mock_client_patch = patch("core.brain.genai.Client")
        self.mock_client_class = self.mock_client_patch.start()
        self.mock_client = MagicMock()
        self.mock_client_class.return_value = self.mock_client

        # Mock chat session
        self.mock_chat = MagicMock()
        self.mock_client.chats.create.return_value = self.mock_chat

        # Mock API key retrieval
        self.mock_key_patch = patch("core.brain.load_api_key", return_value="fake-api-key")
        self.mock_key_patch.start()

        # Isolate environment for deterministic Gemini brain unit testing
        self.mock_env = patch.dict("os.environ", {"LLM_PROVIDER": "gemini", "GROQ_API_KEY": "", "GEMINI_MODEL": "", "MODEL_NAME": ""})
        self.mock_env.start()

    def tearDown(self) -> None:
        """Tear down all patches."""
        self.mock_client_patch.stop()
        self.mock_key_patch.stop()
        self.mock_env.stop()

    def test_initialization(self) -> None:
        """Verify brain initializes with default model and system prompt."""
        brain = JarvisBrain()
        self.assertIn(brain.model_name, ("gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-2.5-flash"))
        self.assertEqual(brain.system_prompt, DEFAULT_SYSTEM_PROMPT)
        self.assertEqual(len(brain.history), 0)
        self.assertEqual(brain.max_history_entries, 8)
        self.mock_client.chats.create.assert_called_once()

    def test_concurrent_turns_are_serialized(self) -> None:
        """Shared Gemini session turns must not overlap or exchange answers."""
        brain = JarvisBrain()
        active = 0
        max_active = 0
        counter_lock = threading.Lock()

        def fake_turn(message: str, mode: str = "normal", cancel_event=None):
            nonlocal active, max_active
            with counter_lock:
                active += 1
                max_active = max(max_active, active)
            time.sleep(0.02)
            with counter_lock:
                active -= 1
            yield f"answer to {message}"

        with patch.object(brain, "_chat_stream_unlocked", side_effect=fake_turn):
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(brain.chat, ["first question", "second question"]))

        self.assertEqual(max_active, 1)
        self.assertEqual(set(results), {"answer to first question", "answer to second question"})

    def test_chat_multi_turn_history(self) -> None:
        """Verify chat updates conversation history buffer accurately."""
        mock_response_1 = MagicMock()
        mock_response_1.text = "Hello Jay. All systems operational."
        mock_response_2 = MagicMock()
        mock_response_2.text = "Your CPU is running optimally at 14%."

        self.mock_chat.send_message.side_effect = [mock_response_1, mock_response_2]

        brain = JarvisBrain()
        reply_1 = brain.chat("Jarvis, report status.")
        self.assertEqual(reply_1, "Hello Jay. All systems operational.")

        reply_2 = brain.chat("How is my CPU doing?")
        self.assertEqual(reply_2, "Your CPU is running optimally at 14%.")

        history = brain.get_history()
        self.assertEqual(len(history), 4)
        self.assertEqual(history[0], {"role": "user", "content": "Jarvis, report status."})
        self.assertEqual(history[1], {"role": "model", "content": "Hello Jay. All systems operational."})
        self.assertEqual(history[2], {"role": "user", "content": "How is my CPU doing?"})
        self.assertEqual(history[3], {"role": "model", "content": "Your CPU is running optimally at 14%."})

    def test_process_input_interface_contract(self) -> None:
        """Verify process_input is an exact functional alias for chat."""
        mock_response = MagicMock()
        mock_response.text = "Confirmed, Jay."
        self.mock_chat.send_message.return_value = mock_response

        brain = JarvisBrain()
        reply = brain.process_input("Confirm interface compliance.")
        self.assertEqual(reply, "Confirmed, Jay.")
        call = self.mock_chat.send_message.call_args
        self.assertEqual(call.args, ("Confirm interface compliance.",))
        self.assertIsNone(call.kwargs["config"].tools)

    def test_request_tool_selection_limits_schemas_to_user_intent(self) -> None:
        """Normal chat sends no tool schemas and screen requests expose vision tools."""
        brain = JarvisBrain()

        normal_tools = brain._select_tools_for_request("Explain how eclipses work")
        screen_tools = brain._select_tools_for_request("What is visible on my screen?")

        self.assertEqual(normal_tools, [])
        screen_names = {tool.__name__ for tool in screen_tools}
        self.assertIn("describe_screen", screen_names)
        self.assertIn("capture_screen", screen_names)
        self.assertNotIn("create_document", screen_names)

    def test_request_tool_selection_keeps_task_categories_available(self) -> None:
        """Explicit requests receive the tool category needed to complete them."""
        brain = JarvisBrain()

        cases = {
            "search the web for Gemini API rate limits": {"search_web"},
            "create a PDF report about climate change": {"create_document", "create_pdf"},
            "send this message on Telegram": {"send_telegram"},
            "remember this note for later": {"save_note"},
        }
        for prompt, expected in cases.items():
            with self.subTest(prompt=prompt):
                selected = {tool.__name__ for tool in brain._select_tools_for_request(prompt)}
                self.assertTrue(expected.issubset(selected))

    def test_gemini_request_receives_only_selected_tool_declarations(self) -> None:
        """The outgoing request config must not reattach the full tool catalog."""
        mock_response = MagicMock()
        mock_response.text = "I can see your open application."
        self.mock_chat.send_message.return_value = mock_response
        brain = JarvisBrain()

        brain.chat("What is visible on my screen?")

        request_config = self.mock_chat.send_message.call_args.kwargs["config"]
        sent_tools = {tool.__name__ for tool in request_config.tools}
        self.assertIn("describe_screen", sent_tools)
        self.assertNotIn("create_document", sent_tools)

    def test_compound_request_executes_local_actions_without_llm(self) -> None:
        """Handle the common multi-tab, local-app, time, and arithmetic request offline."""
        from tools.base import ToolResult

        brain = JarvisBrain()
        user_request = (
            "On Chrome search about Modern Warfare four and then another tab open and search LinkedIn "
            "and then open another tab and search YouTube and also open my downloads folder and also "
            "open calculator and tell me what's the time and also what's 13 + 13 into 26"
        )
        with patch("tools.registry.execute_tool", return_value=ToolResult(
            success=True, data={}, message="Action completed"
        )) as execute:
            reply = brain.chat(user_request)

        self.assertEqual(execute.call_count, 5)
        self.assertEqual(
            [call.args[0] for call in execute.call_args_list],
            ["browser_control", "browser_control", "browser_control", "open_file", "open_app"],
        )
        self.assertEqual(
            [call.args[1] for call in execute.call_args_list[:3]],
            [
                {"action": "search", "query": "Modern Warfare four", "browser": "chrome"},
                {"action": "search", "query": "LinkedIn", "browser": "chrome"},
                {"action": "search", "query": "YouTube", "browser": "chrome"},
            ],
        )
        self.assertIn("351", reply)
        self.assertIn("13 + 13 * 26 = 351", reply)

    def test_plain_and_separated_browser_tasks_keep_searches_ordered(self) -> None:
        """Natural conjunctions should preserve each ordered Chrome search."""
        from tools.base import ToolResult

        brain = JarvisBrain()
        prompt = (
            "search about carryminati on YouTube and open Chrome for me and open another tab "
            "and search LinkedIn and open another tab and search it up"
        )
        with patch("tools.registry.execute_tool", return_value=ToolResult(
            success=True, data={}, message="Action completed"
        )) as execute:
            reply = brain.chat(prompt)

        self.assertEqual(execute.call_count, 3)
        self.assertEqual(
            [call.args[1] for call in execute.call_args_list],
            [
                {
                    "action": "open",
                    "url": "https://www.youtube.com/results?search_query=carryminati",
                    "browser": "chrome",
                },
                {"action": "search", "query": "LinkedIn", "browser": "chrome"},
                {"action": "search", "query": "LinkedIn", "browser": "chrome"},
            ],
        )
        self.assertIn("Completed the requested steps", reply)

    def test_direct_document_request_uses_creator_without_chat_llm(self) -> None:
        """A direct PDF request reaches the creator even when chat reasoning is unavailable."""
        import json
        from tools.base import ToolResult

        brain = JarvisBrain()
        with patch("ddgs.DDGS") as mock_ddgs:
            mock_ddgs.return_value.__enter__.return_value.text.return_value = [{
                "title": "Official update",
                "body": "A sample current update excerpt.",
                "href": "https://example.com/update",
            }]
            with patch("tools.registry.execute_tool", return_value=ToolResult(
                success=True,
                data={"file_path": "workspace/cod_mw4.pdf"},
                message="Document created.",
            )) as execute:
                reply = brain.chat("Jarvis create me a PDF about COD MW4 latest game in MW style")

        execute.assert_called_once_with(
            "create_document",
            {
                "topic": "COD MW4 latest game",
                "kind": "pdf",
                "theme": "dark_pro",
                "auto_open": True,
                "reference_material": json.dumps([{
                    "title": "Official update",
                    "body": "A sample current update excerpt.",
                    "href": "https://example.com/update",
                }], ensure_ascii=False),
            },
        )
        self.assertIn("workspace/cod_mw4.pdf", reply)
        self.assertIn("1 live search sources", reply)

    def test_pdf_request_with_for_me_wording_uses_creator(self) -> None:
        """Natural PDF wording should route directly to the document creator."""
        from tools.base import ToolResult

        brain = JarvisBrain()
        with patch("tools.registry.execute_tool", return_value=ToolResult(
            success=True,
            data={"file_path": "workspace/solar_energy.pdf"},
            message="Document created.",
        )) as execute:
            reply = brain.chat("Please create a PDF for me about solar energy")

        execute.assert_called_once_with(
            "create_document",
            {
                "topic": "solar energy",
                "kind": "pdf",
                "theme": "clean_light",
                "auto_open": True,
            },
        )
        self.assertIn("workspace/solar_energy.pdf", reply)

    def test_quick_action_polished_pdf_prompt_routes_without_gemini(self) -> None:
        """The HUD's built-in polished-PDF command must work during quota exhaustion."""
        from tools.base import ToolResult

        brain = JarvisBrain()
        with patch("ddgs.DDGS") as ddgs, patch("tools.registry.execute_tool", return_value=ToolResult(
            success=True,
            data={"file_path": "workspace/call_of_duty.pdf"},
            message="Document created.",
        )) as execute:
            ddgs.return_value.__enter__.return_value.text.return_value = []
            reply = brain.chat("Create a polished PDF about the latest Call of Duty Modern Warfare game")

        execute.assert_called_once_with(
            "create_document",
            {
                "topic": "the latest Call of Duty Modern Warfare game",
                "kind": "pdf",
                "theme": "dark_pro",
                "auto_open": True,
            },
        )
        self.assertIn("Created the PDF document", reply)

    def test_quick_action_builds_a_real_pdf_when_gemini_is_unavailable(self) -> None:
        """The quick action should create a valid PDF using the offline outline."""
        from tools.registry import execute_tool

        brain = JarvisBrain()
        with tempfile.TemporaryDirectory() as output_dir:
            def execute_to_temp(name, args=None):
                safe_args = dict(args or {})
                safe_args["out_dir"] = output_dir
                safe_args["auto_open"] = False
                return execute_tool(name, safe_args)

            with patch("creator.outline._request_gemini_outline", return_value=None), \
                 patch("ddgs.DDGS") as ddgs, \
                 patch("tools.registry.execute_tool", side_effect=execute_to_temp):
                ddgs.return_value.__enter__.return_value.text.return_value = []
                reply = brain.chat(
                    "Create a polished PDF about the latest Call of Duty Modern Warfare game"
                )

            created_path = next(Path(output_dir).glob("*.pdf"))
            self.assertTrue(created_path.is_file())
            self.assertGreater(created_path.stat().st_size, 500)
            self.assertTrue(created_path.read_bytes().startswith(b"%PDF"))
            self.assertIn(str(created_path), reply)

    def test_reset_conversation(self) -> None:
        """Verify resetting clears history and starts new chat session."""
        mock_response = MagicMock()
        mock_response.text = "Understood."
        self.mock_chat.send_message.return_value = mock_response

        brain = JarvisBrain()
        brain.chat("Remember this.")
        self.assertEqual(len(brain.get_history()), 2)

        brain.reset()
        self.assertEqual(len(brain.get_history()), 0)
        self.assertEqual(self.mock_client.chats.create.call_count, 2)

    def test_missing_api_key_raises_value_error(self) -> None:
        """Verify clean error when GEMINI_API_KEY is missing."""
        with patch.dict("os.environ", {}, clear=True), patch("core.brain.load_dotenv"):
            with self.assertRaises(ValueError) as ctx:
                load_api_key()
            self.assertIn("GEMINI_API_KEY is missing", str(ctx.exception))

    def test_groq_key_does_not_replace_required_gemini_key(self) -> None:
        """The core requires its sole configured provider, Gemini."""
        with patch("core.brain.load_api_key", side_effect=ValueError("missing Gemini key")):
            with patch.dict(
                "os.environ",
                {
                    "GROQ_API_KEY": "gsk-test-key",
                    "LLM_PROVIDER": "groq",
                    "GEMINI_API_KEY": "",
                },
            ):
                with self.assertRaisesRegex(ValueError, "Gemini key"):
                    JarvisBrain(enable_tools=False)

    def test_compact_history(self) -> None:
        """Verify context compaction prunes older turns and maintains sliding window."""
        brain = JarvisBrain()
        for i in range(25):
            brain.history.append({"role": "user", "content": f"msg {i}"})
            brain.history.append({"role": "model", "content": f"reply {i}"})
        self.assertEqual(len(brain.history), 50)

        pruned = brain.compact_history(max_entries=10)
        self.assertEqual(pruned, 40)
        self.assertEqual(len(brain.history), 10)
        self.assertEqual(brain.history[-1]["content"], "reply 24")

    def test_compact_history_rebuilds_gemini_session_from_retained_turns(self) -> None:
        """Compaction must keep the live Gemini context bounded as well as local history."""
        brain = JarvisBrain()
        for i in range(6):
            brain.history.extend([
                {"role": "user", "content": f"question {i}"},
                {"role": "model", "content": f"answer {i}"},
            ])

        brain.compact_history(max_entries=4)

        self.assertEqual(len(brain.history), 4)
        self.assertEqual(
            self.mock_client.chats.create.call_args.kwargs["history"],
            [
                {"role": "user", "parts": [{"text": "question 4"}]},
                {"role": "model", "parts": [{"text": "answer 4"}]},
                {"role": "user", "parts": [{"text": "question 5"}]},
                {"role": "model", "parts": [{"text": "answer 5"}]},
            ],
        )

    def test_external_message_tool_requires_user_confirmation(self) -> None:
        """Sending a message must be queued until the user confirms it."""
        from tools.base import ToolResult
        from core.confirm import _pending_confirmations

        brain = JarvisBrain(enable_tools=False)
        _pending_confirmations.clear()
        self.addCleanup(_pending_confirmations.clear)
        with patch("tools.registry.execute_tool") as dispatch:
            result = brain._execute_registered_tool(
                "send_telegram", {"text": "A test message"}
            )

        self.assertIsInstance(result, ToolResult)
        self.assertFalse(result.success)
        self.assertIn("CONFIRM", result.message)
        dispatch.assert_not_called()

    def test_whatsapp_tool_requires_user_confirmation(self) -> None:
        """WhatsApp recipient and exact message are gated before dispatch."""
        from tools.base import ToolResult
        from core.confirm import _pending_confirmations

        brain = JarvisBrain(enable_tools=False)
        _pending_confirmations.clear()
        self.addCleanup(_pending_confirmations.clear)
        with patch("tools.registry.execute_tool") as dispatch:
            result = brain._execute_registered_tool(
                "send_whatsapp", {"contact": "Alex", "message": "Meet me at 5"}
            )

        self.assertIsInstance(result, ToolResult)
        self.assertFalse(result.success)
        self.assertIn("send_whatsapp", result.message)
        self.assertIn("Alex", result.message)
        self.assertIn("Meet me at 5", result.message)
        self.assertIn("CONFIRM", result.message)
        dispatch.assert_not_called()

    def test_confirmation_token_executes_queued_tool_once(self) -> None:
        """A valid explicit confirmation executes its queued action once."""
        from tools.base import ToolResult
        from core.confirm import _pending_confirmations

        brain = JarvisBrain(enable_tools=False)
        _pending_confirmations.clear()
        self.addCleanup(_pending_confirmations.clear)
        with patch("core.confirm.secrets.token_hex", return_value="A1B2C3D4E5F60718"):
            with patch("tools.registry.execute_tool", return_value=ToolResult(
                success=True,
                data=None,
                message="Telegram message delivered.",
            )) as dispatch:
                pending = brain._execute_registered_tool(
                    "send_telegram", {"text": "A test message"}
                )
                self.assertIn("CONFIRM A1B2C3D4E5F60718", pending.message)
                chunks = list(brain.chat_stream("CONFIRM A1B2C3D4E5F60718"))

        self.assertEqual(chunks, ["Telegram message delivered."])
        dispatch.assert_called_once_with(
            name="send_telegram", args={"text": "A test message"}
        )
        self.assertEqual(_pending_confirmations, {})

    def test_overwriting_a_file_requires_user_confirmation(self) -> None:
        """The LLM dispatch path must gate explicit file overwrites."""
        from tools.base import ToolResult
        from core.confirm import _pending_confirmations

        brain = JarvisBrain(enable_tools=False)
        _pending_confirmations.clear()
        self.addCleanup(_pending_confirmations.clear)
        with patch("tools.registry.execute_tool") as dispatch:
            result = brain._execute_registered_tool(
                "write_file",
                {"file_path": "workspace/report.txt", "content": "new content", "overwrite": True},
            )

        self.assertIsInstance(result, ToolResult)
        self.assertFalse(result.success)
        self.assertIn("CONFIRM", result.message)
        dispatch.assert_not_called()

    def test_destructive_code_execution_requires_confirmation(self) -> None:
        """Recognizable deletion commands require confirmation before execution."""
        from tools.base import ToolResult
        from core.confirm import _pending_confirmations

        brain = JarvisBrain(enable_tools=False)
        _pending_confirmations.clear()
        self.addCleanup(_pending_confirmations.clear)
        cases = [
            ("run_command", {"command": "Remove-Item workspace\\report.txt"}),
            ("run_python", {"code": "Path('workspace/report.txt').unlink()"}),
        ]

        for tool_name, args in cases:
            with self.subTest(tool_name=tool_name):
                with patch("tools.registry.execute_tool") as dispatch:
                    result = brain._execute_registered_tool(tool_name, args)
                self.assertIsInstance(result, ToolResult)
                self.assertFalse(result.success)
                self.assertIn("CONFIRM", result.message)
                dispatch.assert_not_called()

    def test_gemini_destructive_wrappers_use_confirmation_gate(self) -> None:
        """Gemini's callable wrappers must apply the confirmation gate."""
        from core.confirm import _pending_confirmations

        brain = JarvisBrain(enable_tools=True)
        _pending_confirmations.clear()
        self.addCleanup(_pending_confirmations.clear)
        wrappers = {tool.__name__: tool for tool in brain.tools}

        command_result = wrappers["run_command"](
            command="Remove-Item workspace\\report.txt"
        )
        python_result = wrappers["run_python"](
            code="Path('workspace/report.txt').unlink()"
        )

        self.assertIn("CONFIRM", command_result)
        self.assertIn("CONFIRM", python_result)

    def test_gemini_quota_error_is_not_retried(self) -> None:
        """A quota error returns immediately without spending more requests."""
        from google.genai import errors

        brain = JarvisBrain(enable_tools=False)
        self.mock_chat.send_message_stream.side_effect = errors.APIError(
            429,
            {"message": "Quota exceeded", "status": "RESOURCE_EXHAUSTED"},
        )

        reply = list(brain.chat_stream("Say hello"))

        self.assertEqual(len(reply), 1)
        self.assertIn("rate-limited", reply[0])
        call = self.mock_chat.send_message_stream.call_args
        self.assertEqual(call.args, ("Say hello",))
        self.assertIsNone(call.kwargs["config"].tools)
        self.mock_chat.send_message.assert_not_called()


if __name__ == "__main__":
    unittest.main()
