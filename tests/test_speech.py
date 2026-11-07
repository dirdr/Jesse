"""Spoken announcements are synthesized once, and only for events marked speak. No OpenAI call is made."""
import json
from pathlib import Path
import tempfile
import unittest

from jesse.conversation.speech import cached_speech


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
            self.assertEqual((first, second), (folder / "speech" / f"{spoken}.mp3",) * 2)
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


if __name__ == "__main__":
    unittest.main()
