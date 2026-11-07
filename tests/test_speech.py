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
                {"id": spoken, "text": "trial1 recorded: 1.28.", "speak": True},
                {"id": silent, "text": "internal", "speak": False}]) + "\n", encoding="utf-8")
            calls = []
            synthesize = lambda text: calls.append(text) or b"mp3"
            first = cached_speech(folder, spoken, synthesize)
            second = cached_speech(folder, spoken, synthesize)
            self.assertEqual((first, second), (folder / "speech" / f"{spoken}.mp3",) * 2)
            self.assertEqual(calls, ["trial1 recorded: 1.28."])
            self.assertIsNone(cached_speech(folder, silent, synthesize))
            self.assertIsNone(cached_speech(folder, "../escape", synthesize))
            self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
