"""H API and filesystem implementations for desktop feasibility."""
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
import time

from jesse.recording.adapters import FileObservations
from jesse.recording.domain import Observation
from .ports import ExperimentRecords


def json_value(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if is_dataclass(value):
        return {key: json_value(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {key: json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_value(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()
    return value


class HDesktopAgent:
    def __init__(self, budget_seconds: int = 600, client: Any = None, surface: str = "desktop"):
        self.budget_seconds = budget_seconds
        self.client = client
        if surface not in {"desktop", "web"}:
            raise ValueError("Unsupported NetLogo surface")
        self.surface = surface

    def run(self, instructions: str, records: ExperimentRecords) -> tuple[dict, str]:
        from hai_agents import Client

        client = self.client or Client(timeout=30)

        def record_observation(
            observation_id: str, trial_id: str,
            volume: float | None, kc: float | None, kd: float | None,
            kr: float | None, pause: bool | None, value: float | None,
            unit: str | None, raw_reading: str, evidence: list[str],
            start_tick: float | None, end_tick: float | None,
            status: str, reason: str | None = None,
        ) -> dict:
            """Save a raw GUI reading immediately. Reuse IDs only for identical retries.

            Pass the observed controls as scalar arguments: volume is VOLUME,
            kc/kd/kr are Kc/Kd/Kr, pause is PAUSE?. start_tick and end_tick
            identify the observed interval. Unknown values/units are null. The
            controller supplies the timestamp, control labels and rate quantity.
            status is observed, unreadable or interrupted. Preserve raw displayed
            output and actual evidence references. Require recorded=true before
            continuing; after a failed correction stop and report the blocker.
            """
            observation = Observation(
                observation_id, trial_id, datetime.now(timezone.utc).isoformat(),
                {"VOLUME": volume, "Kc": kc, "Kd": kd, "Kr": kr, "PAUSE?": pause},
                "reaction velocity (V)", value, unit, raw_reading, evidence,
                {"start": start_tick, "end": end_tick, "unit": "ticks"}, status, reason,
            )
            return records.record_observation(observation)

        def analyze_measurements() -> dict:
            """Compare saved NetLogo rate readings using checked Python calculations.

            Call after recording the trials. The analysis checks conditions, units,
            independent trial IDs and intervals, excludes incomplete readings, and
            saves derived results separately. It cannot establish saturation.
            """
            return records.analyze_measurements()

        from .domain import WEB_LAUNCH_URL
        environment = (
            {"id": "netlogo-web", "kind": "web", "start_url": WEB_LAUNCH_URL, "mode": {"type": "visual", "width": 1280, "height": 900}}
            if self.surface == "web" else
            # host=user_device makes the SDK start the local desktop bridge; without it no bridge serves screenshots.
            {"id": "local-mac", "kind": "desktop", "host": "user_device", "shell": False}
        )
        handle = client.start_session(
            # Inline specs enable the SDK's automatic local desktop connection.
            agent={
                "name": f"jesse-netlogo-{self.surface}",
                "description": "Bounded NetLogo GUI feasibility test",
                "model": "holo4-27b",
                "environments": [environment],
            },
            messages=instructions, tools=[record_observation, analyze_measurements],
            max_time_s=self.budget_seconds,
        )
        try:
            records.session_started({"id": handle.id, "agent_view_url": None})
            metadata = handle.get()
            records.session_started({"id": handle.id, "agent_view_url": metadata.agent_view_url})
            for event in handle.stream(timeout_seconds=self.budget_seconds, wait_for_seconds=5):
                records.event_received(json_value(event))
            result = handle.wait_for_completion(timeout_seconds=15)
            payload = json_value(result)
            payload["agent_view_url"] = metadata.agent_view_url
            if result.status == "idle":
                try:
                    handle.cancel()
                    payload["cleanup"] = "cancelled_after_answer"
                except Exception as error:
                    payload["cleanup"] = f"cancellation_failed:{type(error).__name__}"
            return payload, str(result.answer or "No final answer was returned.")
        except BaseException:
            try:
                handle.cancel()
            except Exception:
                pass  # Preserve the original error; process exit closes the bridge.
            raise


class FileExperimentRecords:
    def __init__(self, folder: Path):
        self.folder = folder
        self.folder.mkdir(parents=True, exist_ok=True)
        self.observations = FileObservations(folder / "observations", folder.name)
        self.started = time.monotonic()
        self.first_event_seconds = None
        self.first_observation_seconds = None

    def _json(self, name: str, payload: dict) -> None:
        path = self.folder / name
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, indent=2, allow_nan=False), encoding="utf-8")
        temporary.replace(path)

    def session_started(self, session: dict) -> None:
        self._json("session.json", session)
        if session.get("agent_view_url"):
            print(f"Agent View: {session['agent_view_url']}", flush=True)

    def event_received(self, event: dict) -> None:
        if self.first_event_seconds is None:
            self.first_event_seconds = time.monotonic() - self.started
        with (self.folder / "events.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event, allow_nan=False) + "\n")
        print(f"H: {event.get('type', 'event')}", flush=True)

    def record_observation(self, observation: Observation) -> dict:
        # A retry keeps the original controller timestamp; the tool may be
        # delivered more than once even when its payload is unchanged.
        existing_path = self.folder / "observations" / f"{observation.observation_id}.json"
        if existing_path.exists():
            from dataclasses import replace
            original = json.loads(existing_path.read_text(encoding="utf-8"))
            observation = replace(observation, observed_at=original["observed_at"])
        result = self.observations.record(observation)
        if self.first_observation_seconds is None:
            self.first_observation_seconds = time.monotonic() - self.started
        self._metrics()
        return result

    def _metrics(self) -> None:
        previous_path = self.folder / "metrics.json"
        previous = json.loads(previous_path.read_text(encoding="utf-8")) if previous_path.exists() else {}
        event_path = self.folder / "events.jsonl"
        events = []
        if event_path.exists():
            for line in event_path.read_text(encoding="utf-8").splitlines():
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue  # A hard stop may leave the final event line partial.
        observations = [json.loads(path.read_text(encoding="utf-8")) for path in (self.folder / "observations").glob("*.json")]
        provider_metrics = next((event.get("data", {}).get("metrics") for event in reversed(events) if event.get("type") == "MetricsUpdateEvent"), None)
        self._json("metrics.json", {
            "elapsed_seconds": max(round(time.monotonic() - self.started, 3), previous.get("elapsed_seconds", 0)),
            "first_event_seconds": self.first_event_seconds if self.first_event_seconds is not None else previous.get("first_event_seconds"),
            "first_observation_seconds": self.first_observation_seconds if self.first_observation_seconds is not None else previous.get("first_observation_seconds"),
            "recorded_observations": len(observations),
            "readable_observations": sum(item["status"] == "observed" for item in observations),
            "event_count": len(events),
            "provider_metrics": provider_metrics,
        })

    def analyze_measurements(self) -> dict:
        from jesse.analyzing.adapters import FileAnalysisRecords
        from jesse.analyzing.application import analyze_measurements

        return analyze_measurements(FileAnalysisRecords(self.folder))

    def save(self, session: dict, report: str) -> None:
        self._json("session.json", session)
        (self.folder / "agent-report.md").write_text(report, encoding="utf-8")

    def finish(self, outcome: str, reason: str) -> None:
        if outcome not in {"blocked", "inconclusive", "supported_conclusion"}:
            raise ValueError("Invalid investigation outcome")
        self._json("outcome.json", {
            "run_id": self.folder.name, "outcome": outcome, "reason": reason,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "verification": "pending_replay_review" if (self.folder / "session.json").exists() else "not_started",
        })
        self._metrics()
        self._evidence_index()
        evidence = ["- [Session metadata](session.json)"] if (self.folder / "session.json").exists() else []
        if (self.folder / "events.jsonl").exists():
            evidence.append("- [Session events](events.jsonl)")
            evidence.append("- [Observation-to-event index](evidence-index.json)")
        for path in sorted((self.folder / "observations").glob("*.json")):
            evidence.append(f"- [Observation {path.stem}](observations/{path.name})")
        for path in sorted((self.folder / "analyses").glob("*.md")):
            evidence.append(f"- [Python rate comparison](analyses/{path.name})")
        report = (
            f"# NetLogo interaction feasibility\n\nOutcome: **{outcome}**\n\n{reason}\n\n"
            "## Planned method\n\nTwo GUI trials with different substrate settings and fixed reaction constants. "
            "See the supplied protocol and session record for actual actions.\n\n"
            "## Evidence\n\n" + ("\n".join(evidence) or "No session evidence was recorded.") + "\n\n"
            "## Verification\n\nPending replay review: check parameter change, simulation execution, "
            "readable rates, corresponding settings and evidence for both trials. "
            "A finished API session alone does not establish feasibility or saturation.\n"
        )
        if (self.folder / "agent-report.md").exists():
            report += "\n## Agent account\n\n[Unverified observations and interpretation](agent-report.md).\n"
        (self.folder / "report.md").write_text(report, encoding="utf-8")

    def _evidence_index(self) -> None:
        path = self.folder / "events.jsonl"
        if not path.exists():
            return
        session_path = self.folder / "session.json"
        session = json.loads(session_path.read_text(encoding="utf-8")) if session_path.exists() else {}
        index = {}
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            for call in (event.get("data") or {}).get("pending_tool_calls") or []:
                if call.get("tool_name") == "record_observation":
                    observation_id = call.get("args", {}).get("observation_id")
                    if observation_id:
                        index.setdefault(observation_id, {
                            "session_id": session.get("id"), "agent_view_url": session.get("agent_view_url"),
                            "events_file": "events.jsonl", "line": line_number,
                            "event_timestamp": event.get("timestamp"), "tool_call_id": call.get("id"),
                            "verification": "pending_replay_review",
                        })
        self._json("evidence-index.json", index)
