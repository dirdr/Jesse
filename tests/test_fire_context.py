"""Synthetic Fire readings exercise the real context extension, not simulator findings."""
from pathlib import Path
import tempfile
import unittest

from jesse.contexts import find_context, load_extension
from jesse.investigating.lab import Lab
from jesse.investigating.runner import context_tools

CONTEXTS = Path(__file__).resolve().parents[1] / "contexts"


class FireContextTests(unittest.TestCase):
    def setUp(self):
        self.context = find_context("netlogo-fire", CONTEXTS)
        self.extension = load_extension(self.context)

    def reading(self, **changes):
        return {"trial_id": "low-1", "density_percent": 55.0, "percent_burned": 12.3,
                "ticks": 135, "fresh_setup": True, "completed": True, "settings_verified": True,
                "raw_reading": "Synthetic fixture: density 55%, percent burned 12.3, ticks 135",
                "evidence": ["synthetic:setup", "synthetic:final"], **changes}

    def test_context_registers_both_surfaces_and_real_sdk_tools(self):
        from hai_agents.tools import as_tools
        self.assertEqual(self.context.max_trials, 4)
        self.assertEqual(set(self.context.surfaces), {"desktop", "web"})
        with tempfile.TemporaryDirectory() as directory:
            tools = context_tools(Lab(Path(directory), self.context, extension=self.extension))
            self.assertEqual([tool.__name__ for tool in tools],
                             ["publish_update", "acknowledge_researcher_message", "record_fire_trial"])
            for tool in as_tools(tools):
                self.assertEqual(tool.definition()["input_schema"]["type"], "object")

    def test_incomplete_trials_are_excluded_without_losing_the_reading(self):
        for change in ({"completed": False}, {"fresh_setup": False}, {"settings_verified": False},
                       {"percent_burned": None}, {"ticks": 0}, {"density_percent": 70}):
            with self.subTest(change=change):
                self.assertEqual(self.extension.analyze_reading(self.reading(**change))["status"], "incomplete")
        with tempfile.TemporaryDirectory() as directory:
            lab = Lab(Path(directory), self.context, extension=self.extension)
            (record,) = self.extension.tools(lab)
            result = record(**self.reading(completed=False))
            self.assertTrue(result["recorded"])
            self.assertEqual(result["comparison"]["conditions"], {})
            self.assertFalse(lab.observations()[0]["reading"]["completed"])

    def test_rejects_invalid_numbers_ids_and_missing_evidence(self):
        for change in ({"density_percent": float("nan")}, {"percent_burned": 101},
                       {"ticks": -1}, {"ticks": 1.5}, {"percent_burned": True},
                       {"trial_id": "extra"}, {"evidence": []}, {"fresh_setup": "yes"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.extension.analyze_reading(self.reading(**change))

    def test_checked_comparison_repeats_retries_and_report(self):
        with tempfile.TemporaryDirectory() as directory:
            lab = Lab(Path(directory), self.context, "Synthetic question", self.extension)
            (record,) = self.extension.tools(lab)
            readings = [self.reading(), self.reading(trial_id="high-1", density_percent=70, percent_burned=90),
                        self.reading(trial_id="low-2", percent_burned=17.7),
                        self.reading(trial_id="high-2", density_percent=70, percent_burned=94)]
            for reading in readings:
                result = record(**reading)
            self.assertEqual(result["comparison"]["status"], "repeated_comparison")
            self.assertAlmostEqual(result["comparison"]["difference_percentage_points"], 77)
            self.assertEqual(result["comparison"]["conditions"]["55"]["count"], 2)
            record(**readings[0])
            self.assertEqual(len(lab.observations()), 4)
            with self.assertRaisesRegex(ValueError, "Conflicting retry"):
                record(**self.reading(percent_burned=9))
            lab.finish("Synthetic verification only")
            report = (Path(directory) / "report.md").read_text()
            self.assertIn("+77.00 percentage points", report)
            self.assertIn("observations/low-1.json", report)
            self.assertIn("no critical threshold or probability estimate", report)


if __name__ == "__main__":
    unittest.main()
