"""Single-writer immutable observation persistence."""
import json
from pathlib import Path

from .domain import Observation


class FileObservations:
    def __init__(self, folder: Path, run_id: str):
        self.folder = folder
        self.run_id = run_id

    def record(self, observation: Observation) -> dict:
        self.folder.mkdir(parents=True, exist_ok=True)
        path = self.folder / f"{observation.observation_id}.json"
        payload = {"run_id": self.run_id, **observation.to_dict()}
        if path.exists():
            if json.loads(path.read_text(encoding="utf-8")) != payload:
                raise ValueError("Observation ID already exists with different data; use a new ID")
            return {"observation_id": observation.observation_id, "recorded": True, "duplicate": True}
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, indent=2, allow_nan=False), encoding="utf-8")
        temporary.replace(path)
        return {"observation_id": observation.observation_id, "recorded": True, "duplicate": False}
