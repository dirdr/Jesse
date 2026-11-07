"""Live view parsing. All events and readings here are synthetic fixtures."""
import json
from pathlib import Path
import tempfile
import unittest

from jesse.conversation.live import cached_frame, live_state


def write_events(folder: Path, events: list[dict]) -> None:
    (folder / "events.jsonl").write_text("\n".join(json.dumps(event) for event in events) + "\n{partial", encoding="utf-8")


def observation(source: str) -> dict:
    return {"type": "AgentEvent", "timestamp": "2026-11-07T12:00:00Z", "data": {
        "kind": "observation_event", "image": {"source": source, "type": "url"},
        "metadata": {"viewport_size": [1920, 1080], "cursor_position": [10, 20]}}}


class LiveViewTests(unittest.TestCase):
    def test_actions_link_to_frames_and_hide_private_reasoning(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            write_events(folder, [
                observation("https://agp.eu.hcompany.ai/frame-0.jpg"),
                {"type": "AgentEvent", "timestamp": "2026-11-07T12:00:01Z", "data": {
                    "kind": "policy_event", "content": "Click setup.", "reasoning_content": "PRIVATE",
                    "tool_reqs": [{"tool_name": "click_desktop", "args": {"x": 0.5, "y": 0.25, "element": "setup", "evidence": ["x"]}},
                                  {"tool_name": "update_plan", "args": {"goals": [{"title": "Run trial", "status": "running"}]}},
                                  {"tool_name": "answer", "args": {"content": "report"}}]}},
                {"type": "MetricsUpdateEvent", "timestamp": "2026-11-07T12:00:02Z", "data": {"metrics": {"steps": 3, "total_cost": 0.01}}},
            ])
            state = live_state(folder)
            self.assertEqual(state["frames"][0]["viewport"], [1920, 1080])
            self.assertEqual([action["tool"] for action in state["actions"]], ["click_desktop", "update_plan"])
            self.assertEqual(state["actions"][0]["frame"], 0)
            self.assertEqual(state["actions"][0]["args"], {"x": 0.5, "y": 0.25, "element": "setup"})
            self.assertEqual(state["plan"], [{"title": "Run trial", "status": "running"}])
            self.assertEqual(state["steps"], 3)
            self.assertNotIn("PRIVATE", json.dumps(state))

    def test_measurements_from_display_and_legacy_coolant_formats(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / "observations").mkdir()
            (folder / "observations" / "t1.json").write_text(json.dumps({
                "trial_id": "t1", "recorded_at": "2026-11-07T12:00:00Z", "reading": {"x": 1.0},
                "display": {"fields": {"x": "1.0 synthetic unit"}, "result": "2.0 derived", "status": "estimated"}}))
            (folder / "observations" / "c1.json").write_text(json.dumps({
                "recorded_at": "2026-11-07T12:00:00Z", "reading": {"trial_id": "c1", "coolant_volume_ml": 10,
                "coolant_initial_c": 20, "water_volume_ml": 20, "water_initial_c": 80, "final_c": 50}}))
            (folder / "analysis-c1.json").write_text(json.dumps({"status": "estimated", "specific_heat_j_g_c": 1.5}))
            rows = {row["id"]: row for row in live_state(folder)["measurements"]}
            self.assertEqual(rows["t1"]["result"], "2.0 derived")
            self.assertEqual(rows["t1"]["fields"], {"x": "1.0 synthetic unit"})
            self.assertEqual(rows["c1"]["result"], "1.500 J/(g·°C)")

    def test_frames_are_fetched_once_and_only_from_h_hosts(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            write_events(folder, [observation("https://agp.eu.hcompany.ai/a.jpg"), observation("https://evil.example/b.jpg")])
            calls = []
            fetch = lambda url: calls.append(url) or b"jpeg"
            self.assertEqual(cached_frame(folder, 0, fetch).read_bytes(), b"jpeg")
            cached_frame(folder, 0, fetch)
            self.assertEqual(len(calls), 1)
            self.assertIsNone(cached_frame(folder, 1, fetch))
            self.assertIsNone(cached_frame(folder, 9, fetch))


if __name__ == "__main__":
    unittest.main()
