"""Shared session serialization and bounded worker cleanup."""
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
from uuid import uuid4


def json_value(value):
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


def save_json(folder: Path, name: str, payload) -> None:
    path = folder / name
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, indent=2, allow_nan=False), encoding="utf-8")
    temporary.replace(path)


def conversation_event(folder: Path, kind: str, text: str, *, author="jesse", speak=False, **data) -> dict:
    """Append one public event; raw H reasoning is never projected into chat."""
    event = {"id": uuid4().hex, "kind": kind, "text": text, "author": author,
             "speak": speak, "at": datetime.now(timezone.utc).isoformat(), **data}
    folder.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(folder / "conversation.jsonl", os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        os.write(descriptor, (json.dumps(event, allow_nan=False) + "\n").encode())
    finally:
        os.close(descriptor)
    print(f"Jesse: {text}", flush=True)
    return event


def stop_worker(process) -> None:
    if process.is_alive():
        try:
            os.kill(process.pid, signal.SIGINT)
        except ProcessLookupError:
            pass
        process.join(3)
    if process.is_alive():
        process.terminate()
        process.join(2)
    if process.is_alive():
        process.kill()
        process.join(2)
