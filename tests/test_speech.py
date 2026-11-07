"""Spoken announcements are synthesized once, and only for events marked speak. No OpenAI call is made."""
import json
from pathlib import Path
import tempfile
import unittest

from jesse.conversation.speech import cached_action_speech, cached_speech, cached_step_speech


class SpeechTests(unittest.TestCase):
    def test_only_spoken_events_are_synthesized_once(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            spoken, silent = "a" * 32, "b" * 32
            (folder / "conversation.jsonl").write_text("\n".join(json.dumps(event) for event in [
                {"id": "c" * 32, "kind": "question", "author": "researcher", "text": "Le substrat accélère-t-il la réaction ?"},
                {"id": spoken, "text": "trial1 recorded: 1.28.", "speak": True},
                {"id": silent, "text": "internal", "speak": False}]) + "\n", encoding="utf-8")
            calls = []
            synthesize = lambda text: calls.append(text) or b"mp3"
            translate = lambda text, question: f"[fr] {text}" if "substrat" in question else text
            first = cached_speech(folder, spoken, synthesize, translate)
            second = cached_speech(folder, spoken, synthesize, translate)
            self.assertEqual(first, second)
            self.assertEqual(first.name, f"{spoken}.mp3")
            self.assertEqual(first.parent.parent, folder / "speech")
            self.assertEqual(calls, ["[fr] trial1 recorded: 1.28."])
            self.assertIsNone(cached_speech(folder, silent, synthesize, translate))
            self.assertIsNone(cached_speech(folder, "../escape", synthesize, translate))
            self.assertEqual(len(calls), 1)


class TranslationFailureTests(unittest.TestCase):
    def test_original_text_is_spoken_when_translation_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            event = "d" * 32
            (folder / "conversation.jsonl").write_text("\n".join(json.dumps(item) for item in [
                {"id": "c" * 32, "kind": "question", "author": "researcher", "text": "¿Más sustrato?"},
                {"id": event, "text": "Done.", "speak": True}]) + "\n", encoding="utf-8")
            calls = []

            def broken(text, question):
                raise RuntimeError("offline")

            cached_speech(folder, event, lambda text: calls.append(text) or b"mp3", broken)
            self.assertEqual(calls, ["Done."])


class StepSpeechTests(unittest.TestCase):
    def test_current_plan_step_is_announced(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            plan = {"tool_name": "update_plan", "args": {"goals": [
                {"title": "Open the model", "status": "done"}, {"title": "Trial 1: VOLUME 50", "status": "running"}]}}
            (folder / "events.jsonl").write_text(json.dumps({"type": "AgentEvent", "timestamp": "t", "data": {
                "kind": "policy_event", "content": "", "tool_reqs": [plan]}}) + "\n", encoding="utf-8")
            calls = []
            path = cached_step_speech(folder, 1, lambda text: calls.append(text) or b"mp3", lambda text, question: text)
            self.assertTrue(path.exists())
            self.assertEqual(calls, ["Step 2/2: Trial 1: VOLUME 50"])
            self.assertIsNone(cached_step_speech(folder, 5, lambda text: b"", lambda text, question: text))

    def test_agent_action_is_announced_from_its_public_text(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            click = {"tool_name": "click_web", "args": {"x": 0.5, "y": 0.5, "element": "Load arrow"}}
            (folder / "events.jsonl").write_text(json.dumps({"type": "AgentEvent", "timestamp": "t", "data": {
                "kind": "policy_event", "content": "Loading the Coolant I assignment.", "reasoning_content": "private",
                "tool_reqs": [click]}}) + "\n", encoding="utf-8")
            calls = []
            cached_action_speech(folder, 0, lambda text: calls.append(text) or b"mp3", lambda text, question: text)
            self.assertEqual(calls, ["Loading the Coolant I assignment."])


class ProviderTests(unittest.TestCase):
    def test_elevenlabs_key_alone_enables_speech(self):
        from unittest import mock
        from jesse.conversation import speech

        for name in ("ELEVENLABS_API_KEY", "IL_KEY"):
            with mock.patch.dict("os.environ", {name: "k"}, clear=True):
                self.assertTrue(speech.speech_available())
        with mock.patch.dict("os.environ", {}, clear=True):
            self.assertFalse(speech.speech_available())

    def test_pinkman_persona_is_default_and_plain_is_explicit(self):
        from unittest import mock
        from jesse.conversation import speech

        with mock.patch.dict("os.environ", {}, clear=True):
            self.assertTrue(speech.pinkman())
        with mock.patch.dict("os.environ", {"JESSE_PERSONA": "pinkman"}, clear=True):
            self.assertTrue(speech.pinkman())
        with mock.patch.dict("os.environ", {"JESSE_PERSONA": "plain"}, clear=True):
            self.assertFalse(speech.pinkman())


if __name__ == "__main__":
    unittest.main()
