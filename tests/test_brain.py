"""Unit tests for Jarvis Core Brain module."""

from __future__ import annotations

import unittest
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
        self.assertIn(brain.model_name, ("gemini-2.5-flash", "gemini-3.8-flash", "gemini-3.5-flash-lite"))
        self.assertEqual(brain.system_prompt, DEFAULT_SYSTEM_PROMPT)
        self.assertEqual(len(brain.history), 0)
        self.mock_client.chats.create.assert_called_once()

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
        self.mock_chat.send_message.assert_called_with("Confirm interface compliance.")

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

    def test_direct_document_request_uses_creator_without_chat_llm(self) -> None:
        """A direct PDF request reaches the creator even when chat reasoning is unavailable."""
        import json
        from tools.base import ToolResult

        brain = JarvisBrain()
        with patch("ddgs.DDGS") as mock_ddgs:
            mock_ddgs.return_value.text.return_value = [{
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

    def test_groq_only_configuration_initializes_without_gemini(self) -> None:
        """A valid Groq key must be enough to start the brain without Gemini."""
        with patch("core.brain.load_api_key", side_effect=ValueError("missing Gemini key")):
            with patch.dict(
                "os.environ",
                {
                    "GROQ_API_KEY": "gsk-test-key",
                    "LLM_PROVIDER": "groq",
                    "GEMINI_API_KEY": "",
                },
            ):
                brain = JarvisBrain(enable_tools=False)

        self.assertEqual(brain.llm_provider, "groq")
        self.assertIsNone(brain.client)
        self.assertIsNone(brain.chat_session)

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
        """Gemini's callable wrappers must apply the same gate as Groq dispatch."""
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

    def test_gemini_runtime_error_fails_over_to_groq(self) -> None:
        """A non-quota Gemini error should still use the configured backup provider."""
        brain = JarvisBrain(enable_tools=False)
        brain.groq_api_key = "test-groq-key"
        self.mock_chat.send_message_stream.side_effect = RuntimeError("connection reset")

        with patch.object(
            brain,
            "_chat_stream_with_groq",
            return_value=iter(["Backup provider reply."]),
        ) as groq_fallback:
            reply = list(brain.chat_stream("Say hello"))

        self.assertEqual(reply, ["Backup provider reply."])
        groq_fallback.assert_called_once()

    def test_groq_tool_schemas_preserve_arguments_without_oversized_enums(self) -> None:
        """Groq gets all tool schemas with compact but structurally complete arguments."""
        import json
        from core.brain import _groq_tool_definitions
        from tools.registry import get_tools_schema

        definitions = _groq_tool_definitions(get_tools_schema())
        by_name = {item["function"]["name"]: item["function"] for item in definitions}
        encoded = json.dumps(definitions, separators=(",", ":"))

        self.assertEqual(len(definitions), 52)
        self.assertIn("search_whatsapp_contacts", by_name)
        self.assertIn("send_whatsapp", by_name)
        self.assertLess(len(encoded), 20_000)
        self.assertNotIn("enum", by_name["open_app"]["parameters"]["properties"]["app_name"])
        section_items = by_name["create_pdf"]["parameters"]["properties"]["sections"]["items"]
        self.assertEqual(section_items["type"], "object")
        self.assertIn("heading", section_items["properties"])

    def test_groq_executes_tool_calls_returned_by_tool_follow_up(self) -> None:
        """Groq should keep reasoning through successive tool calls until it answers."""
        import sys
        from types import SimpleNamespace
        from tools.base import ToolResult

        def call_chunk(call_id: str, name: str, arguments: str):
            call = SimpleNamespace(
                index=0,
                id=call_id,
                function=SimpleNamespace(name=name, arguments=arguments),
            )
            delta = SimpleNamespace(tool_calls=[call], content=None)
            return SimpleNamespace(choices=[SimpleNamespace(delta=delta)])

        final_delta = SimpleNamespace(tool_calls=None, content="Both browser steps are complete.")
        final_chunk = SimpleNamespace(choices=[SimpleNamespace(delta=final_delta)])
        client = MagicMock()
        client.chat.completions.create.side_effect = [
            iter([call_chunk("call_1", "browser_control", '{"action":"new_tab"}')]),
            iter([call_chunk("call_2", "browser_control", '{"action":"navigate","url":"https://youtube.com"}')]),
            iter([final_chunk]),
        ]
        brain = JarvisBrain(enable_tools=True)
        brain.groq_api_key = "test-groq-key"
        with patch.dict(sys.modules, {"groq": SimpleNamespace(Groq=lambda api_key: client)}):
            with patch.object(brain, "_execute_registered_tool", return_value=ToolResult(success=True, message="Done")) as execute:
                response = brain._chat_with_groq("Open a new tab and go to YouTube")

        self.assertEqual(response, "Both browser steps are complete.")
        self.assertEqual(execute.call_count, 2)
        self.assertEqual(client.chat.completions.create.call_count, 3)
        self.assertIn("tools", client.chat.completions.create.call_args_list[1].kwargs)


if __name__ == "__main__":
    unittest.main()
