"""Controller integration tests. All numerical readings here are synthetic fixtures."""
from dataclasses import dataclass
from pathlib import Path
import json
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from jesse.experiments.netlogo.application import run_experiment
from jesse.experiments.netlogo.adapters import FileExperimentRecords, HDesktopAgent
from jesse.experiments.netlogo.cli import main
from jesse.experiments.netlogo.domain import build_prompt
from jesse.experiments.netlogo.preflight import Check, check_desktop
from jesse.recording.domain import Observation


def synthetic_reading(**changes):
    payload = dict(
        observation_id="obs-1", trial_id="trial-1", observed_at="2026-11-07T12:00:00Z",
        settings={"VOLUME": 10, "Kc": 1, "Kd": 1, "Kr": 1, "PAUSE?": True},
        quantity="reaction rate", value=2.0, unit=None, raw_reading="synthetic fixture: 2",
        evidence=["session:test-session/event:1"],
        interval={"start": 0, "end": 30, "unit": "ticks"}, status="observed", reason=None,
    )
    return {**payload, **changes}


@dataclass
class SyntheticResult:
    id: str = "test-session"
    status: str = "completed"
    answer: str = "Synthetic test report"


class FakeHandle:
    id = "test-session"

    def __init__(self, records, fail=False):
        self.records = records
        self.fail = fail
        self.cancelled = False

    def get(self):
        return SimpleNamespace(agent_view_url="https://example.test/view")

    def stream(self, **kwargs):
        # Metadata must reach disk before the first observation is processed.
        saved = json.loads((self.records.folder / "session.json").read_text())
        assert saved["agent_view_url"] == "https://example.test/view"
        yield {"type": "SyntheticEvent", "id": "1"}
        observation = synthetic_reading()
        self.tool(
            observation_id=observation["observation_id"], trial_id=observation["trial_id"],
            volume=10, kc=1, kd=1, kr=1, pause=True, value=observation["value"],
            unit=observation["unit"], raw_reading=observation["raw_reading"],
            evidence=observation["evidence"], start_tick=0, end_tick=30, status="observed",
        )
        self.analysis_tool()
        if self.fail:
            raise RuntimeError("Synthetic connection failure")

    def wait_for_completion(self, **kwargs):
        return SyntheticResult()

    def cancel(self):
        self.cancelled = True


class FakeClient:
    def __init__(self, handle):
        self.handle = handle

    def start_session(self, **kwargs):
        from hai_agents.tools import as_tools
        tools = as_tools(kwargs["tools"])
        assert tools[0].definition()["input_schema"]["type"] == "object"
        assert "settings" not in tools[0].input_schema["properties"]
        assert {"volume", "kc", "kd", "kr", "pause"} <= set(tools[0].input_schema["properties"])
        self.handle.tool = tools[0]
        self.handle.analysis_tool = tools[1]
        self.params = kwargs
        return self.handle


class ExperimentTests(unittest.TestCase):
    def test_real_adapter_streams_records_and_preserves_sdk_dataclass(self):
        with tempfile.TemporaryDirectory() as directory:
            records = FileExperimentRecords(Path(directory))
            client = FakeClient(FakeHandle(records))
            outcome = run_experiment(HDesktopAgent(client=client, surface="web"), records, build_prompt("web"))
            self.assertEqual(outcome, "inconclusive")  # Replay still needs review.
            session = json.loads((records.folder / "session.json").read_text())
            self.assertEqual(session["id"], "test-session")
            self.assertEqual(session["status"], "completed")
            self.assertIn("Synthetic test report", (records.folder / "agent-report.md").read_text())
            self.assertTrue((records.folder / "observations/obs-1.json").exists())
            reading = json.loads((records.folder / "observations/obs-1.json").read_text())
            self.assertEqual(reading["settings"], {"VOLUME": 10, "Kc": 1, "Kd": 1, "Kr": 1, "PAUSE?": True})
            self.assertEqual(reading["quantity"], "reaction velocity (V)")
            self.assertIn("SyntheticEvent", (records.folder / "events.jsonl").read_text())
            self.assertEqual(client.params["agent"]["environments"][0]["kind"], "web")
            self.assertEqual(client.params["max_time_s"], 600)

    def test_stream_failure_cancels_and_retains_prior_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            records = FileExperimentRecords(Path(directory))
            handle = FakeHandle(records, fail=True)
            with self.assertRaises(RuntimeError):
                run_experiment(HDesktopAgent(client=FakeClient(handle)), records)
            self.assertTrue(handle.cancelled)
            records.finish("blocked", "Synthetic connection failure")
            self.assertTrue((records.folder / "session.json").exists())
            self.assertTrue((records.folder / "observations/obs-1.json").exists())
            self.assertIn("obs-1", (records.folder / "report.md").read_text())
            self.assertFalse((records.folder / "agent-report.md").exists())

    def test_idle_turn_is_cancelled_after_its_answer_is_retained(self):
        with tempfile.TemporaryDirectory() as directory:
            records = FileExperimentRecords(Path(directory))
            handle = FakeHandle(records)
            handle.wait_for_completion = lambda **kwargs: SyntheticResult(status="idle")
            run_experiment(HDesktopAgent(client=FakeClient(handle)), records)
            self.assertTrue(handle.cancelled)
            saved = json.loads((records.folder / "session.json").read_text())
            self.assertEqual(saved["cleanup"], "cancelled_after_answer")
            self.assertIn("Synthetic test report", (records.folder / "agent-report.md").read_text())

    def test_failed_sdk_session_is_not_success(self):
        class FailedAgent:
            def run(self, instructions, records):
                return {"id": "failed", "status": "failed"}, "Could not read the screen"
        with tempfile.TemporaryDirectory() as directory:
            records = FileExperimentRecords(Path(directory))
            self.assertEqual(run_experiment(FailedAgent(), records), "blocked")

    def test_evidence_index_uses_real_tool_event_and_handles_null_pending_calls(self):
        with tempfile.TemporaryDirectory() as directory:
            records = FileExperimentRecords(Path(directory))
            records.session_started({"id": "test-session", "agent_view_url": "https://example.test/view"})
            records.event_received({"type": "ActiveStateChangeEvent", "data": {"pending_tool_calls": None}})
            records.event_received({"type": "ActiveStateChangeEvent", "timestamp": "2026-11-07T12:00:00Z", "data": {"pending_tool_calls": [{"tool_name": "record_observation", "id": "tool-1", "args": {"observation_id": "obs-1"}}]}})
            records.finish("inconclusive", "Synthetic evidence index test")
            index = json.loads((records.folder / "evidence-index.json").read_text())
            self.assertEqual(index["obs-1"]["line"], 2)
            self.assertEqual(index["obs-1"]["tool_call_id"], "tool-1")

    def test_parent_finalization_preserves_first_reading_metrics(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            worker = FileExperimentRecords(folder)
            worker.record_observation(Observation(**synthetic_reading()))
            original = json.loads((folder / "metrics.json").read_text())
            FileExperimentRecords(folder).finish("inconclusive", "Synthetic timeout")
            updated = json.loads((folder / "metrics.json").read_text())
            self.assertEqual(updated["first_observation_seconds"], original["first_observation_seconds"])
            self.assertEqual(updated["readable_observations"], 1)

    def test_web_prompt_uses_same_science_without_desktop_only_instruction(self):
        prompt = build_prompt("web")
        self.assertIn("Operate NetLogo Web only", prompt)
        self.assertNotIn("Operate NetLogo Desktop only", prompt)
        self.assertIn("record_observation", prompt)
        self.assertIn("RECORD V", prompt)

    def test_web_preflight_does_not_require_native_application_or_permissions(self):
        with patch.dict("os.environ", {"HAI_API_KEY": "synthetic-test-key"}):
            checks, application = check_desktop(surface="web")
        self.assertTrue(all(check.ready for check in checks))
        self.assertIsNone(application)
        self.assertEqual({check.name for check in checks}, {"credentials", "sdk"})

    def test_check_command_creates_no_paid_session(self):
        with patch("jesse.experiments.netlogo.cli.check_desktop", return_value=([Check("test", False, "missing")], None)), patch("jesse.experiments.netlogo.cli.multiprocessing.get_context") as processes:
            self.assertEqual(main(["--surface", "web", "--check"]), 1)
            processes.assert_not_called()

    def test_timeout_cannot_expand_ten_minute_budget(self):
        with self.assertRaises(SystemExit) as result:
            main(["--timeout", "601"])
        self.assertEqual(result.exception.code, 2)


class ObservationTests(unittest.TestCase):
    def test_identical_retries_are_idempotent_and_conflicts_preserve_original(self):
        with tempfile.TemporaryDirectory() as directory:
            records = FileExperimentRecords(Path(directory))
            reading = Observation(**synthetic_reading())
            self.assertFalse(records.record_observation(reading)["duplicate"])
            self.assertTrue(records.record_observation(reading)["duplicate"])
            with self.assertRaises(ValueError):
                records.record_observation(Observation(**synthetic_reading(value=99)))
            saved = json.loads((records.folder / "observations/obs-1.json").read_text())
            self.assertEqual(saved["value"], 2)
            self.assertEqual(len(list((records.folder / "observations").glob("*.json"))), 1)

    def test_invalid_or_unsupported_readings_are_rejected(self):
        for changes in (
            {"observation_id": "../../escape"}, {"value": float("nan")}, {"value": True},
            {"evidence": []}, {"value": None}, {"observed_at": "2026-11-07T12:00:00"},
            {"interval": {"start": 30, "end": 0, "unit": "ticks"}},
            {"status": "unreadable", "value": None, "reason": None},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                Observation(**synthetic_reading(**changes))

    def test_unreadable_output_preserves_unknowns_and_reason(self):
        reading = Observation(**synthetic_reading(value=None, status="unreadable", reason="Plot labels too small"))
        self.assertIsNone(reading.value)
        self.assertIsNone(reading.unit)
        self.assertEqual(reading.status, "unreadable")
