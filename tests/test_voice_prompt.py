import unittest

from jesse.voice.prompt import build_spoken_request


class SpokenRequestPromptTests(unittest.TestCase):
    def test_wraps_transcript_as_researcher_request(self):
        prompt = build_spoken_request("  Compare the reaction rates.  ")

        self.assertEqual(
            prompt,
            "Researcher request transcribed by Gladia "
            "(the transcript may contain recognition errors):\n\n"
            "Compare the reaction rates.",
        )

    def test_rejects_empty_transcript(self):
        with self.assertRaisesRegex(ValueError, "spoken request"):
            build_spoken_request(" \n ")
