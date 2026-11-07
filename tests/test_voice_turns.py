import unittest

from jesse.voice.turns import TurnAssembler


class TurnAssemblerTests(unittest.TestCase):
    def test_waits_exact_silence_duration_and_groups_segments(self):
        turns = TurnAssembler(1.5)
        turns.speech_start(0)
        turns.final("a", "Compare rates.", 0, 0.1)
        turns.speech_end(0.2)
        self.assertIsNone(turns.take_ready(1.69))
        turns.speech_start(1.69)
        turns.final("b", "Repeat the trial.", 1, 1.8)
        turns.speech_end(1.9)
        self.assertIsNone(turns.take_ready(3.39))
        self.assertEqual(turns.take_ready(3.4), "Compare rates. Repeat the trial.")
        self.assertIsNone(turns.take_ready(5))

    def test_does_not_emit_while_speech_or_partial_is_pending(self):
        turns = TurnAssembler(1.5)
        turns.speech_start(0)
        turns.final("a", "First.", 0, 0.1)
        self.assertIsNone(turns.take_ready(10))
        turns.partial("b", 10)
        turns.speech_end(11)
        self.assertIsNone(turns.take_ready(100))
        self.assertIsNone(turns.take_ready(100, finishing=True))
        turns.final("b", "Second.", 1, 101)
        self.assertIsNone(turns.take_ready(102.49))
        self.assertEqual(turns.take_ready(102.5), "First. Second.")

    def test_finals_are_ordered_and_duplicates_are_ignored(self):
        turns = TurnAssembler(1.5)
        turns.final("b", "Second.", 2, 0)
        turns.final("a", "First.", 1, 0)
        self.assertFalse(turns.final("a", "Duplicate.", 1, 0))
        self.assertFalse(turns.partial("a", 0))
        self.assertEqual(turns.take_ready(0, finishing=True), "First. Second.")

    def test_empty_transcript_clears_pending_without_emitting(self):
        turns = TurnAssembler(1.5)
        turns.partial("a", 0)
        turns.final("a", " ", 0, 1)
        self.assertIsNone(turns.take_ready(10))
        self.assertFalse(turns.pending_ids)

    def test_silence_must_be_positive_and_finite(self):
        for value in (0, -1, float("inf"), float("nan")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                TurnAssembler(value)
