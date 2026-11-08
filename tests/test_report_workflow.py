"""Session activity, report delivery and scientific outcome are independent."""
from pathlib import Path
import tempfile
import unittest

from fastapi.testclient import TestClient

from jesse.conversation.application import RunManager
from jesse.conversation.web import create_app
from jesse.investigating.lab import Lab
from jesse.runtime import save_json


class Process:
    exit_code = None

    def poll(self):
        return self.exit_code


class ReportWorkflowTests(unittest.TestCase):
    def test_report_is_available_before_session_closes_and_refreshes_after_follow_up(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = RunManager(Path(directory))
            manager.current_id = "synthetic-run"
            manager.process = Process()
            folder = Path(directory) / manager.current_id
            lab = Lab(folder, "Synthetic question")
            save_json(folder, "session.json", {"id": "synthetic-session"})
            save_json(folder, "session-state.json", {"state": "running"})
            self.assertEqual(manager.snapshot(folder.name)["status"], "running")
            (folder / "agent-report.md").write_text("Synthetic first interpretation.")
            lab.record("first", {"x": 1})
            lab.finish("Answer is ready; review pending")
            save_json(folder, "session-state.json", {"state": "idle"})
            snapshot = manager.snapshot(folder.name)
            self.assertEqual(snapshot["status"], "report_ready")
            self.assertTrue(snapshot["active"])
            self.assertTrue(snapshot["can_message"])
            self.assertEqual(snapshot["outcome"]["outcome"], "inconclusive")
            client = TestClient(create_app(manager))
            report = client.get(snapshot["report_url"])
            self.assertEqual(report.status_code, 200)
            self.assertIn("Synthetic first interpretation", report.text)
            revision = snapshot["report_revision"]
            save_json(folder, "session-state.json", {"state": "running"})
            self.assertEqual(manager.snapshot(folder.name)["status"], "running")
            (folder / "agent-report.md").write_text("Synthetic revised interpretation.")
            lab.finish("Follow-up answered")
            save_json(folder, "session-state.json", {"state": "idle"})
            snapshot = manager.snapshot(folder.name)
            self.assertNotEqual(snapshot["report_revision"], revision)
            self.assertIn("Synthetic revised interpretation", client.get(snapshot["report_url"]).text)
            manager.process.exit_code = 0
            snapshot = manager.snapshot(folder.name)
            self.assertEqual(snapshot["status"], "inconclusive")
            self.assertFalse(snapshot["can_message"])
            self.assertTrue(snapshot["report_available"])

    def test_idle_without_a_report_and_worker_failure_do_not_claim_a_ready_report(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = RunManager(Path(directory))
            manager.current_id = "synthetic-run"
            manager.process = Process()
            folder = Path(directory) / manager.current_id
            folder.mkdir()
            save_json(folder, "session-state.json", {"state": "idle"})
            self.assertEqual(manager.snapshot(folder.name)["status"], "waiting")
            self.assertFalse(manager.snapshot(folder.name)["report_available"])
            manager.process.exit_code = 1
            snapshot = manager.snapshot(folder.name)
            self.assertEqual(snapshot["status"], "blocked")
            self.assertIsNone(snapshot["report_url"])

    def test_explicit_desktop_surface_reaches_the_existing_worker(self):
        commands = []

        def popen(command, **kwargs):
            commands.append(command)
            return Process()

        with tempfile.TemporaryDirectory() as directory:
            manager = RunManager(Path(directory), popen=popen, research=Path(directory) / "notes", surface="desktop")
            manager.start("Synthetic fire question")
            self.assertEqual(commands[0][commands[0].index("--surface") + 1], "desktop")
            self.assertEqual(commands[0][commands[0].index("--research") + 1], str((Path(directory) / "notes").resolve()))


if __name__ == "__main__":
    unittest.main()
