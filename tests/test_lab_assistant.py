"""The generic tools turn recorded readings into traceable analyses; synthetic values only."""
import math
from pathlib import Path
import tempfile
import unittest

from jesse.investigating.lab import Lab
from jesse.investigating.runner import build_prompt, environment
from jesse.investigating.tools import agent_tools
from jesse.research import SEARCH_URL, load_notes

REPO_NOTES = Path(__file__).resolve().parents[1] / "research"


def tools(lab):
    return {tool.__name__: tool for tool in agent_tools(lab)}


class LabAssistantTests(unittest.TestCase):
    def test_fit_uses_only_recorded_observed_values(self):
        with tempfile.TemporaryDirectory() as directory:
            lab = Lab(Path(directory), "What is g on Planet X?")
            tool = tools(lab)
            for index, length in enumerate((0.3, 0.5, 0.7, 0.95), start=1):
                period = 2 * math.pi * math.sqrt(length / 14.2)
                tool["record_observation"](f"fit-{index}", {"length_m": length, "period_s": period},
                                           {"length_m": "m", "period_s": "s"}, f"L {length} m", ["synthetic"])
            tool["record_observation"]("bad", {"length_m": 0.4, "period_s": None}, {}, "unreadable", ["synthetic"],
                                       status="unreadable")
            result = tool["analyze_readings"]("gravity", "length_m", "period_s", y_power=2, through_origin=True)
            self.assertEqual(result["trials"], ["fit-1", "fit-2", "fit-3", "fit-4"])
            self.assertAlmostEqual(4 * math.pi ** 2 / result["slope"], 14.2, places=6)
            self.assertGreater(result["r2"], 0.9999)
            self.assertTrue((Path(directory) / "analyses" / "gravity.json").exists())
            lab.finish("done")
            self.assertIn("## Analysis", (Path(directory) / "report.md").read_text())

    def test_fit_needs_two_trials(self):
        with tempfile.TemporaryDirectory() as directory:
            lab = Lab(Path(directory), "Q")
            tool = tools(lab)
            tool["record_observation"]("one", {"x": 1, "y": 2}, {}, "x 1 y 2", ["synthetic"])
            with self.assertRaisesRegex(ValueError, "at least two"):
                tool["analyze_readings"]("fit", "x", "y")

    def test_prompt_carries_question_notes_and_search_start(self):
        notes = load_notes(REPO_NOTES)
        prompt = build_prompt(notes, "web", "What is g on Planet X?")
        self.assertIn("What is g on Planet X?", prompt)
        self.assertIn("PhET Pendulum Lab", prompt)
        self.assertIn("Propose before you act", prompt)
        self.assertEqual(environment("web")["start_url"], SEARCH_URL)
        self.assertEqual(environment("desktop")["host"], "user_device")


if __name__ == "__main__":
    unittest.main()
