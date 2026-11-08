import contextlib
import io
import os
import threading
import unittest

from jesse.voice.planning import VoicePlanningQueue


class VoicePlanningTests(unittest.TestCase):
    def test_planning_queue_is_ordered_and_reports_blocked(self):
        received = []

        def plan(text):
            received.append(text)
            return 1 if text == "blocked" else 0

        output = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(output):
            worker = VoicePlanningQueue(plan)
            worker.submit("first")
            worker.submit("blocked")
            self.assertFalse(worker.close())
        self.assertEqual(received, ["first", "blocked"])
        self.assertIn("blocked", output.getvalue())

    def test_queue_full_is_explicit_and_accepted_turns_finish(self):
        started = threading.Event()
        release = threading.Event()
        received = []

        def plan(text):
            received.append(text)
            started.set()
            release.wait(5)
            return 0

        with contextlib.redirect_stdout(io.StringIO()):
            worker = VoicePlanningQueue(plan, capacity=1)
            try:
                worker.submit("first")
                self.assertTrue(started.wait(5))
                worker.submit("second")
                with self.assertRaisesRegex(RuntimeError, "queue is full"):
                    worker.submit("third")
            finally:
                release.set()
                self.assertTrue(worker.close())
        self.assertEqual(received, ["first", "second"])

    def test_worker_failure_is_reported_without_exposing_provider_details(self):
        def fail(text):
            raise RuntimeError("sensitive provider details")

        output = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(output):
            worker = VoicePlanningQueue(fail)
            worker.submit("question")
            self.assertFalse(worker.close())
        self.assertIn("Voice planning failed", output.getvalue())
        self.assertNotIn("sensitive provider details", output.getvalue())
