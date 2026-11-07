"""Research context folders load, validate and supply tools. Readings are synthetic fixtures."""
from dataclasses import dataclass
import json
from pathlib import Path
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest

from jesse.contexts import ContextError, find_context, load_context, load_contexts, load_extension
from jesse.investigating.lab import Lab
from jesse.investigating.runner import build_prompt, context_tools, execute
from context_fixtures import synthetic_context, write_context

REPO_CONTEXTS = Path(__file__).resolve().parents[1] / "contexts"


class ContextLoadingTests(unittest.TestCase):
    def test_shipped_coolant_context_loads_with_its_calorimetry_tool(self):
        context = find_context("chemcollective-coolant", REPO_CONTEXTS)
        self.assertEqual(context.surface_names, ("web",))
        self.assertEqual(context.surfaces["web"].start_url, "https://chemcollective.org/vlab/92")
        self.assertEqual(context.max_trials, 2)
        with tempfile.TemporaryDirectory() as directory:
            lab = Lab(Path(directory), context, extension=load_extension(context))
            names = [tool.__name__ for tool in context_tools(lab)]
        self.assertEqual(names, ["publish_update", "acknowledge_researcher_message", "record_calorimetry"])

    def test_template_and_hidden_folders_are_not_loaded(self):
        ids = {item.id for item in load_contexts(REPO_CONTEXTS)}
        self.assertIn("chemcollective-coolant", ids)
        self.assertFalse(any(item.startswith("_") for item in ids))

    def test_a_new_folder_becomes_a_context_with_both_surfaces(self):
        with tempfile.TemporaryDirectory() as directory:
            write_context(Path(directory))
            (context,) = load_contexts(Path(directory))
            self.assertEqual(context.surface_names, ("web", "desktop"))
            self.assertEqual(context.surfaces["desktop"].environment(context.id)["host"], "user_device")
            self.assertEqual(context.tools, ("publish_update", "acknowledge_researcher_message", "record_observation"))
            self.assertNotIn("protocol", context.to_dict())

    def test_invalid_declarations_name_the_problem(self):
        cases = {
            "missing surface": 'id = "bad"\ntitle = "t"\napplication = "a"\nquestions = ["q"]\n',
            "unknown surface": 'id = "bad"\ntitle = "t"\napplication = "a"\nquestions = ["q"]\n[surfaces.phone]\n',
            "http url": 'id = "bad"\ntitle = "t"\napplication = "a"\nquestions = ["q"]\n[surfaces.web]\nstart_url = "http://x.test"\n',
            "unknown tool": 'id = "bad"\ntitle = "t"\napplication = "a"\nquestions = ["q"]\ntools = ["rm_rf"]\n[surfaces.web]\nstart_url = "https://x.test"\n',
            "bad id": 'id = "Bad Id"\ntitle = "t"\napplication = "a"\nquestions = ["q"]\n[surfaces.web]\nstart_url = "https://x.test"\n',
            "budget": 'id = "bad"\ntitle = "t"\napplication = "a"\nquestions = ["q"]\n[surfaces.web]\nstart_url = "https://x.test"\n[limits]\nbudget_seconds = 9000\n',
        }
        for name, toml in cases.items():
            with self.subTest(name), tempfile.TemporaryDirectory() as directory:
                with self.assertRaises(ContextError):
                    load_context(write_context(Path(directory), "bad", toml=toml))

    def test_missing_protocol_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = write_context(Path(directory))
            (folder / "protocol.md").unlink()
            with self.assertRaises(ContextError):
                load_context(folder)

    def test_prompt_names_the_surface_and_includes_the_protocol(self):
        context = synthetic_context(surfaces=("web", "desktop"))
        self.assertIn("https://example.test/lab", build_prompt(context, "web", "Q?"))
        self.assertIn("local desktop", build_prompt(context, "desktop", "Q?"))
        self.assertIn("# Synthetic protocol", build_prompt(context, "web", "Q?"))


class LabRecordTests(unittest.TestCase):
    def test_identical_retries_are_idempotent_conflicts_and_extra_trials_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            lab = Lab(Path(directory), synthetic_context(max_trials=1))
            self.assertTrue(lab.record("t1", {"x": 1}, fields={"x": "1"})["recorded"])
            self.assertTrue(lab.record("t1", {"x": 1})["recorded"])
            with self.assertRaises(ValueError):
                lab.record("t1", {"x": 2})
            with self.assertRaises(ValueError):
                lab.record("t2", {"x": 3})
            with self.assertRaises(ValueError):
                lab.record("../escape", {"x": 3})

    def test_report_links_evidence_and_never_claims_support_before_review(self):
        with tempfile.TemporaryDirectory() as directory:
            lab = Lab(Path(directory), synthetic_context(), "Q?")
            self.assertEqual(lab.finish("Nothing recorded."), "blocked")
            lab.record("t1", {"x": 1}, analysis={"status": "estimated"}, fields={"x": "1 u"}, result="2 v")
            self.assertEqual(lab.finish("Done."), "inconclusive")
            report = (Path(directory) / "report.md").read_text()
            self.assertIn("| t1 | x: 1 u | 2 v | estimated |", report)
            self.assertIn("analyses/t1.json", report)

    def test_generic_observation_tool_requires_evidence(self):
        from jesse.investigating.tools import builtin_tools
        with tempfile.TemporaryDirectory() as directory:
            lab = Lab(Path(directory), synthetic_context())
            (record,) = builtin_tools(lab, ("record_observation",))
            with self.assertRaises(ValueError):
                record("t1", {"temperature": 20.0}, {"temperature": "°C"}, "20 °C", [])
            self.assertTrue(record("t1", {"temperature": 20.0}, {"temperature": "°C"}, "20 °C", ["screenshot:1"])["recorded"])
            saved = json.loads((Path(directory) / "observations" / "t1.json").read_text())
            self.assertEqual(saved["display"]["fields"], {"temperature": "20.0 °C"})


class CoolantToolTests(unittest.TestCase):
    def setUp(self):
        self.context = find_context("chemcollective-coolant", REPO_CONTEXTS)
        self.extension = load_extension(self.context)

    def reading(self, **changes):
        values = dict(trial_id="trial-1", coolant_volume_ml=10.0, water_volume_ml=20.0, coolant_initial_c=20.0,
                      water_initial_c=80.0, final_c=60.0, samples_insulated=True, mixing_vessel_insulated=True,
                      temperatures_verified=True, raw_reading="synthetic fixture", evidence=["screenshot:1"])
        return {**values, **changes}

    def test_calorimetry_estimates_and_compares_with_the_reference(self):
        result = self.extension.analyze_reading(self.reading())
        self.assertEqual(result["status"], "estimated")
        self.assertAlmostEqual(result["specific_heat_j_g_c"], 20 * 4.184 * 20 / (27.8 * 40))
        self.assertEqual(result["comparison"], "lower")

    def test_uninsulated_or_unverified_trials_need_a_repeat(self):
        self.assertEqual(self.extension.analyze_reading(self.reading(samples_insulated=False))["status"], "needs_repeat")
        self.assertEqual(self.extension.analyze_reading(self.reading(final_c=90.0))["status"], "needs_repeat")

    def finish_with(self, *final_temperatures):
        with tempfile.TemporaryDirectory() as directory:
            lab = Lab(Path(directory), self.context, "Q?", self.extension)
            (tool,) = self.extension.tools(lab)
            for index, final_c in enumerate(final_temperatures, 1):
                tool(**self.reading(trial_id=f"trial-{index}", final_c=final_c))
            outcome = lab.finish("Session finished.")
            return outcome, json.loads((Path(directory) / "outcome.json").read_text())

    def test_two_agreeing_checked_trials_support_a_conclusion(self):
        outcome, saved = self.finish_with(46.82, 46.82)
        self.assertEqual(outcome, "supported_conclusion")
        self.assertIn("more heat", saved["reason"])
        self.assertEqual(saved["verification"], "pending_replay_review")

    def test_one_trial_or_disagreeing_trials_stay_inconclusive(self):
        self.assertEqual(self.finish_with(46.82)[0], "inconclusive")
        self.assertEqual(self.finish_with(46.82, 60.0)[0], "inconclusive")

    def test_tool_records_display_and_report_section(self):
        with tempfile.TemporaryDirectory() as directory:
            lab = Lab(Path(directory), self.context, "Q?", self.extension)
            (tool,) = self.extension.tools(lab)
            tool(**self.reading())
            lab.finish("Done.")
            report = (Path(directory) / "report.md").read_text()
            self.assertIn("Final: 60 °C", report)
            self.assertIn("## Calculation", report)


@dataclass
class SyntheticResult:
    id: str = "test-session"
    status: str = "completed"
    answer: str = "Synthetic test report"


class FakeHandle:
    id = "test-session"

    def __init__(self, folder, fail=False, freeze=None):
        self.folder = folder
        self.fail = fail
        self.freeze = freeze  # None, or the agent state H reports before going silent
        self.cancelled = False
        self.released = threading.Event()

    def get(self):
        return SimpleNamespace(agent_view_url="https://example.test/view")

    def stream(self, **kwargs):
        saved = json.loads((self.folder / "session.json").read_text())
        assert saved["agent_view_url"] == "https://example.test/view"
        yield {"type": "SyntheticEvent", "id": "1"}
        self.tools["record_observation"](trial_id="t1", readings={"x": 1.0}, units={"x": "u"},
                                         raw_reading="synthetic fixture", evidence=["event:1"])
        if self.fail:
            raise RuntimeError("Synthetic connection failure")
        if self.freeze:
            yield {"type": "ActiveStateChangeEvent", "data": {"state": self.freeze}}
            self.released.wait(1.0)  # H goes silent; the stall watchdog must not wait this out

    def wait_for_completion(self, **kwargs):
        return SyntheticResult()

    def cancel(self):
        self.cancelled = True
        self.released.set()


class FakeClient:
    def __init__(self, handle):
        self.handle = handle

    def start_session(self, **kwargs):
        from hai_agents.tools import as_tools
        for tool in as_tools(kwargs["tools"]):
            assert tool.definition()["input_schema"]["type"] == "object"
        self.handle.tools = {tool.__name__: tool for tool in kwargs["tools"]}
        self.params = kwargs
        return self.handle


class RunnerTests(unittest.TestCase):
    def run_session(self, surface="web", fail=False, freeze=None, stall_seconds=60):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        folder = Path(directory.name)
        context = synthetic_context()
        (folder / "protocol.md").write_text(build_prompt(context, surface, "Q?"), encoding="utf-8")
        handle = FakeHandle(folder, fail, freeze)
        client = FakeClient(handle)
        execute(folder, context, surface, 120, "Q?", client=client, stall_seconds=stall_seconds)
        return folder, client, handle

    def test_session_streams_records_and_reports(self):
        folder, client, handle = self.run_session()
        self.assertEqual(client.params["agent"]["environments"][0]["start_url"], "https://example.test/lab")
        self.assertEqual(client.params["max_time_s"], 120)
        self.assertIn("SyntheticEvent", (folder / "events.jsonl").read_text())
        self.assertEqual(json.loads((folder / "outcome.json").read_text())["outcome"], "inconclusive")
        self.assertIn("Synthetic test report", (folder / "agent-report.md").read_text())
        self.assertTrue(handle.cancelled)

    def test_desktop_surface_uses_the_local_bridge(self):
        _, client, _ = self.run_session("desktop")
        self.assertEqual(client.params["agent"]["environments"][0], {"id": "synthetic-lab-desktop", "kind": "desktop", "host": "user_device", "shell": False})

    def test_frozen_agent_is_closed_and_measurements_kept(self):
        started = time.monotonic()
        folder, _, handle = self.run_session(freeze="running", stall_seconds=0.2)
        self.assertLess(time.monotonic() - started, 0.9)
        self.assertTrue(handle.cancelled)
        outcome = json.loads((folder / "outcome.json").read_text())
        self.assertEqual(outcome["outcome"], "inconclusive")
        self.assertIn("stopped responding", outcome["reason"])
        self.assertTrue((folder / "stall.json").exists())
        self.assertIn("t1", (folder / "report.md").read_text())

    def test_idle_agent_waiting_for_the_researcher_is_not_a_stall(self):
        folder, _, handle = self.run_session(freeze="idle", stall_seconds=0.2)
        self.assertFalse((folder / "stall.json").exists())
        self.assertNotIn("stopped responding", json.loads((folder / "outcome.json").read_text())["reason"])

    def test_interactive_answer_publishes_report_before_session_closes(self):
        class InteractiveHandle(FakeHandle):
            def stream(inner, **kwargs):
                self.assertEqual(kwargs["until"], "terminal")
                yield from super(InteractiveHandle, inner).stream(**kwargs)
                yield {"type": "AgentEvent", "data": {"kind": "answer_event", "answer": "Synthetic current answer"}}
                yield {"type": "ActiveStateChangeEvent", "data": {"state": "idle"}}

            def wait_for_completion(inner, **kwargs):
                self.assertIn("Synthetic current answer", (inner.folder / "report.md").read_text())
                self.assertIn('"kind": "report_ready"', (inner.folder / "conversation.jsonl").read_text())
                self.assertEqual(json.loads((inner.folder / "session-state.json").read_text())["state"], "idle")
                return super(InteractiveHandle, inner).wait_for_completion(**kwargs)

        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            context = synthetic_context()
            (folder / "protocol.md").write_text(build_prompt(context, "web", "Synthetic question"))
            handle = InteractiveHandle(folder)
            client = FakeClient(handle)
            execute(folder, context, "web", 120, "Synthetic question", interactive=True, client=client)
            self.assertTrue(handle.cancelled)
            self.assertFalse((folder / "error.json").exists())

    def test_stream_failure_cancels_and_retains_prior_evidence(self):
        folder, _, handle = self.run_session(fail=True)
        self.assertTrue(handle.cancelled)
        self.assertEqual(json.loads((folder / "error.json").read_text())["type"], "RuntimeError")
        self.assertTrue((folder / "observations" / "t1.json").exists())
        self.assertIn("t1", (folder / "report.md").read_text())


if __name__ == "__main__":
    unittest.main()
