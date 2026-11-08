"""Synthetic pendulum readings exercise the real context extension, not simulator findings."""
import math
from pathlib import Path
import tempfile
import unittest

from jesse.contexts import find_context, load_extension
from jesse.investigating.lab import Lab
from jesse.investigating.runner import context_tools

CONTEXTS = Path(__file__).resolve().parents[1] / "contexts"
G = 14.2


def period(length, angle=0.0):
    return 2 * math.pi * math.sqrt(length / G) * (1 + (math.radians(angle) ** 2) / 16)


class PendulumContextTests(unittest.TestCase):
    def setUp(self):
        self.context = find_context("phet-pendulum", CONTEXTS)
        self.extension = load_extension(self.context)

    def reading(self, trial_id, length, mass=1.0, angle=8.0, **changes):
        return {"trial_id": trial_id, "length_m": length, "mass_kg": mass, "angle_deg": angle,
                "period_s": round(period(length, angle), 4), "planet_x": True, "friction_none": True,
                "raw_reading": f"Synthetic fixture: L {length} m", "evidence": ["synthetic:readout"], **changes}

    def record(self, lab, *readings):
        tool = context_tools(lab)[-1]
        return [tool(**reading) for reading in readings]

    def test_registers_web_surface_and_tool(self):
        with tempfile.TemporaryDirectory() as directory:
            names = [tool.__name__ for tool in context_tools(Lab(Path(directory), self.context, extension=self.extension))]
        self.assertEqual(names[-1], "record_pendulum_trial")
        self.assertEqual(set(self.context.surfaces), {"web"})

    def test_fit_recovers_gravity_and_decides_outcome_in_python(self):
        with tempfile.TemporaryDirectory() as directory:
            lab = Lab(Path(directory), self.context, extension=self.extension)
            self.record(lab, self.reading("fit-1", 0.30), self.reading("fit-2", 0.50),
                        self.reading("fit-3", 0.70), self.reading("fit-4", 0.95),
                        self.reading("mass", 0.95, mass=0.2))
            fit = self.extension.fit_gravity(lab.analyses())
            self.assertAlmostEqual(fit["g"], G, delta=0.05)
            self.assertGreater(fit["r2"], 0.999)
            self.assertLess(abs(fit["mass_effect"]), 0.005)
            first = lab.finish("done")
            report = (Path(directory) / "report.md").read_text()
            self.assertEqual(first, "supported_conclusion")
            self.assertEqual(lab.finish("done"), first)
            self.assertEqual((Path(directory) / "report.md").read_text(), report)

    def test_too_few_trials_or_bad_conditions_stay_inconclusive(self):
        with tempfile.TemporaryDirectory() as directory:
            lab = Lab(Path(directory), self.context, extension=self.extension)
            self.record(lab, self.reading("fit-1", 0.30), self.reading("fit-2", 0.50, planet_x=False))
            self.assertEqual(self.extension.outcome(lab)[0], "inconclusive")
            self.assertEqual(lab.finish("done"), "inconclusive")

    def test_large_angle_fit_trial_is_excluded(self):
        analysis = self.extension.analyze_reading(self.reading("fit-1", 0.5, angle=40))
        self.assertEqual(analysis["status"], "incomplete")
        amplitude = self.extension.analyze_reading(self.reading("amplitude", 0.95, angle=60))
        self.assertEqual(amplitude["status"], "measured")


if __name__ == "__main__":
    unittest.main()
