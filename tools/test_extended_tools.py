"""
Verification test suite for extended Jarvis system tools.
Author: Abhijit (System & Automation Engineer)

Tests:
1. OpenAppTool extension with common Windows apps and safe handling.
2. OpenWebsiteTool shortcut mapping, direct URL opening, scheme rejection.
3. SearchWebTool query escaping, Google/YouTube targets, error handling.
4. Tool registry integration and safe execution dispatching.
5. BaseTool contract compliance, typing, schema generation, and exception safety.
"""

import os
import sys
import types
import unittest
import urllib.parse
from unittest.mock import MagicMock, patch

# Ensure project root is in sys.path regardless of execution directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools.base import BaseTool, ToolResult
from tools.system_tools import (
    GetSystemStatsTool,
    OpenAppTool,
    ListDirectoryTool,
    OpenWebsiteTool,
    SearchWebTool,
)
from tools.registry import (
    TOOL_REGISTRY,
    execute_tool,
    execute,
    get_registered_tools,
    get_tools_schema,
)


class TestOpenAppTool(unittest.TestCase):
    """Tests for OpenAppTool extension and robustness."""

    def setUp(self) -> None:
        self.tool = OpenAppTool()

    def test_extended_app_mapping_contains_required_apps(self) -> None:
        """Verifies common Windows apps exist in OpenAppTool mapping."""
        required_apps = [
            "chrome", "code", "calc", "notepad", "spotify",  # original apps
            "explorer", "cmd", "paint", "settings", "vlc", "word", "excel",  # requested apps
        ]
        for app in required_apps:
            self.assertIn(app, self.tool.APP_MAPPING, f"App '{app}' should be in APP_MAPPING")

    def test_unknown_app_returns_failure_without_crash(self) -> None:
        """Verifies unknown app returns ToolResult(success=False) and never raises."""
        result = self.tool.run(app_name="unknown_super_app_99")
        self.assertIsInstance(result, ToolResult)
        self.assertFalse(result.success)
        self.assertIsNone(result.data)
        self.assertIn("Unknown application shortcut", result.message)

    def test_invalid_app_name_types(self) -> None:
        """Verifies empty or non-string app_name returns ToolResult(success=False)."""
        result_empty = self.tool.run(app_name="")
        self.assertFalse(result_empty.success)

        result_none = self.tool.run(app_name=None)  # type: ignore
        self.assertFalse(result_none.success)

        result_int = self.tool.run(app_name=123)  # type: ignore
        self.assertFalse(result_int.success)

    @patch("subprocess.Popen")
    @patch("os.path.exists", return_value=True)
    def test_launch_app_success(self, mock_exists: MagicMock, mock_popen: MagicMock) -> None:
        """Verifies launching an app returns success with PID."""
        mock_proc = MagicMock()
        mock_proc.pid = 4321
        mock_popen.return_value = mock_proc

        result = self.tool.run(app_name="notepad")
        self.assertTrue(result.success)
        self.assertEqual(result.data["app_name"], "notepad")
        self.assertEqual(result.data["pid"], 4321)
        mock_popen.assert_called_once()

    def test_schema_validity(self) -> None:
        """Verifies OpenAppTool schema definition."""
        schema = self.tool.get_schema()
        self.assertEqual(schema["name"], "open_app")
        self.assertIn("app_name", schema["parameters"]["properties"])
        self.assertEqual(schema["parameters"]["required"], ["app_name"])
        enum_values = schema["parameters"]["properties"]["app_name"]["enum"]
        self.assertIn("explorer", enum_values)
        self.assertIn("cmd", enum_values)
        self.assertIn("paint", enum_values)
        self.assertIn("settings", enum_values)
        self.assertIn("vlc", enum_values)
        self.assertIn("word", enum_values)
        self.assertIn("excel", enum_values)


class TestOpenWebsiteTool(unittest.TestCase):
    """Tests for OpenWebsiteTool shortcuts and URL handling."""

    def setUp(self) -> None:
        self.tool = OpenWebsiteTool()

    @patch("webbrowser.open", return_value=True)
    def test_shortcut_mapping_success(self, mock_browser: MagicMock) -> None:
        """Verifies shortcuts ('youtube', 'google', 'gmail', 'github') resolve correctly."""
        expected = {
            "youtube": "https://www.youtube.com",
            "google": "https://www.google.com",
            "gmail": "https://mail.google.com",
            "github": "https://github.com",
        }
        for shortcut, expected_url in expected.items():
            mock_browser.reset_mock()
            result = self.tool.run(site=shortcut)
            self.assertTrue(result.success, f"Shortcut '{shortcut}' should succeed")
            self.assertEqual(result.data["url"], expected_url)
            mock_browser.assert_called_once_with(expected_url)

    @patch("webbrowser.open", return_value=True)
    def test_shortcut_case_insensitivity(self, mock_browser: MagicMock) -> None:
        """Verifies shortcuts are case-insensitive."""
        result = self.tool.run(site="YouTube")
        self.assertTrue(result.success)
        self.assertEqual(result.data["url"], "https://www.youtube.com")

        result2 = self.tool.run(site="  GITHUB  ")
        self.assertTrue(result2.success)
        self.assertEqual(result2.data["url"], "https://github.com")

    @patch("webbrowser.open", return_value=True)
    def test_direct_http_and_https_urls(self, mock_browser: MagicMock) -> None:
        """Verifies direct http:// and https:// URLs are opened directly."""
        urls = [
            "https://docs.python.org/3/",
            "http://localhost:8000/dashboard",
            "https://en.wikipedia.org/wiki/Artificial_intelligence",
        ]
        for url in urls:
            mock_browser.reset_mock()
            result = self.tool.run(site=url)
            self.assertTrue(result.success)
            self.assertEqual(result.data["url"], url)
            mock_browser.assert_called_once_with(url)

    @patch("webbrowser.open")
    def test_reject_unsupported_url_schemes(self, mock_browser: MagicMock) -> None:
        """Verifies URL schemes other than http and https are rejected."""
        invalid_schemes = [
            "ftp://ftp.example.com/files",
            "file:///C:/Windows/System32/cmd.exe",
            "javascript:alert(1)",
            "data:text/html,<h1>test</h1>",
            "ssh://user@server.com",
        ]
        for bad_url in invalid_schemes:
            result = self.tool.run(site=bad_url)
            self.assertFalse(result.success, f"Scheme in '{bad_url}' must be rejected")
            self.assertIn("Invalid URL scheme", result.message)
            mock_browser.assert_not_called()

    @patch("webbrowser.open")
    def test_reject_unknown_shortcuts(self, mock_browser: MagicMock) -> None:
        """Verifies unknown shortcuts without http/https are rejected."""
        unknown = ["unknown_service", "customsite", "reddit"]
        for site in unknown:
            result = self.tool.run(site=site)
            self.assertFalse(result.success)
            self.assertIn("Unknown website shortcut", result.message)
            mock_browser.assert_not_called()

    def test_reject_invalid_or_empty_inputs(self) -> None:
        """Verifies empty or non-string inputs are rejected safely."""
        for invalid in ["", "   ", None, 42]:
            result = self.tool.run(site=invalid)  # type: ignore
            self.assertFalse(result.success)
            self.assertIn("site must be a non-empty string", result.message)

    @patch("webbrowser.open", side_effect=Exception("Browser launch failed"))
    def test_webbrowser_exception_handled_safely(self, mock_browser: MagicMock) -> None:
        """Verifies webbrowser errors are trapped and return ToolResult(success=False)."""
        result = self.tool.run(site="google")
        self.assertFalse(result.success)
        self.assertIn("Failed to open website", result.message)

    def test_schema_validity(self) -> None:
        """Verifies OpenWebsiteTool schema definition."""
        schema = self.tool.get_schema()
        self.assertEqual(schema["name"], "open_website")
        self.assertIn("site", schema["parameters"]["properties"])
        self.assertEqual(schema["parameters"]["required"], ["site"])


class TestSearchWebTool(unittest.TestCase):
    """Tests for SearchWebTool query escaping and platform search."""

    def setUp(self) -> None:
        self.tool = SearchWebTool()
        ddgs_module = types.ModuleType("ddgs")
        fake_ddgs = MagicMock()
        fake_ddgs.__enter__.return_value = fake_ddgs
        fake_ddgs.text.return_value = []
        ddgs_module.DDGS = MagicMock(return_value=fake_ddgs)  # type: ignore[attr-defined]
        patcher = patch.dict(sys.modules, {"ddgs": ddgs_module})
        patcher.start()
        self.addCleanup(patcher.stop)

    @patch("webbrowser.open", return_value=True)
    def test_search_fetches_bounded_snippets_and_closes_ddgs(self, mock_browser: MagicMock) -> None:
        """Search returns useful snippets without sending an unbounded prompt."""
        captured: dict[str, int] = {}

        class FakeDDGS:
            def __enter__(self) -> "FakeDDGS":
                return self

            def __exit__(self, *_: object) -> None:
                captured["closed"] = 1

            def text(self, query: str, max_results: int) -> list[dict[str, str]]:
                captured["max_results"] = max_results
                return [
                    {"title": "Result", "body": "Useful snippet", "href": "https://example.com"}
                    for _ in range(max_results)
                ]

        with patch.dict(sys.modules, {"ddgs": types.ModuleType("ddgs")}):
            sys.modules["ddgs"].DDGS = FakeDDGS  # type: ignore[attr-defined]
            result = self.tool.run(query="test", max_results=100)

        self.assertTrue(result.success)
        self.assertEqual(captured["max_results"], 8)
        self.assertEqual(captured["closed"], 1)
        self.assertEqual(len(result.data["results"]), 8)
        self.assertIn("Useful snippet", result.data["summary"])
        mock_browser.assert_called_once()

    @patch("webbrowser.open", return_value=True)
    def test_default_google_search(self, mock_browser: MagicMock) -> None:
        """Verifies default search site is Google with query encoded."""
        query = "python asyncio tutorial"
        result = self.tool.run(query=query)
        self.assertTrue(result.success)
        expected_url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"
        self.assertEqual(result.data["url"], expected_url)
        self.assertEqual(result.data["site"], "google")
        mock_browser.assert_called_once_with(expected_url)

    @patch("webbrowser.open", return_value=True)
    def test_youtube_search(self, mock_browser: MagicMock) -> None:
        """Verifies YouTube search URL construction with encoded query."""
        query = "lofi hip hop radio"
        result = self.tool.run(query=query, site="youtube")
        self.assertTrue(result.success)
        expected_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(query)}"
        self.assertEqual(result.data["url"], expected_url)
        self.assertEqual(result.data["site"], "youtube")
        mock_browser.assert_called_once_with(expected_url)

    @patch("webbrowser.open", return_value=True)
    def test_query_special_characters_encoded_with_quote_plus(self, mock_browser: MagicMock) -> None:
        """Verifies special characters (+, &, #, ?, etc.) are correctly encoded."""
        query = "c++ & python #1? a=b"
        result = self.tool.run(query=query, site="google")
        self.assertTrue(result.success)
        encoded_query = urllib.parse.quote_plus(query)
        self.assertIn(encoded_query, result.data["url"])
        self.assertEqual(encoded_query, "c%2B%2B+%26+python+%231%3F+a%3Db")
        mock_browser.assert_called_once_with(f"https://www.google.com/search?q={encoded_query}")

    @patch("webbrowser.open", return_value=True)
    def test_site_case_insensitivity(self, mock_browser: MagicMock) -> None:
        """Verifies site argument is case-insensitive."""
        res_google = self.tool.run(query="test", site="GOOGLE")
        self.assertTrue(res_google.success)
        self.assertEqual(res_google.data["site"], "google")

        res_yt = self.tool.run(query="test", site="YouTube")
        self.assertTrue(res_yt.success)
        self.assertEqual(res_yt.data["site"], "youtube")

    @patch("webbrowser.open")
    def test_unsupported_search_site(self, mock_browser: MagicMock) -> None:
        """Verifies unsupported search site returns ToolResult(success=False)."""
        result = self.tool.run(query="test", site="bing")
        self.assertFalse(result.success)
        self.assertIn("Unsupported search site 'bing'", result.message)
        mock_browser.assert_not_called()

    def test_invalid_or_empty_query(self) -> None:
        """Verifies empty or non-string query returns ToolResult(success=False)."""
        for invalid_query in ["", "   ", None, 99]:
            result = self.tool.run(query=invalid_query)  # type: ignore
            self.assertFalse(result.success)
            self.assertIn("query must be a non-empty string", result.message)

    @patch("webbrowser.open", side_effect=Exception("Browser subprocess error"))
    def test_webbrowser_exception_handled_safely(self, mock_browser: MagicMock) -> None:
        """Verifies search errors are trapped and return ToolResult(success=False)."""
        result = self.tool.run(query="test query")
        self.assertFalse(result.success)
        self.assertIn("Failed to execute search", result.message)

    def test_schema_validity(self) -> None:
        """Verifies SearchWebTool schema definition."""
        schema = self.tool.get_schema()
        self.assertEqual(schema["name"], "search_web")
        self.assertIn("query", schema["parameters"]["properties"])
        self.assertIn("site", schema["parameters"]["properties"])
        self.assertEqual(schema["parameters"]["required"], ["query"])
        self.assertEqual(schema["parameters"]["properties"]["site"]["default"], "google")
        self.assertEqual(schema["parameters"]["properties"]["site"]["enum"], ["google", "youtube"])


class TestToolRegistryIntegration(unittest.TestCase):
    """Tests for Tool Registry registration and execution dispatching."""

    def test_all_tools_registered(self) -> None:
        """Verifies all 5 tools are registered in TOOL_REGISTRY."""
        expected_tools = [
            "get_system_stats",
            "open_app",
            "list_directory",
            "open_website",
            "search_web",
        ]
        registered_keys = list(TOOL_REGISTRY.keys())
        for tool_name in expected_tools:
            self.assertIn(tool_name, registered_keys)

        instances = get_registered_tools()
        self.assertGreaterEqual(len(instances), 5)
        instance_names = [t.name for t in instances]
        for tool_name in expected_tools:
            self.assertIn(tool_name, instance_names)

    def test_all_tools_inherit_base_tool(self) -> None:
        """Verifies every registered tool inherits from BaseTool."""
        for name, tool in TOOL_REGISTRY.items():
            self.assertIsInstance(tool, BaseTool, f"Tool '{name}' must inherit from BaseTool")

    def test_tools_schema_generation(self) -> None:
        """Verifies schema definitions for LLM tool calling."""
        schemas = get_tools_schema()
        self.assertGreaterEqual(len(schemas), 5)
        schema_names = [s["name"] for s in schemas]
        self.assertIn("open_website", schema_names)
        self.assertIn("search_web", schema_names)
        self.assertIn("open_app", schema_names)
        self.assertIn("get_system_stats", schema_names)
        self.assertIn("list_directory", schema_names)

    @patch("webbrowser.open", return_value=True)
    def test_execute_tool_open_website(self, mock_browser: MagicMock) -> None:
        """Verifies execute_tool dispatches open_website correctly."""
        result = execute_tool("open_website", {"site": "github"})
        self.assertIsInstance(result, ToolResult)
        self.assertTrue(result.success)
        mock_browser.assert_called_once_with("https://github.com")

    @patch("webbrowser.open", return_value=True)
    def test_execute_tool_search_web(self, mock_browser: MagicMock) -> None:
        """Verifies execute_tool dispatches search_web correctly."""
        result = execute_tool("search_web", {"query": "deep learning", "site": "youtube"})
        self.assertIsInstance(result, ToolResult)
        self.assertTrue(result.success)
        mock_browser.assert_called_once_with("https://www.youtube.com/results?search_query=deep+learning")

    def test_execute_tool_case_insensitive_and_class_name(self) -> None:
        """Verifies tool lookup works case-insensitively and by class name."""
        # Class name lookup
        tool_by_class = TOOL_REGISTRY.get("SearchWebTool")
        self.assertIsNotNone(tool_by_class)
        self.assertEqual(tool_by_class.name, "search_web")

        # Case-insensitive lookup
        tool_by_case = TOOL_REGISTRY.get("OPEN_WEBSITE")
        self.assertIsNotNone(tool_by_case)
        self.assertEqual(tool_by_case.name, "open_website")

    def test_execute_unknown_tool_returns_failure(self) -> None:
        """Verifies executing unknown tool returns failure ToolResult without crashing."""
        result = execute_tool("nonexistent_tool_xyz")
        self.assertIsInstance(result, ToolResult)
        self.assertFalse(result.success)
        self.assertIn("Unknown tool", result.message)

    def test_execute_tool_invalid_argument_type(self) -> None:
        """Verifies invalid argument payload returns failure ToolResult."""
        result = execute_tool("open_website", "not_a_dict")  # type: ignore
        self.assertFalse(result.success)
        self.assertIn("must be provided as a dictionary", result.message)


class TestExistingToolsContractIntegrity(unittest.TestCase):
    """Verifies existing tools retain their interface contracts and functionality."""

    def test_get_system_stats_runs(self) -> None:
        """Verifies GetSystemStatsTool returns valid telemetry data."""
        tool = GetSystemStatsTool()
        result = tool.run()
        self.assertIsInstance(result, ToolResult)
        self.assertTrue(result.success)
        self.assertIn("cpu_usage_percent", result.data)
        self.assertIn("ram_usage_percent", result.data)
        self.assertIn("battery", result.data)

    def test_list_directory_runs(self) -> None:
        """Verifies ListDirectoryTool lists entries in current directory."""
        tool = ListDirectoryTool()
        result = tool.run(directory_path=".")
        self.assertIsInstance(result, ToolResult)
        self.assertTrue(result.success)
        self.assertIsInstance(result.data, list)


def run_all_tests() -> bool:
    """Runs the test suite and returns True if all tests passed."""
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
