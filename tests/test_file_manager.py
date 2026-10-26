"""
Unit and integration tests for FileManagerTool and File Manager intent parsing.
Author: Abhijit (System & Automation Engineer)
"""

import os
import unittest
from unittest.mock import MagicMock, patch

from tools.file_manager_tool import FileManagerTool, _format_size
from tools.base import ToolResult
from ui.server import parse_file_manager_intent


class TestFileManagerTool(unittest.TestCase):
    def setUp(self) -> None:
        self.tool = FileManagerTool()

    def test_schema_validity(self) -> None:
        """Verify schema defines all required file manager actions."""
        schema = self.tool.get_schema()
        self.assertEqual(schema["name"], "file_manager_control")
        actions = schema["parameters"]["properties"]["action"]["enum"]
        expected = [
            "list_drives", "open_drive", "open_folder", "look_at_folder",
            "search_folders", "create_folder", "show_in_explorer"
        ]
        for act in expected:
            self.assertIn(act, actions, f"Action {act} missing from schema")

    def test_format_size(self) -> None:
        """Verify byte formatting logic."""
        self.assertEqual(_format_size(500), "500 B")
        self.assertEqual(_format_size(2048), "2.0 KB")
        self.assertEqual(_format_size(5 * 1024 * 1024), "5.0 MB")
        self.assertEqual(_format_size(10 * 1024 * 1024 * 1024), "10.00 GB")

    def test_resolve_path(self) -> None:
        """Verify folder aliases and paths resolve accurately."""
        downloads = self.tool.resolve_path("downloads")
        self.assertTrue(downloads.endswith("Downloads"))

        desktop = self.tool.resolve_path("desktop")
        self.assertTrue(desktop.endswith("Desktop"))

        c_drive = self.tool.resolve_path("c drive")
        self.assertEqual(c_drive, "C:\\")

        d_drive = self.tool.resolve_path("drive d")
        self.assertEqual(d_drive, "D:\\")

    def test_list_drives(self) -> None:
        """Verify list_drives identifies real system drives."""
        res = self.tool.run(action="list_drives")
        self.assertTrue(res.success)
        self.assertGreater(res.data.get("count", 0), 0)
        self.assertIn("active drive", res.message)

    @patch.object(FileManagerTool, "_open_in_windows_explorer", return_value=True)
    def test_open_drive(self, mock_explorer: MagicMock) -> None:
        """Verify open_drive invokes explorer for drive letter."""
        res = self.tool.run(action="open_drive", drive="C:")
        self.assertTrue(res.success)
        mock_explorer.assert_called_with("C:\\")

    @patch.object(FileManagerTool, "_open_in_windows_explorer", return_value=True)
    def test_open_folder(self, mock_explorer: MagicMock) -> None:
        """Verify open_folder resolves and opens a valid directory."""
        cwd = os.getcwd()
        res = self.tool.run(action="open_folder", folder_path=cwd)
        self.assertTrue(res.success)
        mock_explorer.assert_called_with(cwd)

    def test_look_at_folder_workspace(self) -> None:
        """Verify look_at_folder inspects current project workspace."""
        res = self.tool.run(action="look_at_folder", folder_path=".")
        self.assertTrue(res.success)
        data = res.data
        self.assertIn("subfolders_count", data)
        self.assertIn("files_count", data)
        self.assertGreater(data["subfolders_count"], 0)
        # Check that core, tools, or ui are in subfolder list
        subfolder_names = [s["name"] for s in data["subfolders"]]
        self.assertTrue(any(f in subfolder_names for f in ("core", "tools", "ui", "voice")))

    def test_search_folders_workspace(self) -> None:
        """Verify search_folders finds directories matching pattern."""
        cwd = os.getcwd()
        res = self.tool.run(action="search_folders", query="voice", root_path=cwd)
        self.assertTrue(res.success)
        matches = res.data.get("matches", [])
        match_names = [m["name"].lower() for m in matches]
        self.assertIn("voice", match_names)


class TestFileManagerIntentParsing(unittest.TestCase):
    def test_list_drives_intent(self) -> None:
        """Verify list drives intent."""
        i1 = parse_file_manager_intent("list drives")
        self.assertIsNotNone(i1)
        self.assertEqual(i1["action"], "list_drives")

        i2 = parse_file_manager_intent("show drives")
        self.assertIsNotNone(i2)
        self.assertEqual(i2["action"], "list_drives")

    def test_open_drive_intent(self) -> None:
        """Verify open specific drive intent."""
        i_c = parse_file_manager_intent("open c drive")
        self.assertIsNotNone(i_c)
        self.assertEqual(i_c["action"], "open_drive")
        self.assertEqual(i_c["drive"], "C:\\")

        i_d = parse_file_manager_intent("open d drive")
        self.assertIsNotNone(i_d)
        self.assertEqual(i_d["action"], "open_drive")
        self.assertEqual(i_d["drive"], "D:\\")

    def test_look_at_folders_intent(self) -> None:
        """Verify look at folders intent."""
        i1 = parse_file_manager_intent("look at folders")
        self.assertIsNotNone(i1)
        self.assertEqual(i1["action"], "look_at_folder")

        i2 = parse_file_manager_intent("look at folder Project - A")
        self.assertIsNotNone(i2)
        self.assertEqual(i2["action"], "look_at_folder")
        self.assertEqual(i2["folder_path"], "Project - A")

    def test_search_folders_intent(self) -> None:
        """Verify search folders intent."""
        i1 = parse_file_manager_intent("search folders project")
        self.assertIsNotNone(i1)
        self.assertEqual(i1["action"], "search_folders")
        self.assertEqual(i1["query"], "project")

        i2 = parse_file_manager_intent("find folders python")
        self.assertIsNotNone(i2)
        self.assertEqual(i2["action"], "search_folders")
        self.assertEqual(i2["query"], "python")

    def test_open_folder_intent(self) -> None:
        """Verify open folder and folder aliases intents."""
        i1 = parse_file_manager_intent("open downloads")
        self.assertIsNotNone(i1)
        self.assertEqual(i1["action"], "open_folder")
        self.assertEqual(i1["folder_path"], "downloads")

        i2 = parse_file_manager_intent("open folder my_work")
        self.assertIsNotNone(i2)
        self.assertEqual(i2["action"], "open_folder")
        self.assertEqual(i2["folder_path"], "my_work")

    def test_meta_capabilities(self) -> None:
        """Verify capability questions return structured summary."""
        i = parse_file_manager_intent("handle my whole file manager")
        self.assertIsNotNone(i)
        self.assertEqual(i["action"], "capabilities")
        self.assertIn("File Explorer automation", i["message"])


if __name__ == "__main__":
    unittest.main()
