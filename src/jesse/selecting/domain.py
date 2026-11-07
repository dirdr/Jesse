"""Validated routing decisions over the loaded research contexts."""
from dataclasses import asdict, dataclass
from typing import Literal

from jesse.contexts import ResearchContext

Surface = Literal["web", "desktop"]


class PlannerUnavailable(RuntimeError):
    """A provider failure that can be shown without leaking request details."""


@dataclass(frozen=True)
class Proposal:
    decision: Literal["select", "blocked"]
    experiment_id: str | None
    surface: Surface | None
    reason: str


@dataclass(frozen=True)
class Selection:
    status: Literal["ready", "blocked"]
    question: str
    reason: str
    experiment_id: str | None = None
    surface: Surface | None = None
    maximum_trials: int | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def validate_selection(
    question: str, proposal: Proposal, catalogue: tuple[ResearchContext, ...],
    available_surfaces: set[str], requested_surface: str = "auto",
) -> Selection:
    def blocked(reason: str) -> Selection:
        return Selection("blocked", question, reason)

    if not proposal.reason.strip():
        return blocked("The planner did not explain its selection.")
    if proposal.decision == "blocked":
        return blocked(proposal.reason)
    if proposal.decision != "select":
        return blocked("The planner returned an unknown decision.")
    definition = next((item for item in catalogue if item.id == proposal.experiment_id), None)
    if definition is None:
        return blocked("The proposed experiment is not in the approved catalogue.")
    if proposal.surface not in definition.surfaces or proposal.surface not in available_surfaces:
        return blocked("The proposed surface is unsupported or unavailable on this machine.")
    if requested_surface != "auto" and proposal.surface != requested_surface:
        return blocked("The proposed surface conflicts with the researcher's explicit choice.")
    return Selection("ready", question, proposal.reason, definition.id, proposal.surface, definition.max_trials)
