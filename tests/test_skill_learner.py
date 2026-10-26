"""
Unit and integration tests for Skill Learner, Adaptive Memory, and Personalized Speaking.
Author: Abhijit (System & Automation Engineer)
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from memory.manager import PreferenceManager, sanitize_memory_value
from tools.skill_tool import SkillLearnerTool
from tools.base import ToolResult
from ui.server import (
    parse_skill_learner_intent,
    parse_memory_intent,
    _generate_response,
    current_user_state,
)


class TestPreferenceManagerSkillsAndFacts(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.temp_file.close()
        self.mgr = PreferenceManager(storage_path=Path(self.temp_file.name))

    def tearDown(self) -> None:
        if os.path.exists(self.temp_file.name):
            try:
                os.remove(self.temp_file.name)
            except OSError:
                pass

    def test_sanitize_memory_value(self) -> None:
        """Verify prompt injection tokens and control chars are defanged."""
        self.assertEqual(sanitize_memory_value("system: do bad thing"), "[system]: do bad thing")
        self.assertEqual(sanitize_memory_value("hello\n\rworld"), "hello world")
        self.assertEqual(sanitize_memory_value("<<<inject>>>"), "<<inject>>")

    def test_add_and_recall_facts(self) -> None:
        """Verify facts can be stored, retrieved, and deleted."""
        self.mgr.add_fact("favorite_browser", "Brave")
        self.assertEqual(self.mgr.get_fact("favorite_browser"), "Brave")

        all_facts = self.mgr.get_all_facts()
        self.assertIn("favorite_browser", all_facts)
        self.assertEqual(all_facts["favorite_browser"], "Brave")

        self.assertTrue(self.mgr.remove_fact("favorite_browser"))
        self.assertIsNone(self.mgr.get_fact("favorite_browser"))

    def test_add_and_match_skills(self) -> None:
        """Verify skills can be registered and matched by trigger or name."""
        skill = self.mgr.add_skill(
            name="morning_routine",
            trigger="morning routine",
            steps="open Brave and open YouTube Music",
            description="Start morning flow",
        )
        self.assertEqual(skill["name"], "morning_routine")
        self.assertEqual(skill["trigger"], "morning routine")

        # Find by name
        found = self.mgr.get_skill("morning_routine")
        self.assertIsNotNone(found)
        self.assertEqual(found["name"], "morning_routine")

        # Find by trigger
        found_trig = self.mgr.get_skill("morning routine")
        self.assertIsNotNone(found_trig)

        # Match in user query
        matched = self.mgr.find_matching_skill("please run morning routine now")
        self.assertIsNotNone(matched)
        self.assertEqual(matched["name"], "morning_routine")

        # List skills
        skills = self.mgr.list_skills()
        self.assertEqual(len(skills), 1)

        # Remove skill
        self.assertTrue(self.mgr.remove_skill("morning_routine"))
        self.assertEqual(len(self.mgr.list_skills()), 0)

    def test_adaptive_prompt_context(self) -> None:
        """Verify adaptive context includes personalized user name, facts, and skills."""
        self.mgr.set_preference("user_name", "Boss")
        self.mgr.set_preference("speaking_style", "ultra-concise and witty")
        self.mgr.add_fact("profession", "Python Architect")
        self.mgr.add_skill(
            name="deep_work",
            trigger="deep work",
            steps="set volume to 20 and open PyCharm",
            description="Focus session",
        )

        ctx = self.mgr.get_adaptive_prompt_context()
        self.assertIn("Boss", ctx)
        self.assertIn("ultra-concise and witty", ctx)
        self.assertIn("Profession: Python Architect", ctx)
        self.assertIn("deep_work", ctx)
        self.assertIn("PERSONALIZATION MANDATE", ctx)


class TestSkillLearnerTool(unittest.TestCase):
    def setUp(self) -> None:
        self.tool = SkillLearnerTool()

    def test_schema_validity(self) -> None:
        """Verify schema defines all required actions."""
        schema = self.tool.get_schema()
        self.assertEqual(schema["name"], "skill_learner")
        actions = schema["parameters"]["properties"]["action"]["enum"]
        expected = [
            "learn_skill", "execute_skill", "list_skills", "forget_skill",
            "remember_fact", "recall_facts", "forget_fact",
            "set_speaking_style", "set_user_name"
        ]
        for act in expected:
            self.assertIn(act, actions)

    def test_learn_and_list_skills(self) -> None:
        """Verify learning a new skill and listing it."""
        res = self.tool.run(
            action="learn_skill",
            skill_name="code_sprint",
            trigger="code sprint",
            instructions="open vscode and set volume to 30",
        )
        self.assertTrue(res.success)
        self.assertIn("code_sprint", res.message)

        res_list = self.tool.run(action="list_skills")
        self.assertTrue(res_list.success)
        self.assertIn("code_sprint", res_list.message)

    def test_remember_and_recall_facts(self) -> None:
        """Verify storing and recalling personal facts."""
        res_rem = self.tool.run(
            action="remember_fact",
            fact_key="favorite_editor",
            fact_value="VS Code",
        )
        self.assertTrue(res_rem.success)
        self.assertIn("Favorite Editor is VS Code", res_rem.message)

        res_rec = self.tool.run(action="recall_facts")
        self.assertTrue(res_rec.success)
        self.assertIn("Favorite Editor: VS Code", res_rec.message)

    def test_set_user_name_and_speaking_style(self) -> None:
        """Verify custom naming and speaking style adaptation."""
        res_name = self.tool.run(action="set_user_name", user_name="Captain")
        self.assertTrue(res_name.success)
        self.assertIn("Captain", res_name.message)

        res_style = self.tool.run(action="set_speaking_style", style="sharp and witty British cadence")
        self.assertTrue(res_style.success)
        self.assertIn("sharp and witty British cadence", res_style.message)


class TestSkillAndMemoryIntentParsing(unittest.TestCase):
    def test_learn_skill_intent(self) -> None:
        """Verify skill learning natural language parsing."""
        i1 = parse_skill_learner_intent("learn a new skill morning routine: open Brave, open YouTube Music, and set volume to 50")
        self.assertIsNotNone(i1)
        self.assertEqual(i1["action"], "learn_skill")
        self.assertEqual(i1["skill_name"], "morning routine")
        self.assertIn("open Brave", i1["instructions"])

        i2 = parse_skill_learner_intent("when I say start work, open chrome and open notes")
        self.assertIsNotNone(i2)
        self.assertEqual(i2["action"], "learn_skill")
        self.assertEqual(i2["trigger"], "start work")

    def test_list_skills_intent(self) -> None:
        """Verify list skills intent."""
        i = parse_skill_learner_intent("what skills have you learned")
        self.assertIsNotNone(i)
        self.assertEqual(i["action"], "list_skills")

    def test_remember_facts_intent(self) -> None:
        """Verify remember facts intents."""
        i1 = parse_memory_intent("remember that my favorite browser is Brave")
        self.assertIsNotNone(i1)
        self.assertEqual(i1["action"], "remember_fact")
        self.assertEqual(i1["fact_key"], "favorite_browser")
        self.assertEqual(i1["fact_value"], "Brave")

        i2 = parse_memory_intent("remember that I am a Python developer")
        self.assertIsNotNone(i2)
        self.assertEqual(i2["action"], "remember_fact")
        self.assertEqual(i2["fact_key"], "profession")
        self.assertEqual(i2["fact_value"], "Python developer")

        i3 = parse_memory_intent("remember that my birthday is May 14th")
        self.assertIsNotNone(i3)
        self.assertEqual(i3["action"], "remember_fact")
        self.assertEqual(i3["fact_key"], "birthday")
        self.assertEqual(i3["fact_value"], "May 14th")

    def test_call_me_and_tone_intent(self) -> None:
        """Verify call me and tone change intents."""
        i_name = parse_memory_intent("call me Boss")
        self.assertIsNotNone(i_name)
        self.assertEqual(i_name["action"], "set_user_name")
        self.assertEqual(i_name["user_name"], "Boss")

        i_style = parse_memory_intent("speak in Hinglish")
        self.assertIsNotNone(i_style)
        self.assertEqual(i_style["action"], "set_speaking_style")
        self.assertEqual(i_style["style"], "Hinglish")

    def test_recall_facts_intent(self) -> None:
        """Verify what do you remember about me intent."""
        i = parse_memory_intent("what do you remember about me")
        self.assertIsNotNone(i)
        self.assertEqual(i["action"], "recall_facts")


class TestAdaptiveSpeakingResponse(unittest.IsolatedAsyncioTestCase):
    async def test_adaptive_speaking_name_change(self) -> None:
        """Verify when user tells JARVIS to call them Boss, responses immediately address them as Boss."""
        # 1. Set name to Boss
        resp1 = await _generate_response("call me Boss")
        self.assertIn("Boss", resp1)

        # 2. Tell JARVIS to remember favorite browser
        resp2 = await _generate_response("remember that my favorite browser is Brave")
        self.assertIn("Boss", resp2)
        self.assertIn("Brave", resp2)

        # 3. Ask what JARVIS remembers
        resp3 = await _generate_response("what do you remember about me")
        self.assertIn("Boss", resp3)
        self.assertIn("Brave", resp3)


if __name__ == "__main__":
    unittest.main()
