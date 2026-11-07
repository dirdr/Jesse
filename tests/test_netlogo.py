import tempfile
import unittest
import json
from pathlib import Path
from jesse.experiments.netlogo.application import run_experiment
from jesse.experiments.netlogo.adapters import FileExperimentRecords

class ExperimentTests(unittest.TestCase):
    def test_preserves_observed_session_and_report(self):
        class Agent:
            def run(self, instructions):
                return {'status': 'completed', 'id': 'trial-session'}, '# Observations\nMeasured rate: 2'
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            run_experiment(Agent(), FileExperimentRecords(folder))
            self.assertEqual(json.loads((folder / 'session.json').read_text())['id'], 'trial-session')
            self.assertIn('Measured rate: 2', (folder / 'report.md').read_text())

    def test_provider_failure_does_not_generate_findings(self):
        class Agent:
            def run(self, instructions):
                raise RuntimeError('Desktop unavailable')
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            with self.assertRaises(RuntimeError):
                run_experiment(Agent(), FileExperimentRecords(folder))
            self.assertEqual(list(folder.iterdir()), [])
