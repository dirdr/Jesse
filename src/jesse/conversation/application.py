"""Own one local worker; send messages to its existing H session only."""
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import threading
from datetime import datetime, timezone
from uuid import uuid4

from jesse.runtime import conversation_event, save_json


def read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}")
MAX_HISTORY = 100


def run_summary(folder: Path) -> dict | None:
    request = read_json(folder / "request.json") or read_json(folder / "run.json")
    if not isinstance(request, dict) or not request.get("question"):
        return None
    run = read_json(folder / "run.json", {}) or {}
    selection = read_json(folder / "selection.json", {}) or {}
    outcome = read_json(folder / "outcome.json", {}) or {}
    started = request.get("started_at")
    if not started:
        started = datetime.fromtimestamp((folder / "request.json" if (folder / "request.json").exists() else folder).stat().st_mtime, timezone.utc).isoformat()
    return {"run_id": folder.name, "question": request["question"], "started_at": started,
            "context": run.get("experiment") or selection.get("experiment_id") or request.get("context"),
            "title": run.get("title"), "surface": run.get("surface") or selection.get("surface"),
            "outcome": outcome.get("outcome"), "report_available": (folder / "report.md").exists()}


class RunManager:
    def __init__(self, root: Path, *, popen=subprocess.Popen, send_message=None,
                 context: str | None = None, contexts: Path | None = None):
        self.root = root.resolve()
        self.context = context
        self.contexts = contexts.resolve() if contexts else None
        self.root.mkdir(parents=True, exist_ok=True)
        self.popen = popen
        self.send_message = send_message or self._send_message
        self.process = None
        self.current_id = None
        self.lock = threading.Lock()

    def folder(self, run_id: str) -> Path:
        if not RUN_ID.fullmatch(run_id):
            raise ValueError("Invalid investigation ID")
        path = self.root / run_id
        if not path.is_dir() or path.is_symlink():
            raise FileNotFoundError("Investigation not found")
        return path

    def start(self, question: str) -> str:
        with self.lock:
            if self.process is not None and self.process.poll() is None:
                raise ValueError("An investigation is already active. Stop it before starting another.")
            run_id = uuid4().hex
            folder = self.root / run_id
            folder.mkdir()
            conversation_event(folder, "question", question, author="researcher")
            try:
                with (folder / "worker.log").open("w", encoding="utf-8") as log:
                    command = [sys.executable, "-m", "jesse.selecting.cli", question,
                               "--timeout", "600", "--interactive", "--run-dir", str(folder)]
                    if self.context:
                        command += ["--context", self.context]
                    if self.contexts:
                        command += ["--contexts", str(self.contexts)]
                    self.process = self.popen(command, stdout=log, stderr=log, start_new_session=True)
            except Exception:
                save_json(folder, "outcome.json", {"outcome": "blocked", "reason": "The investigation worker could not start."})
                raise
            self.current_id = run_id
            return run_id

    def history(self) -> list[dict]:
        rows = []
        for folder in self.root.iterdir():
            if folder.is_dir() and not folder.is_symlink() and RUN_ID.fullmatch(folder.name):
                summary = run_summary(folder)
                if summary:
                    summary["active"] = folder.name == self.current_id and self.process is not None and self.process.poll() is None
                    rows.append(summary)
        rows.sort(key=lambda row: row["started_at"], reverse=True)
        return rows[:MAX_HISTORY]

    def snapshot(self, run_id: str) -> dict:
        folder = self.folder(run_id)
        active = run_id == self.current_id and self.process is not None and self.process.poll() is None
        session = read_json(folder / "session.json", {})
        outcome = read_json(folder / "outcome.json")
        state = read_json(folder / "session-state.json", {}).get("state")
        events = []
        path = folder / "conversation.jsonl"
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue  # Ignore an unfinished concurrent append until next poll.
        report = folder / "report.md"
        status = ("waiting" if state == "idle" else "running" if session.get("id") else "planning") if active else (outcome or {}).get("outcome", "blocked")
        if not active and outcome is None:
            outcome = {"outcome": "blocked", "reason": "The worker is no longer running. Inspect the local worker log; no scientific conclusion was accepted."}
        return {"run_id": run_id, "active": active, "status": status,
                "can_message": active and bool(session.get("id")),
                "agent_view_url": session.get("agent_view_url"), "events": events,
                "outcome": outcome, "report_available": report.exists(),
                "report_url": f"/api/runs/{run_id}/report" if report.exists() else None,
                "selection": read_json(folder / "selection.json")}

    def message(self, run_id: str, event_id: str, text: str, source: str) -> dict:
        # Persist before network delivery. A retry reuses the receipt and never
        # guesses whether a failed HTTP request was received by H.
        with self.lock:
            folder = self.folder(run_id)
            messages = folder / "messages"
            messages.mkdir(exist_ok=True)
            path = messages / f"{event_id}.json"
            existing = read_json(path)
            if existing:
                if existing["text"] != text or existing["source"] != source:
                    raise ValueError("Conflicting retry for this message ID")
                return existing
            state = self.snapshot(run_id)
            if not state["can_message"]:
                raise ValueError("Wait for the laboratory session to open, or start a new investigation if it has ended.")
            session_id = read_json(folder / "session.json", {})["id"]
            payload = {"event_id": event_id, "text": text, "source": source, "status": "sending", "run_id": run_id}
            save_json(messages, path.name, payload)
            conversation_event(folder, "question", text, author="researcher", message_id=event_id)
        try:
            self.send_message(session_id, f"Researcher message ID {event_id}:\n{text}\nAcknowledge this message using its ID. Keep the approved protocol, trial limit and original time budget; verify any change before marking it applied.")
            payload["status"] = "delivered"
            note = "Your message reached the experiment session. Jesse will confirm its response separately."
        except Exception as error:
            payload["status"] = "delivery_unknown"
            payload["error_type"] = type(error).__name__
            note = "Message delivery could not be confirmed. It has not been marked as applied."
        save_json(messages, path.name, payload)
        conversation_event(folder, payload["status"], note, author="controller", message_id=event_id)
        return payload

    @staticmethod
    def _send_message(session_id: str, text: str):
        from hai_agents import Client
        from hai_agents.sessions import SendSessionMessagesRequestBody_UserMessage
        Client(timeout=15).sessions.send_session_messages(session_id,
            request=SendSessionMessagesRequestBody_UserMessage(type="user_message", message=text))

    def stop(self, run_id: str) -> dict:
        with self.lock:
            folder = self.folder(run_id)
            if run_id != self.current_id or self.process is None or self.process.poll() is not None:
                return {"status": "already_stopped"}
            try:
                os.killpg(self.process.pid, signal.SIGINT)
            except ProcessLookupError:
                return {"status": "already_stopped"}
            conversation_event(folder, "stopping", "Stopping the experiment and retaining earlier measurements.", author="controller")
            return {"status": "stopping"}

    def close(self):
        if self.current_id and self.process is not None and self.process.poll() is None:
            self.stop(self.current_id)
            try:
                self.process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(self.process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                self.process.wait(timeout=3)
