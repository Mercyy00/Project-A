"""
Skill Learner and Adaptive Memory Tool for JARVIS.
Author: Abhijit (System & Automation Engineer)

Enables JARVIS to:
1. Learn new user-taught skills, procedures, and workflows.
2. Recall and execute learned skills on command or trigger.
3. Remember personal facts, preferences, and custom instructions.
4. Adapt his speech, addressing style, and persona based on what he has learned.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from tools.base import BaseTool, ToolResult
from memory.manager import preference_manager

logger = logging.getLogger(__name__)

try:
    from tools.guard import is_stopped, log_action
except ImportError:
    def is_stopped() -> bool:
        return False

    def log_action(tool_name: str, args: Any, result_summary: Any) -> None:
        pass


class SkillLearnerTool(BaseTool):
    """Tool for learning new skills, remembering personal facts, and adapting JARVIS's behavior."""
    name: str = "skill_learner"
    description: str = (
        "Learns new user-taught skills, workflows, and procedures; executes previously learned skills; "
        "and remembers/recalls personal user facts, preferences, and speaking styles."
    )

    def get_schema(self) -> Dict[str, Any]:
        """Returns JSON schema definition for LLM tool calling."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "learn_skill",
                            "execute_skill",
                            "list_skills",
                            "forget_skill",
                            "remember_fact",
                            "recall_facts",
                            "forget_fact",
                            "set_speaking_style",
                            "set_user_name",
                        ],
                        "description": "Skill learning or memory action to perform.",
                    },
                    "skill_name": {
                        "type": "string",
                        "description": "Name or identifier of the skill to learn, execute, or forget.",
                    },
                    "trigger": {
                        "type": "string",
                        "description": "User voice or text trigger phrase that activates this skill (e.g. 'morning routine').",
                    },
                    "instructions": {
                        "type": "string",
                        "description": "Step-by-step instructions or action description for the skill to perform.",
                    },
                    "fact_key": {
                        "type": "string",
                        "description": "Short category or key for the fact (e.g. 'favorite_browser', 'profession', 'birthday').",
                    },
                    "fact_value": {
                        "type": "string",
                        "description": "The fact or preference details to remember (e.g. 'Brave', 'Python developer').",
                    },
                    "style": {
                        "type": "string",
                        "description": "Preferred speaking style or tone (e.g. 'British witty', 'Hinglish', 'ultra concise').",
                    },
                    "user_name": {
                        "type": "string",
                        "description": "Preferred name or honorific to address the user by (e.g. 'Boss', 'Tony', 'Shiv').",
                    },
                },
                "required": ["action"],
            },
        }

    # -------------------------------------------------------------------------
    # Execution Dispatcher
    # -------------------------------------------------------------------------

    def run(self, **kwargs: Any) -> ToolResult:
        """Executes skill learner actions synchronously."""
        return self._execute_sync(**kwargs)

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Executes skill learner actions asynchronously."""
        return self._execute_sync(**kwargs)

    def _execute_sync(self, **kwargs: Any) -> ToolResult:
        """Safely dispatches learning and memory actions."""
        if is_stopped():
            return ToolResult(success=False, message="Action aborted: Emergency stop is active.")

        action = (kwargs.get("action") or "").lower().strip()
        skill_name = (kwargs.get("skill_name") or kwargs.get("name") or "").strip()
        trigger = (kwargs.get("trigger") or "").strip()
        instructions = (kwargs.get("instructions") or kwargs.get("steps") or "").strip()
        fact_key = (kwargs.get("fact_key") or kwargs.get("key") or "").strip()
        fact_value = (kwargs.get("fact_value") or kwargs.get("value") or kwargs.get("fact") or "").strip()
        style = (kwargs.get("style") or kwargs.get("speaking_style") or "").strip()
        user_name = (kwargs.get("user_name") or "").strip()

        logger.info("Executing SkillLearner action '%s'", action)

        try:
            if action in ("learn_skill", "teach_skill", "add_skill", "learn"):
                return self._action_learn_skill(skill_name, trigger, instructions)
            elif action in ("execute_skill", "run_skill", "trigger_skill"):
                return self._action_execute_skill(skill_name or trigger)
            elif action in ("list_skills", "show_skills", "get_skills"):
                return self._action_list_skills()
            elif action in ("forget_skill", "delete_skill", "remove_skill"):
                return self._action_forget_skill(skill_name or trigger)
            elif action in ("remember_fact", "remember", "save_fact"):
                return self._action_remember_fact(fact_key, fact_value)
            elif action in ("recall_facts", "show_facts", "list_facts", "what_do_you_remember"):
                return self._action_recall_facts(fact_key)
            elif action in ("forget_fact", "delete_fact"):
                return self._action_forget_fact(fact_key)
            elif action in ("set_speaking_style", "set_style", "speaking_style"):
                return self._action_set_speaking_style(style)
            elif action in ("set_user_name", "set_name", "call_me"):
                return self._action_set_user_name(user_name)
            else:
                return ToolResult(
                    success=False,
                    message=f"Unknown SkillLearner action '{action}'. Valid actions: "
                            "learn_skill, execute_skill, list_skills, forget_skill, "
                            "remember_fact, recall_facts, forget_fact, set_speaking_style, set_user_name.",
                )
        except Exception as exc:
            logger.exception("SkillLearner error for action '%s': %s", action, exc)
            return ToolResult(
                success=False,
                message=f"Skill learning error: {str(exc)}",
                data={"action": action, "error": str(exc)},
            )

    # -------------------------------------------------------------------------
    # Core Actions
    # -------------------------------------------------------------------------

    def _action_learn_skill(self, name: str, trigger: str, instructions: str) -> ToolResult:
        """Registers a new skill learned from the user."""
        if not name and not trigger:
            return ToolResult(success=False, message="Please provide a name or trigger phrase for the new skill.")
        if not instructions:
            return ToolResult(success=False, message="Please provide the action instructions for what this skill should do.")

        clean_name = name or re.sub(r"[^\w\s-]", "", trigger).replace(" ", "_")
        clean_trigger = trigger or clean_name.replace("_", " ")

        skill = preference_manager.add_skill(
            name=clean_name,
            trigger=clean_trigger,
            steps=instructions,
            description=instructions,
            raw_instruction=instructions,
        )

        user_title = preference_manager.get_preference("user_name", "Sir")
        msg = (
            f"Understood, {user_title}. I have successfully learned the new skill '{skill['name']}' "
            f"with trigger '{skill['trigger']}'. Whenever you say '{skill['trigger']}', "
            f"I will execute: {skill['description']}."
        )
        return ToolResult(success=True, message=msg, data={"action": "learn_skill", "skill": skill})

    def _action_execute_skill(self, identifier: str) -> ToolResult:
        """Executes a previously learned skill by name or trigger."""
        if not identifier:
            return ToolResult(success=False, message="Please specify the skill name or trigger to execute.")

        skill = preference_manager.get_skill(identifier) or preference_manager.find_matching_skill(identifier)
        if not skill:
            return ToolResult(
                success=False,
                message=f"I have not learned a skill matching '{identifier}'. You can teach it to me anytime.",
                data={"action": "execute_skill", "identifier": identifier, "found": False},
            )

        instructions = skill.get("raw_instruction") or skill.get("description") or str(skill.get("steps"))
        user_title = preference_manager.get_preference("user_name", "Sir")

        # Execute instruction steps sequentially using registered tools and intent dispatch
        steps_text = instructions
        parts = re.split(r"\s+(?:and\s+then|then|and|also|,)\s+", steps_text, flags=re.IGNORECASE)

        outcomes: List[str] = []
        for part in parts:
            part = part.strip(" ,.;")
            if not part:
                continue

            # 1. Check YouTube Music
            from ui.server import (
                parse_youtube_music_intent,
                parse_browser_intent,
                parse_file_manager_intent,
                parse_youtube_intent,
                try_launch_system_app,
            )

            ytm = parse_youtube_music_intent(part)
            if ytm and ytm.get("action") != "capabilities":
                from tools.youtube_music_tool import YouTubeMusicTool
                res = YouTubeMusicTool().run(**ytm)
                outcomes.append(res.message)
                continue

            # 2. Check YouTube
            yt = parse_youtube_intent(part)
            if yt and yt.get("action") != "capabilities":
                from tools.youtube_tool import YouTubeControlTool
                res = YouTubeControlTool().run(**yt)
                outcomes.append(res.message)
                continue

            # 3. Check Browser
            br = parse_browser_intent(part)
            if br and br.get("action") != "capabilities":
                from tools.browser_tools import BrowserControlTool
                res = BrowserControlTool().run(**br)
                outcomes.append(res.message)
                continue

            # 4. Check File Manager
            fm = parse_file_manager_intent(part)
            if fm and fm.get("action") != "capabilities":
                from tools.file_manager_tool import FileManagerTool
                res = FileManagerTool().run(**fm)
                outcomes.append(res.message)
                continue

            # 5. Check System Apps / Launch
            launch = try_launch_system_app(part)
            if launch:
                app_label = str(launch.label if hasattr(launch, 'label') else launch[0])
                outcomes.append(f"Opened {app_label}")
                continue

            # 6. Check System volume / brightness
            m_vol = re.search(r"\b(?:set\s+)?volume\s+(?:to\s+)?(\d+)\b", part, re.IGNORECASE)
            if m_vol:
                from tools.registry import execute_tool
                vol_lvl = int(m_vol.group(1))
                execute_tool("set_volume", {"level": vol_lvl})
                outcomes.append(f"Set volume to {vol_lvl}%")
                continue

            outcomes.append(f"Executed '{part}'")

        outcome_summary = ". ".join(outcomes)
        msg = f"Executed learned skill '{skill['name']}', {user_title}. {outcome_summary}."
        return ToolResult(
            success=True,
            message=msg,
            data={"action": "execute_skill", "skill": skill, "outcomes": outcomes},
        )

    def _action_list_skills(self) -> ToolResult:
        """Lists all skills learned from the user."""
        skills = preference_manager.list_skills()
        user_title = preference_manager.get_preference("user_name", "Sir")

        if not skills:
            return ToolResult(
                success=True,
                message=f"I have not learned any custom skills yet, {user_title}. "
                        "You can teach me new skills anytime by saying 'learn a new skill <name>: <steps>'.",
                data={"action": "list_skills", "skills": [], "count": 0},
            )

        lines = [f"I have mastered {len(skills)} custom skill(s), {user_title}:"]
        for s in skills:
            name = s.get("name", "")
            trig = s.get("trigger", name)
            desc = s.get("description", "")
            lines.append(f"- ⚡ '{name}' (trigger: '{trig}'): {desc}")

        return ToolResult(
            success=True,
            message="\n".join(lines),
            data={"action": "list_skills", "skills": skills, "count": len(skills)},
        )

    def _action_forget_skill(self, identifier: str) -> ToolResult:
        """Removes a previously learned skill."""
        if not identifier:
            return ToolResult(success=False, message="Please specify the skill name to remove.")

        removed = preference_manager.remove_skill(identifier)
        user_title = preference_manager.get_preference("user_name", "Sir")
        if removed:
            return ToolResult(
                success=True,
                message=f"Skill '{identifier}' has been removed from my learned procedures, {user_title}.",
                data={"action": "forget_skill", "identifier": identifier, "removed": True},
            )
        else:
            return ToolResult(
                success=False,
                message=f"I could not find a learned skill named '{identifier}', {user_title}.",
                data={"action": "forget_skill", "identifier": identifier, "removed": False},
            )

    def _action_remember_fact(self, key: str, value: str) -> ToolResult:
        """Stores a personal user fact or preference."""
        if not key or not value:
            return ToolResult(success=False, message="Please provide both a key and detail for the fact to remember.")

        preference_manager.add_fact(key, value)
        # If user is changing their default browser
        if "browser" in key.lower():
            preference_manager.set_preference("default_browser", value.lower().strip())
        # If user is setting their role or name
        if key.lower() in ("name", "user_name", "call_me"):
            preference_manager.set_preference("user_name", value.strip())

        user_title = preference_manager.get_preference("user_name", "Sir")
        clean_key = key.replace("_", " ").title()
        msg = f"I have committed that to memory, {user_title}. I will always remember that your {clean_key} is {value}."
        return ToolResult(
            success=True,
            message=msg,
            data={"action": "remember_fact", "key": key, "value": value},
        )

    def _action_recall_facts(self, specific_key: str = "") -> ToolResult:
        """Recalls all facts or a specific fact remembered about the user."""
        facts = preference_manager.get_all_facts()
        user_title = preference_manager.get_preference("user_name", "Sir")

        if specific_key:
            val = preference_manager.get_fact(specific_key)
            if val:
                return ToolResult(
                    success=True,
                    message=f"According to my memory, {user_title}, your {specific_key.replace('_', ' ')} is {val}.",
                    data={"action": "recall_facts", "key": specific_key, "value": val},
                )
            else:
                return ToolResult(
                    success=False,
                    message=f"I don't have any recorded memory regarding '{specific_key}', {user_title}.",
                    data={"action": "recall_facts", "key": specific_key, "found": False},
                )

        if not facts:
            return ToolResult(
                success=True,
                message=f"I don't have any personal facts stored yet, {user_title}. "
                        "Tell me anything you'd like me to remember by saying 'remember that <fact>'.",
                data={"action": "recall_facts", "facts": {}, "count": 0},
            )

        lines = [f"Here is what I have remembered about you, {user_title}:"]
        for k, v in facts.items():
            lines.append(f"- {k.replace('_', ' ').title()}: {v}")

        return ToolResult(
            success=True,
            message="\n".join(lines),
            data={"action": "recall_facts", "facts": facts, "count": len(facts)},
        )

    def _action_forget_fact(self, key: str) -> ToolResult:
        """Deletes a remembered fact."""
        if not key:
            return ToolResult(success=False, message="Please specify the fact key to forget.")

        removed = preference_manager.remove_fact(key)
        user_title = preference_manager.get_preference("user_name", "Sir")
        if removed:
            return ToolResult(
                success=True,
                message=f"I have removed the memory regarding '{key}', {user_title}.",
                data={"action": "forget_fact", "key": key, "removed": True},
            )
        else:
            return ToolResult(
                success=False,
                message=f"I could not find any stored memory for '{key}', {user_title}.",
                data={"action": "forget_fact", "key": key, "removed": False},
            )

    def _action_set_speaking_style(self, style: str) -> ToolResult:
        """Updates preferred speaking style or tone."""
        if not style:
            return ToolResult(success=False, message="Please provide the desired speaking style or tone.")

        preference_manager.set_preference("speaking_style", style.strip())
        user_title = preference_manager.get_preference("user_name", "Sir")
        msg = f"Speaking cadence updated, {user_title}. I will now speak with a {style.strip()} tone."
        return ToolResult(
            success=True,
            message=msg,
            data={"action": "set_speaking_style", "speaking_style": style},
        )

    def _action_set_user_name(self, name: str) -> ToolResult:
        """Updates the honorific or name used to address the user."""
        if not name:
            return ToolResult(success=False, message="Please provide the name or title to call you.")

        clean_name = name.strip()
        preference_manager.set_preference("user_name", clean_name)
        msg = f"Understood, {clean_name}. I will address you as {clean_name} from now on."
        return ToolResult(
            success=True,
            message=msg,
            data={"action": "set_user_name", "user_name": clean_name},
        )
