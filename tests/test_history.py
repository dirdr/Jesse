"""Past investigations are listed for the panel sidebar. All runs here are synthetic fixtures."""
import json
from pathlib import Path
import tempfile
import unittest

from fastapi.testclient import TestClient

from jesse.contexts import load_context
from jesse.conversation.application import RunManager
from jesse.conversation.web import create_app

REPO_CONTEXTS = Path(__file__).resolve().parents[1] / "contexts"


def write_run(root: Path, name: str, question: str, started: str, outcome: str | None = None) -> Path:
    folder = root / name
    folder.mkdir()
    (folder / "request.json").write_text(json.dumps({"question": question, "started_at": started}))
    (folder / "run.json").write_text(json.dumps({"experiment": "chemcollective-coolant", "title": "Engine coolant heat capacity", "surface": "web"}))
    if outcome:
        (folder / "outcome.json").write_text(json.dumps({"outcome": outcome}))
        (folder / "report.md").write_text("# Report\n")
    return folder


class HistoryTests(unittest.TestCase):
    def test_history_lists_newest_first_and_skips_unrelated_folders(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_run(root, "20261107T100000Z", "Older question", "2026-11-07T10:00:00+00:00", "inconclusive")
            write_run(root, "a" * 32, "Newer question", "2026-11-07T12:00:00+00:00")
            (root / "notes").mkdir()
            rows = RunManager(root).history()
            self.assertEqual([row["question"] for row in rows], ["Newer question", "Older question"])
            self.assertEqual(rows[1]["outcome"], "inconclusive")
            self.assertTrue(rows[1]["report_available"])
            self.assertEqual(rows[0]["title"], "Engine coolant heat capacity")

    def test_api_lists_runs_and_opens_timestamp_named_runs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_run(root, "coolant-20261107T133401102674Z", "Coolant?", "2026-11-07T13:34:01+00:00", "inconclusive")
            client = TestClient(create_app(RunManager(root, contexts=REPO_CONTEXTS)))
            runs = client.get("/api/runs").json()["runs"]
            self.assertEqual(runs[0]["run_id"], "coolant-20261107T133401102674Z")
            self.assertEqual(client.get(f"/api/runs/{runs[0]['run_id']}").status_code, 200)
            self.assertEqual(client.get("/api/runs/..%2Fescape").status_code, 404)

    def test_api_lists_contexts_and_respects_a_pinned_context(self):
        with tempfile.TemporaryDirectory() as directory:
            pinned = TestClient(create_app(RunManager(Path(directory), context="chemcollective-coolant", contexts=REPO_CONTEXTS))).get("/api/contexts").json()
            self.assertEqual(pinned["pinned"], "chemcollective-coolant")
            self.assertEqual([item["experiment_id"] for item in pinned["contexts"]], ["chemcollective-coolant"])
            self.assertTrue(pinned["contexts"][0]["supported_questions"])

    def test_pinned_panel_passes_the_context_to_the_worker(self):
        commands = []

        class Process:
            def poll(self):
                return None

        def popen(command, **kwargs):
            commands.append(command)
            return Process()

        with tempfile.TemporaryDirectory() as directory:
            RunManager(Path(directory), popen=popen, context="chemcollective-coolant", contexts=REPO_CONTEXTS).start("Coolant?")
        self.assertIn("--context", commands[0])
        self.assertEqual(commands[0][commands[0].index("--context") + 1], "chemcollective-coolant")
        self.assertNotIn("--surface", commands[0])

    def test_template_context_is_valid_once_copied(self):
        self.assertEqual(load_context(REPO_CONTEXTS / "_template").id, "my-lab")


if __name__ == "__main__":
    unittest.main()
