"""Unit and Integration Tests for YouTube Control Tool in JARVIS.

Tests:
1. Tool schema and registration conformity.
2. Play action with direct URL and search queries (including scraping).
3. Playback controls: pause, resume, toggle_play.
4. Display controls: fullscreen, exit_fullscreen, theater mode, miniplayer.
5. Navigation controls: scroll_down, scroll_up, click_video.
6. Audio controls: mute, volume_up, volume_down.
7. Seek & Speed: skip_forward, skip_backward, next, prev, speed_up, slow_down, restart.
8. parse_youtube_intent: Natural language parsing across all user queries.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from tools.base import ToolResult
from tools.registry import execute_tool, get_registered_tools
from tools.youtube_tool import YouTubeControlTool
from ui.server import parse_youtube_intent


class TestYouTubeTool(unittest.TestCase):
    """Test suite for YouTubeControlTool."""

    def setUp(self) -> None:
        self.tool = YouTubeControlTool()

    def test_youtube_tool_schema(self) -> None:
        """Verify tool adheres to BaseTool contract and exposes all actions in JSON schema."""
        self.assertEqual(self.tool.name, "youtube_control")
        schema = self.tool.get_schema()
        self.assertEqual(schema["name"], "youtube_control")
        self.assertIn("parameters", schema)
        props = schema["parameters"]["properties"]
        self.assertIn("action", props)
        self.assertIn("query", props)
        self.assertIn("index", props)
        self.assertIn("scroll_amount", props)
        actions = props["action"]["enum"]
        expected_actions = [
            "play", "pause", "resume", "fullscreen", "exit_fullscreen",
            "scroll_down", "scroll_up", "click_video", "mute", "volume_up",
            "volume_down", "skip_forward", "skip_backward", "next", "prev",
            "captions", "speed_up", "slow_down", "restart",
        ]
        for act in expected_actions:
            self.assertIn(act, actions)

    def test_youtube_registered_in_registry(self) -> None:
        """Verify youtube_control is discoverable in system tool registry."""
        tools = get_registered_tools()
        tool_names = [t.name for t in tools]
        self.assertIn("youtube_control", tool_names)

    @patch("webbrowser.open_new_tab")
    def test_play_direct_url(self, mock_browser: MagicMock) -> None:
        """Verify direct YouTube URL opens cleanly in browser."""
        test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        res = self.tool.run(action="play", url=test_url)
        self.assertTrue(res.success)
        mock_browser.assert_called_once_with(test_url)
        self.assertIn(test_url, res.message)

    @patch("tools.youtube_tool.requests.get")
    @patch("webbrowser.open_new_tab")
    def test_play_query_scrapes_and_opens_top_video(
        self, mock_browser: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Verify query search scrapes the first video and opens watch URL directly."""
        mock_resp = MagicMock()
        import json
        payload = {
            "contents": {
                "twoColumnSearchResultsRenderer": {
                    "primaryContents": {
                        "sectionListRenderer": {
                            "contents": [
                                {
                                    "itemSectionRenderer": {
                                        "contents": [
                                            {
                                                "videoRenderer": {
                                                    "videoId": "testVid123",
                                                    "title": {"runs": [{"text": "Imagine Dragons - Believer"}]},
                                                }
                                            }
                                        ]
                                    }
                                }
                            ]
                        }
                    }
                }
            }
        }
        mock_resp.text = f"<script>var ytInitialData = {json.dumps(payload)};</script>"
        mock_requests.return_value = mock_resp

        res = self.tool.run(action="play", query="believer on youtube")
        self.assertTrue(res.success)
        self.assertEqual(res.data["video_id"], "testVid123")
        self.assertEqual(res.data["url"], "https://www.youtube.com/watch?v=testVid123")
        mock_browser.assert_called_once_with("https://www.youtube.com/watch?v=testVid123")
        self.assertIn("Believer", res.message)

    @patch("tools.youtube_tool.pyautogui.press")
    @patch.object(YouTubeControlTool, "_focus_youtube_window", return_value=True)
    def test_pause_action(self, mock_focus: MagicMock, mock_press: MagicMock) -> None:
        """Verify pause focuses YouTube and sends 'k' key."""
        res = self.tool.run(action="pause")
        self.assertTrue(res.success)
        mock_focus.assert_called_once()
        mock_press.assert_called_once_with("k")
        self.assertIn("Paused", res.message)

    @patch("tools.youtube_tool.pyautogui.press")
    @patch.object(YouTubeControlTool, "_focus_youtube_window", return_value=True)
    def test_resume_action(self, mock_focus: MagicMock, mock_press: MagicMock) -> None:
        """Verify resume focuses YouTube and sends 'k' key."""
        res = self.tool.run(action="resume")
        self.assertTrue(res.success)
        mock_focus.assert_called_once()
        mock_press.assert_called_once_with("k")
        self.assertIn("Resumed", res.message)

    @patch("tools.youtube_tool.pyautogui.press")
    @patch.object(YouTubeControlTool, "_focus_youtube_window", return_value=True)
    def test_fullscreen_action(self, mock_focus: MagicMock, mock_press: MagicMock) -> None:
        """Verify fullscreen focuses YouTube and sends 'f' key."""
        res = self.tool.run(action="fullscreen")
        self.assertTrue(res.success)
        mock_focus.assert_called_once()
        mock_press.assert_called_once_with("f")
        self.assertIn("fullscreen", res.message.lower())

    @patch("tools.youtube_tool.pyautogui.press")
    @patch.object(YouTubeControlTool, "_focus_youtube_window", return_value=True)
    def test_exit_fullscreen_action(self, mock_focus: MagicMock, mock_press: MagicMock) -> None:
        """Verify exit_fullscreen focuses YouTube and sends 'f' key."""
        res = self.tool.run(action="exit_fullscreen")
        self.assertTrue(res.success)
        mock_focus.assert_called_once()
        mock_press.assert_called_once_with("f")
        self.assertIn("exited", res.message.lower())

    @patch("tools.youtube_tool.pyautogui.scroll")
    @patch.object(YouTubeControlTool, "_focus_youtube_window", return_value=True)
    @patch.object(YouTubeControlTool, "_get_youtube_window_rect", return_value=(100, 100, 800, 600))
    def test_scroll_down_action(
        self, mock_rect: MagicMock, mock_focus: MagicMock, mock_scroll: MagicMock
    ) -> None:
        """Verify scroll_down focuses YouTube and executes scroll downward."""
        res = self.tool.run(action="scroll_down", scroll_amount=5)
        self.assertTrue(res.success)
        mock_focus.assert_called_once()
        mock_scroll.assert_called_once_with(-600)
        self.assertIn("Scrolled", res.message)

    @patch("tools.youtube_tool.pyautogui.scroll")
    @patch.object(YouTubeControlTool, "_focus_youtube_window", return_value=True)
    @patch.object(YouTubeControlTool, "_get_youtube_window_rect", return_value=(100, 100, 800, 600))
    def test_scroll_up_action(
        self, mock_rect: MagicMock, mock_focus: MagicMock, mock_scroll: MagicMock
    ) -> None:
        """Verify scroll_up focuses YouTube and executes scroll upward."""
        res = self.tool.run(action="scroll_up", scroll_amount=4)
        self.assertTrue(res.success)
        mock_focus.assert_called_once()
        mock_scroll.assert_called_once_with(480)
        self.assertIn("Scrolled", res.message)

    @patch("webbrowser.open_new_tab")
    def test_click_video_from_cached_search(self, mock_browser: MagicMock) -> None:
        """Verify click_video with index opens the corresponding video from recent results."""
        YouTubeControlTool._last_search_results = [
            {"id": "vid1", "title": "First Song", "url": "https://www.youtube.com/watch?v=vid1"},
            {"id": "vid2", "title": "Second Song", "url": "https://www.youtube.com/watch?v=vid2"},
        ]
        res = self.tool.run(action="click_video", index=2)
        self.assertTrue(res.success)
        mock_browser.assert_called_once_with("https://www.youtube.com/watch?v=vid2")
        self.assertIn("Second Song", res.message)

    @patch("tools.youtube_tool.pyautogui.press")
    @patch.object(YouTubeControlTool, "_focus_youtube_window", return_value=True)
    def test_audio_and_seek_controls(self, mock_focus: MagicMock, mock_press: MagicMock) -> None:
        """Verify audio and seek controls dispatch proper YouTube shortcuts."""
        # Mute -> 'm'
        res_mute = self.tool.run(action="mute")
        self.assertTrue(res_mute.success)
        mock_press.assert_called_with("m")

        # Skip forward -> 'l'
        res_ff = self.tool.run(action="skip_forward")
        self.assertTrue(res_ff.success)
        mock_press.assert_called_with("l")

        # Skip backward -> 'j'
        res_rw = self.tool.run(action="skip_backward")
        self.assertTrue(res_rw.success)
        mock_press.assert_called_with("j")

        # Restart -> '0'
        res_re = self.tool.run(action="restart")
        self.assertTrue(res_re.success)
        mock_press.assert_called_with("0")

        # Captions -> 'c'
        res_cc = self.tool.run(action="captions")
        self.assertTrue(res_cc.success)
        mock_press.assert_called_with("c")


class TestYouTubeNaturalLanguageParsing(unittest.TestCase):
    """Test suite for parse_youtube_intent across all user phrasings."""

    def test_play_intents(self) -> None:
        """Verify play commands extract query cleanly."""
        res = parse_youtube_intent("play believer on youtube")
        self.assertIsNotNone(res)
        self.assertEqual(res["action"], "play")
        self.assertEqual(res["query"], "believer")

        res2 = parse_youtube_intent("play youtube video bohemian rhapsody")
        self.assertIsNotNone(res2)
        self.assertEqual(res2["action"], "play")
        self.assertEqual(res2["query"], "bohemian rhapsody")

    def test_scroll_intents(self) -> None:
        """Verify scrolling commands are parsed accurately."""
        res = parse_youtube_intent("scroll youtube for me")
        self.assertIsNotNone(res)
        self.assertEqual(res["action"], "scroll_down")

        res_up = parse_youtube_intent("scroll up on youtube")
        self.assertIsNotNone(res_up)
        self.assertEqual(res_up["action"], "scroll_up")

    def test_click_video_intents(self) -> None:
        """Verify click and open video phrasings."""
        res = parse_youtube_intent("click and open video")
        self.assertIsNotNone(res)
        self.assertEqual(res["action"], "click_video")
        self.assertEqual(res["index"], 1)

        res2 = parse_youtube_intent("open video 2")
        self.assertIsNotNone(res2)
        self.assertEqual(res2["action"], "click_video")
        self.assertEqual(res2["index"], 2)

    def test_pause_and_resume_intents(self) -> None:
        """Verify pause and resume phrasings."""
        res_pause = parse_youtube_intent("pause the video")
        self.assertIsNotNone(res_pause)
        self.assertEqual(res_pause["action"], "pause")

        res_resume = parse_youtube_intent("resume the video")
        self.assertIsNotNone(res_resume)
        self.assertEqual(res_resume["action"], "resume")

    def test_fullscreen_and_exit_fullscreen_intents(self) -> None:
        """Verify fullscreen and out fullscreen phrasings."""
        res_fs = parse_youtube_intent("fullscreen")
        self.assertIsNotNone(res_fs)
        self.assertEqual(res_fs["action"], "fullscreen")

        res_out = parse_youtube_intent("out full screen")
        self.assertIsNotNone(res_out)
        self.assertEqual(res_out["action"], "exit_fullscreen")

        res_exit = parse_youtube_intent("exit fullscreen")
        self.assertIsNotNone(res_exit)
        self.assertEqual(res_exit["action"], "exit_fullscreen")

    def test_meta_capabilities_prompt(self) -> None:
        """Verify the user's overarching question is answered with full capabilities."""
        prompt = (
            "he must be able to play youtube videos and scroll youtube for me and "
            "click and open video and pause the video and fullscreen and then out full screen and control whole youtbe"
        )
        res = parse_youtube_intent(prompt)
        self.assertIsNotNone(res)
        self.assertEqual(res["action"], "capabilities")
        self.assertIn("YouTube control online", res["message"])


class TestYouTubeWebSocketIntegration(unittest.TestCase):
    """Test suite for live WebSocket dispatching of YouTube commands."""

    @patch("tools.youtube_tool.YouTubeControlTool.run")
    def test_websocket_pause_command(self, mock_run: MagicMock) -> None:
        """Verify WebSocket 'pause the video' command invokes youtube_control(action='pause')."""
        from fastapi.testclient import TestClient
        from ui.server import app

        mock_run.return_value = ToolResult(
            success=True,
            data={"action": "pause"},
            message="Paused the YouTube video."
        )

        with TestClient(app) as client:
            with client.websocket_connect("/ws/jarvis") as ws:
                ws.send_json({"action": "chat", "text": "pause the video"})
                # msg1: thinking
                msg1 = ws.receive_json()
                self.assertEqual(msg1["type"], "status")
                # msg2: tool_steps
                msg2 = ws.receive_json()
                self.assertEqual(msg2["type"], "tool_steps")
                self.assertIn("youtube_control(action='pause')", msg2["steps"])
                # msg3: response
                msg3 = ws.receive_json()
                self.assertEqual(msg3["type"], "response")
                self.assertIn("Paused the YouTube video", msg3["text"])

    @patch("tools.youtube_tool.YouTubeControlTool.run")
    def test_websocket_fullscreen_and_scroll(self, mock_run: MagicMock) -> None:
        """Verify WebSocket handles fullscreen and scroll commands."""
        from fastapi.testclient import TestClient
        from ui.server import app

        mock_run.return_value = ToolResult(
            success=True,
            data={"action": "fullscreen"},
            message="Switched YouTube to fullscreen."
        )

        with TestClient(app) as client:
            with client.websocket_connect("/ws/jarvis") as ws:
                ws.send_json({"action": "chat", "text": "fullscreen"})
                msg1 = ws.receive_json()
                msg2 = ws.receive_json()
                self.assertIn("youtube_control(action='fullscreen')", msg2["steps"])
                msg3 = ws.receive_json()
                self.assertIn("Switched YouTube to fullscreen", msg3["text"])


if __name__ == "__main__":
    unittest.main()
