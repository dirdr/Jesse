"""What a research context declares; independent of files and providers."""
from dataclasses import dataclass, field
from pathlib import Path

BUILTIN_TOOLS = frozenset({"publish_update", "acknowledge_researcher_message", "record_observation"})
SURFACE_KINDS = ("web", "desktop")


class ContextError(ValueError):
    """A context folder is missing a required file or declares an invalid value."""


@dataclass(frozen=True)
class Surface:
    kind: str
    start_url: str | None = None
    width: int = 1280
    height: int = 900
    app_path: str | None = None

    def environment(self, context_id: str) -> dict:
        if self.kind == "web":
            return {"id": f"{context_id}-browser", "kind": "web", "start_url": self.start_url,
                    "mode": {"type": "visual", "width": self.width, "height": self.height}}
        return {"id": f"{context_id}-desktop", "kind": "desktop", "host": "user_device", "shell": False}


@dataclass(frozen=True)
class ResearchContext:
    id: str
    title: str
    application: str
    activity: str
    questions: tuple[str, ...]
    surfaces: dict[str, Surface]
    protocol: str
    folder: Path
    unsupported: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    completion: tuple[str, ...] = ()
    sources: tuple[str, ...] = ()
    status: str = "unverified"
    budget_seconds: int = 600
    max_steps: int = 110
    max_trials: int = 2
    tools: tuple[str, ...] = ("publish_update", "acknowledge_researcher_message", "record_observation")
    extension: Path | None = field(default=None, compare=False)

    @property
    def experiment_id(self) -> str:
        return self.id

    @property
    def maximum_trials(self) -> int:
        return self.max_trials

    @property
    def surface_names(self) -> tuple[str, ...]:
        return tuple(self.surfaces)

    def to_dict(self) -> dict:
        """Planner- and panel-facing description; never includes local paths or protocol text."""
        return {
            "experiment_id": self.id, "title": self.title, "application": self.application,
            "activity": self.activity, "supported_questions": list(self.questions),
            "unsupported_questions": list(self.unsupported), "surfaces": list(self.surfaces),
            "assumptions": list(self.assumptions), "completion_criteria": list(self.completion),
            "interaction_status": self.status, "maximum_trials": self.max_trials,
            "source_urls": list(self.sources),
        }
