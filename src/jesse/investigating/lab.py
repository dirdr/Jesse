"""Investigation records shared by built-in and context tools."""
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from types import ModuleType

from jesse.contexts import ResearchContext
from jesse.runtime import conversation_event, save_json

SAFE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}")
UPDATE_KINDS = {"plan", "finding", "follow_up", "blocker"}
ACK_STATUSES = {"acknowledged", "applied", "rejected"}


def _read(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


class Lab:
    """What a context's tools.py receives: the run folder plus safe record helpers."""

    def __init__(self, folder: Path, context: ResearchContext, question: str = "", extension: ModuleType | None = None):
        self.folder = folder
        self.context = context
        self.question = question
        self.extension = extension
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "observations").mkdir(exist_ok=True)
        (folder / "analyses").mkdir(exist_ok=True)

    def say(self, kind: str, text: str, *, speak: bool = False) -> None:
        conversation_event(self.folder, kind, text, speak=speak)

    def record(self, trial_id: str, reading: dict, *, analysis: dict | None = None,
               fields: dict[str, str] | None = None, result: str | None = None, summary: str | None = None) -> dict:
        """Save a raw reading once, enforce the trial limit and store derived values separately."""
        if not SAFE_ID.fullmatch(trial_id):
            raise ValueError("Use a stable safe trial identifier")
        path = self.folder / "observations" / f"{trial_id}.json"
        status = (analysis or {}).get("status", "recorded")
        if path.exists():
            if _read(path, {}).get("reading") != reading:
                raise ValueError("Conflicting retry: preserve the original trial")
        else:
            if len(list(path.parent.glob("*.json"))) >= self.context.max_trials:
                raise ValueError(f"The {self.context.max_trials}-trial limit has been reached")
            display = {"fields": {key: str(value) for key, value in (fields or {}).items()}, "result": result, "status": status}
            save_json(path.parent, path.name, {"trial_id": trial_id, "recorded_at": datetime.now(timezone.utc).isoformat(),
                                               "reading": reading, "display": display})
            self.say("measurement", summary or f"Saved {trial_id}.", speak=True)
        if analysis is not None:
            save_json(self.folder / "analyses", f"{trial_id}.json", analysis)
        return {"recorded": True, **(analysis or {})}

    def observations(self) -> list[dict]:
        return [_read(path, {}) for path in sorted((self.folder / "observations").glob("*.json"))]

    def analyses(self) -> list[dict]:
        return [_read(path, {}) for path in sorted((self.folder / "analyses").glob("*.json"))]

    def update(self, update_id: str, kind: str, text: str) -> dict:
        if kind not in UPDATE_KINDS or not 1 <= len(text.strip()) <= 1000:
            raise ValueError("Supply an allowed kind and 1–1000 characters")
        if not SAFE_ID.fullmatch(update_id):
            raise ValueError("Use a safe update identifier")
        updates = self.folder / "updates"
        updates.mkdir(exist_ok=True)
        path = updates / f"{update_id}.json"
        payload = {"kind": kind, "text": text}
        if path.exists():
            if _read(path) != payload:
                raise ValueError("Conflicting update retry")
        else:
            self.say(kind, text, speak=True)
            save_json(updates, path.name, payload)
        return {"published": True}

    def acknowledge(self, event_id: str, status: str, text: str) -> dict:
        if not SAFE_ID.fullmatch(event_id) or status not in ACK_STATUSES or not 1 <= len(text.strip()) <= 1000:
            raise ValueError("Invalid researcher acknowledgement")
        messages = self.folder / "messages"
        if not (messages / f"{event_id}.json").exists():
            raise ValueError("Unknown researcher message ID")
        receipt = messages / f"{event_id}-{status}.json"
        if not receipt.exists():
            conversation_event(self.folder, status, text, speak=True, message_id=event_id)
            save_json(messages, receipt.name, {"status": status, "text": text})
        return {"recorded": True, "status": status}

    def finish(self, reason: str) -> str:
        observations = self.observations()
        outcome = "inconclusive" if observations else "blocked"
        save_json(self.folder, "outcome.json", {"outcome": outcome, "reason": reason, "context": self.context.id,
                  "recorded_trials": len(observations), "verification": "pending_replay_review"})
        (self.folder / "report.md").write_text(self._report(outcome, reason, observations), encoding="utf-8")
        return outcome

    def _report(self, outcome: str, reason: str, observations: list[dict]) -> str:
        context = self.context
        lines = [f"# {context.title}", ""]
        if self.question:
            lines += [f"Question: {self.question}", ""]
        lines += [f"Outcome: **{outcome}**", "", reason, "", "## Measurements", ""]
        if observations:
            lines += ["| Trial | Readings | Result | Status |", "| --- | --- | --- | --- |"]
            for item in observations:
                display = item.get("display") or {}
                readings = "; ".join(f"{key}: {value}" for key, value in (display.get("fields") or {}).items()) or "See raw reading"
                lines.append(f"| {item.get('trial_id')} | {readings} | {display.get('result') or 'Not calculated'} | {display.get('status', 'recorded')} |")
        else:
            lines.append("No measurement was recorded.")
        section = getattr(self.extension, "report", None)
        if callable(section):
            lines += ["", section(self).strip()]
        if context.assumptions:
            lines += ["", "## Assumptions", "", *[f"- {item}" for item in context.assumptions]]
        lines += ["", "## Verification", "",
                  "Replay review is pending. Agent-reported readings must be checked against the session replay before a conclusion is accepted. Findings concern the configured simulator.",
                  "", "## Evidence", ""]
        for item in observations:
            trial = item.get("trial_id")
            link = f"- [{trial}: raw reading](observations/{trial}.json)"
            if (self.folder / "analyses" / f"{trial}.json").exists():
                link += f" · [Analysis](analyses/{trial}.json)"
            lines.append(link)
        links = ["[Protocol](protocol.md)", *[f"[Source]({url})" for url in context.sources]]
        session = _read(self.folder / "session.json", {})
        if session.get("agent_view_url"):
            links.append(f"[H session and replay]({session['agent_view_url']})")
        lines += ["", " · ".join(links), ""]
        return "\n".join(lines)
