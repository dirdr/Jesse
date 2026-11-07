"""Boundaries owned by the experiment use case."""
from typing import Protocol, Any

class DesktopAgent(Protocol):
    def run(self, instructions: str) -> tuple[dict[str, Any], str]: ...

class ExperimentRecords(Protocol):
    def save(self, session: dict, report: str) -> None: ...
