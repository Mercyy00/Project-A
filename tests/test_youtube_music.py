"""
Unit and integration tests for YouTubeMusicTool and YouTube Music intent parsing.
Author: Abhijit (System & Automation Engineer)
"""

import unittest
from unittest.mock import MagicMock, patch

from tools.youtube_music_tool import YouTubeMusicTool
from tools.base import ToolResult
from ui.server import parse_youtube_music_intent


class TestYouTubeMusicTool(unittest.TestCase):
    def setUp(self) -> None:
        self.tool = YouTubeMusicTool()

    def test_schema_validity(self) -> None:
        """Verify schema defines all required YouTube Music actions."""
        schema = self.tool.get_schema()
        self.assertEqual(schema["name"], "youtube_music_control")
        actions = schema["parameters"]["properties"]["action"]["enum"]
        expected = [
            "play", "pause", "resume", "toggle_play", "next_song", "prev_song",
            "lyrics", "reload", "search", "open", "volume_up", "volume_down",
            "mute", "shuffle", "repeat", "like", "dislike", "seek_forward", "seek_backward"
        ]
        for act in expected:
            self.assertIn(act, actions, f"Action {act} missing from schema")

    @patch.object(YouTubeMusicTool, "_focus_music_window", return_value=True)
    @patch.object(YouTubeMusicTool, "_send_key", return_value=True)
    @patch.object(YouTubeMusicTool, "_send_hotkey", return_value=True)
    def test_next_and_previous_song(self, mock_hotkey: MagicMock, mock_key: MagicMock, mock_focus: MagicMock) -> None:
        """Verify next_song and prev_song invoke correct keys and hotkeys."""
        res_next = self.tool.run(action="next_song")
        self.assertTrue(res_next.success)
        mock_key.assert_called_with("j")
        mock_hotkey.assert_called_with("shift", "n")

        res_prev = self.tool.run(action="prev_song")
        self.assertTrue(res_prev.success)
        mock_key.assert_called_with("k")
        mock_hotkey.assert_called_with("shift", "p")

    @patch.object(YouTubeMusicTool, "_focus_music_window", return_value=True)
    @patch.object(YouTubeMusicTool, "_send_key", return_value=True)
    def test_lyrics_section(self, mock_key: MagicMock, mock_focus: MagicMock) -> None:
        """Verify lyrics action sends 'e' key."""
        res = self.tool.run(action="lyrics")
        self.assertTrue(res.success)
        mock_key.assert_called_with("e")

    @patch.object(YouTubeMusicTool, "_focus_music_window", return_value=True)
    @patch.object(YouTubeMusicTool, "_send_hotkey", return_value=True)
    def test_reload_music_tab(self, mock_hotkey: MagicMock, mock_focus: MagicMock) -> None:
        """Verify reload sends Ctrl+R to music tab."""
        res = self.tool.run(action="reload")
        self.assertTrue(res.success)
        mock_hotkey.assert_called_with("ctrl", "r")

    @patch("webbrowser.open")
    def test_play_direct_video_id(self, mock_web_open: MagicMock) -> None:
        """Verify direct video_id opens music.youtube.com/watch?v=..."""
        res = self.tool.run(action="play", video_id="dQw4w9WgXcQ")
        self.assertTrue(res.success)
        mock_web_open.assert_called_with("https://music.youtube.com/watch?v=dQw4w9WgXcQ")

    @patch("webbrowser.open")
    def test_search_song(self, mock_web_open: MagicMock) -> None:
        """Verify search opens music.youtube.com/search?q=..."""
        res = self.tool.run(action="search", query="Starboy The Weeknd")
        self.assertTrue(res.success)
        self.assertIn("search?q=Starboy+The+Weeknd", mock_web_open.call_args[0][0])


class TestYouTubeMusicIntentParsing(unittest.TestCase):
    def test_next_and_previous_song_intents(self) -> None:
        """Verify next song and previous song intents."""
        i_next = parse_youtube_music_intent("play next song")
        self.assertIsNotNone(i_next)
        self.assertEqual(i_next["action"], "next_song")

        i_next2 = parse_youtube_music_intent("next song")
        self.assertIsNotNone(i_next2)
        self.assertEqual(i_next2["action"], "next_song")

        i_prev = parse_youtube_music_intent("play previous song")
        self.assertIsNotNone(i_prev)
        self.assertEqual(i_prev["action"], "prev_song")

        i_prev2 = parse_youtube_music_intent("prev song")
        self.assertIsNotNone(i_prev2)
        self.assertEqual(i_prev2["action"], "prev_song")

    def test_lyrics_intent(self) -> None:
        """Verify opening lyrics section intent."""
        i_lyr = parse_youtube_music_intent("open lyrics section")
        self.assertIsNotNone(i_lyr)
        self.assertEqual(i_lyr["action"], "lyrics")

        i_lyr2 = parse_youtube_music_intent("show lyrics")
        self.assertIsNotNone(i_lyr2)
        self.assertEqual(i_lyr2["action"], "lyrics")

    def test_reload_music_tab_intent(self) -> None:
        """Verify reload music tab intent."""
        i_reload = parse_youtube_music_intent("reload music tab")
        self.assertIsNotNone(i_reload)
        self.assertEqual(i_reload["action"], "reload")

        i_reload2 = parse_youtube_music_intent("refresh youtube music")
        self.assertIsNotNone(i_reload2)
        self.assertEqual(i_reload2["action"], "reload")

    def test_search_song_intent(self) -> None:
        """Verify search song intent."""
        i_search = parse_youtube_music_intent("search song bohemian rhapsody")
        self.assertIsNotNone(i_search)
        self.assertEqual(i_search["action"], "search")
        self.assertEqual(i_search["query"], "bohemian rhapsody")

        i_search2 = parse_youtube_music_intent("search believer on youtube music")
        self.assertIsNotNone(i_search2)
        self.assertEqual(i_search2["action"], "search")
        self.assertEqual(i_search2["query"], "believer")

        i_search3 = parse_youtube_music_intent("search for faded in youtube music")
        self.assertIsNotNone(i_search3)
        self.assertEqual(i_search3["action"], "search")
        self.assertEqual(i_search3["query"], "faded")

    def test_play_song_intent(self) -> None:
        """Verify play song intent."""
        i_play = parse_youtube_music_intent("play song blinding lights")
        self.assertIsNotNone(i_play)
        self.assertEqual(i_play["action"], "play")
        self.assertEqual(i_play["query"], "blinding lights")

        i_play2 = parse_youtube_music_intent("play believer on youtube music")
        self.assertIsNotNone(i_play2)
        self.assertEqual(i_play2["action"], "play")
        self.assertEqual(i_play2["query"], "believer")

        i_play3 = parse_youtube_music_intent("play starboy on yt music")
        self.assertIsNotNone(i_play3)
        self.assertEqual(i_play3["action"], "play")
        self.assertEqual(i_play3["query"], "starboy")

        i_play4 = parse_youtube_music_intent("play songs on youtube music")
        self.assertIsNotNone(i_play4)
        self.assertEqual(i_play4["action"], "play")
        self.assertEqual(i_play4["query"], "top hit songs")

    def test_meta_capabilities(self) -> None:
        """Verify capability questions return structured summary."""
        i = parse_youtube_music_intent("automate full youtube music")
        self.assertIsNotNone(i)
        self.assertEqual(i["action"], "capabilities")
        self.assertIn("YouTube Music automation", i["message"])


if __name__ == "__main__":
    unittest.main()
