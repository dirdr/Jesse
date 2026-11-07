import contextlib
import io
import os
from pathlib import Path
import sys
import tempfile
import threading
import types
import unittest
from unittest.mock import patch

from context_fixtures import CATALOGUE
from jesse.voice.live import main
from jesse.voice.planning import VoicePlanningQueue


class VoicePlanningTests(unittest.TestCase):
    def test_completed_voice_turn_reaches_existing_pydantic_selector(self):
        from jesse.preflight import Check
        from jesse.selecting.adapters import PlannerOutput
        from pydantic_ai.usage import RunUsage

        output = PlannerOutput(
            decision="select", experiment_id=CATALOGUE[0].id,
            surface="web", reason="A bounded rate comparison is supported.",
        )
        response = types.SimpleNamespace(output=output, usage=RunUsage())

        devices = []

        def capture(client, stream_factory, *, on_turn, silence_seconds, input_device):
            devices.append(input_device)
            on_turn("Does more substrate change the reaction rate?")

        def check(surface, application=None):
            return [Check("test", surface == "web", "synthetic")]

        sounddevice = types.SimpleNamespace(
            query_devices=lambda *args, **kwargs: {"name": "synthetic microphone"}, RawInputStream=object,
            PortAudioError=type("PortAudioError", (Exception,), {}),
        )
        previous = Path.cwd()
        with tempfile.TemporaryDirectory() as directory:
            try:
                os.chdir(directory)
                with patch.dict(os.environ, {"GLADIA_API_KEY": "test", "OPENAI_API_KEY": "test"}):
                    with patch.dict(sys.modules, {"sounddevice": sounddevice}):
                        with patch("jesse.voice.live.run_live_preview", side_effect=capture):
                            with patch("jesse.selecting.cli.check_surface", side_effect=check), patch("jesse.selecting.cli.load_contexts", return_value=CATALOGUE):
                                with patch("pydantic_ai.Agent.run_sync", return_value=response) as model:
                                    with patch("jesse.selecting.cli.run_investigation") as execute:
                                        with contextlib.redirect_stdout(io.StringIO()):
                                            self.assertEqual(main(["--plan", "--input-device", "7"]), 0)
                self.assertEqual(devices, [7])
                self.assertIn("Does more substrate", model.call_args.args[0])
                execute.assert_not_called()
                run = next((Path(directory) / "runs").iterdir())
                self.assertIn("Does more substrate", (run / "request.json").read_text())
                self.assertIn('"status": "ready"', (run / "selection.json").read_text())
                self.assertIn("Plan-only mode", (run / "report.md").read_text())
            finally:
                os.chdir(previous)

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

    def test_plan_requires_openai_key_before_capture(self):
        with patch.dict(os.environ, {"GLADIA_API_KEY": "test"}, clear=True):
            with contextlib.redirect_stderr(io.StringIO()) as output:
                self.assertEqual(main(["--plan"]), 1)
        self.assertIn("OPENAI_API_KEY", output.getvalue())

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
