"""Past investigations are listed for the panel sidebar. All runs here are synthetic fixtures."""
import json
from pathlib import Path
import tempfile
import unittest

from fastapi.testclient import TestClient

from jesse.research import load_notes
from jesse.conversation.application import RunManager
from jesse.conversation.web import create_app

REPO_NOTES = Path(__file__).resolve().parents[1] / "research"


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
            client = TestClient(create_app(RunManager(root, research=REPO_NOTES)))
            runs = client.get("/api/runs").json()["runs"]
            self.assertEqual(runs[0]["run_id"], "coolant-20261107T133401102674Z")
            self.assertEqual(client.get(f"/api/runs/{runs[0]['run_id']}").status_code, 200)
            self.assertEqual(client.get("/api/runs/..%2Fescape").status_code, 404)

    def test_api_lists_research_notes_and_skips_the_template(self):
        with tempfile.TemporaryDirectory() as directory:
            notes = TestClient(create_app(RunManager(Path(directory), research=REPO_NOTES))).get("/api/research").json()["notes"]
        ids = [note["id"] for note in notes]
        self.assertIn("mechanics", ids)
        self.assertNotIn("_template", ids)
        self.assertTrue(all(note["title"] for note in notes))

    def test_note_title_comes_from_its_heading(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "optics.md").write_text("Intro line\n\n# Optics bench\n\n## Usual tools\n")
            (root / "plain-notes.md").write_text("No heading here.")
            (root / "_draft.md").write_text("# Ignored")
            notes = load_notes(root)
        self.assertEqual([(note.id, note.title) for note in notes], [("optics", "Optics bench"), ("plain-notes", "Plain notes")])

if __name__ == "__main__":
    unittest.main()
