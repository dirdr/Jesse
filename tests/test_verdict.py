"""Automatic outcome verdict and its Python guardrails. The model is replaced by a fake; no OpenAI call is made."""
from pathlib import Path
import json
import tempfile
import unittest

from jesse.investigating.lab import Lab
from jesse.investigating.verdict import Verdict, judge
from context_fixtures import synthetic_context


class VerdictTests(unittest.TestCase):
    def lab(self, trials=("t1", "t2")):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        lab = Lab(Path(directory.name), synthetic_context(), "Q?")
        for trial in trials:
            lab.record(trial, {"x": 1}, analysis={"status": "estimated"}, fields={"x": "1 u"})
        return lab

    def test_supported_verdict_citing_recorded_trials_is_accepted(self):
        lab = self.lab()
        calls = []
        ask = lambda payload: calls.append(payload) or Verdict(outcome="supported_conclusion", reason="X is higher.", cited_trials=["t1", "t2"])
        lab.judge = lambda current: judge(current, ask)
        self.assertEqual(lab.finish("Session finished."), "supported_conclusion")
        saved = json.loads((lab.folder / "outcome.json").read_text())
        self.assertIn("X is higher.", saved["reason"])
        self.assertIn("replay review pending", saved["reason"])
        self.assertEqual([trial["trial_id"] for trial in calls[0]["trials"]], ["t1", "t2"])
        self.assertTrue((lab.folder / "verdict.json").exists())

    def test_supported_verdict_citing_unknown_trials_is_downgraded(self):
        lab = self.lab()
        ask = lambda payload: Verdict(outcome="supported_conclusion", reason="X is higher.", cited_trials=["t9"])
        lab.judge = lambda current: judge(current, ask)
        self.assertEqual(lab.finish("Session finished."), "inconclusive")

    def test_model_failure_keeps_the_default_outcome(self):
        lab = self.lab()

        def broken(payload):
            raise RuntimeError("offline")

        lab.judge = lambda current: judge(current, broken)
        self.assertEqual(lab.finish("Session finished."), "inconclusive")
        self.assertEqual(json.loads((lab.folder / "verdict.json").read_text())["error"], "RuntimeError")

    def test_no_measurement_is_blocked_without_asking(self):
        lab = self.lab(trials=())
        calls = []
        lab.judge = lambda current: judge(current, lambda payload: calls.append(payload))
        self.assertEqual(lab.finish("Nothing recorded."), "blocked")
        self.assertEqual(calls, [])

    def test_unchanged_evidence_is_judged_once(self):
        lab = self.lab()
        calls = []
        ask = lambda payload: calls.append(1) or Verdict(outcome="inconclusive", reason="Repeat needed.", cited_trials=[])
        lab.judge = lambda current: judge(current, ask)
        lab.finish("First.")
        lab.finish("Second.")
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
