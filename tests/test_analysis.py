"""Synthetic analysis fixtures; these do not establish simulator behavior."""
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest

from jesse.analyzing.adapters import FileAnalysisRecords
from jesse.analyzing.application import analyze_measurements
from jesse.analyzing.domain import compare_rates
from jesse.experiments.netlogo.adapters import FileExperimentRecords
from jesse.recording.domain import Observation


def reading(identifier="low", volume=50, value=2.0, **changes):
    values = dict(
        observation_id=identifier, trial_id=identifier,
        observed_at="2026-11-07T12:00:00Z",
        settings={"VOLUME": volume, "Kc": 80, "Kd": 62, "Kr": 10, "PAUSE?": True},
        quantity="reaction velocity (V)", value=value, unit="simulator rate units",
        raw_reading=f"Synthetic fixture: {value}", evidence=["synthetic:test-event"],
        interval={"start": 0, "end": 30, "unit": "ticks"}, status="observed", reason=None,
    )
    return Observation(**(values | changes))


class RateAnalysisTests(unittest.TestCase):
    def test_compares_rates_without_claiming_significance_or_saturation(self):
        result = compare_rates([reading(), reading("high", 100, 3)])
        self.assertEqual(result["status"], "compared")
        self.assertEqual(result["comparison"]["rate_difference"], 1)
        self.assertEqual(result["comparison"]["rate_ratio"], 1.5)
        self.assertEqual(result["suggested_follow_up"]["kind"], "repeat")
        self.assertEqual(result["derived_values"][0]["repeat_count"], 1)
        self.assertIsNone(result["derived_values"][0]["sample_standard_deviation"])

    def test_mismatched_conditions_and_unknown_units_prevent_comparison(self):
        high = reading("high", 100, 3)
        for modified in (
            replace(high, settings=high.settings | {"Kr": 20}),
            replace(high, interval={"start": 0, "end": 60, "unit": "ticks"}),
            replace(high, unit=None), replace(high, unit="different units"),
            replace(high, quantity="temperature"),
            replace(high, settings=high.settings | {"PAUSE?": False}),
        ):
            with self.subTest(modified=modified):
                result = compare_rates([reading(), modified])
                self.assertEqual(result["status"], "not_comparable")
                self.assertIsNone(result["comparison"])

    def test_incomplete_readings_are_excluded_with_reasons(self):
        unknown = reading("unknown", 100, None, status="unreadable", reason="Synthetic unreadable plot")
        result = compare_rates([reading(), unknown])
        self.assertEqual(result["status"], "insufficient_data")
        self.assertEqual(result["excluded_observations"][0]["observation_id"], "unknown")
        self.assertEqual(result["included_observation_ids"], ["low"])

    def test_multiple_readings_from_one_trial_are_not_independent_repeats(self):
        duplicate_trial = reading("second-reading", trial_id="low")
        result = compare_rates([reading(), duplicate_trial, reading("high", 100, 3)])
        self.assertEqual(result["status"], "not_comparable")

    def test_independent_repeats_are_summarized(self):
        result = compare_rates([reading(), reading("low-repeat", value=4), reading("high", 100, 6), reading("high-repeat", 100, 8)])
        self.assertEqual(result["derived_values"][0]["mean_rate"], 3)
        self.assertEqual(result["derived_values"][1]["mean_rate"], 7)
        self.assertAlmostEqual(result["derived_values"][0]["sample_standard_deviation"], 2 ** 0.5)
        self.assertEqual(result["suggested_follow_up"]["kind"], "review_evidence")

    def test_zero_baseline_does_not_produce_infinite_ratio(self):
        result = compare_rates([reading(value=0), reading("high", 100, 3)])
        self.assertIsNone(result["comparison"]["rate_ratio"])
        json.dumps(result, allow_nan=False)

    def test_analysis_identity_is_independent_of_input_order(self):
        low, high = reading(), reading("high", 100, 3)
        self.assertEqual(compare_rates([low, high]), compare_rates([high, low]))

    def test_empty_run_produces_an_explicit_incomplete_result(self):
        self.assertEqual(compare_rates([])["status"], "insufficient_data")

    def test_file_path_preserves_raw_observations_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            records = FileExperimentRecords(folder)
            records.record_observation(reading())
            records.record_observation(reading("high", 100, 3))
            before = {path.name: path.read_bytes() for path in (folder / "observations").glob("*.json")}
            first = records.analyze_measurements()
            second = analyze_measurements(FileAnalysisRecords(folder))
            self.assertEqual(first, second)
            self.assertEqual(len(list((folder / "analyses").glob("*.json"))), 1)
            self.assertEqual(before, {path.name: path.read_bytes() for path in (folder / "observations").glob("*.json")})
            report = next((folder / "analyses").glob("*.md")).read_text()
            self.assertIn("../observations/low.json", report)
            records.finish("inconclusive", "Synthetic run")
            self.assertIn("Python rate comparison", (folder / "report.md").read_text())

    def test_cross_run_observations_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            records = FileExperimentRecords(folder)
            records.record_observation(reading())
            path = folder / "observations/low.json"
            payload = json.loads(path.read_text())
            payload["run_id"] = "another-run"
            path.write_text(json.dumps(payload))
            with self.assertRaisesRegex(ValueError, "different run"):
                analyze_measurements(FileAnalysisRecords(folder))
