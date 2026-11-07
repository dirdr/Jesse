"""Ask a planner to route a question, then enforce catalogue boundaries."""
from typing import Protocol

from .domain import ResearchContext, Proposal, Selection, validate_selection


class ExperimentPlanner(Protocol):
    def propose(self, question: str, catalogue: tuple[ResearchContext, ...], available_surfaces: set[str], requested_surface: str) -> Proposal: ...


def select_experiment(
    question: str, catalogue: tuple[ResearchContext, ...], available_surfaces: set[str],
    planner: ExperimentPlanner, requested_surface: str = "auto",
) -> Selection:
    question = question.strip()
    if not question or len(question) > 4000:
        return Selection("blocked", question, "Supply a research question between 1 and 4000 characters.")
    if requested_surface not in {"auto", "web", "desktop"}:
        return Selection("blocked", question, "Unknown surface preference.")
    eligible = available_surfaces if requested_surface == "auto" else available_surfaces & {requested_surface}
    if not eligible:
        return Selection("blocked", question, "No eligible execution surface passed preflight. Inspect availability.json for setup requirements.")
    if not catalogue:
        return Selection("blocked", question, "No experimental protocols are registered.")
    proposal = planner.propose(question, catalogue, eligible, requested_surface)
    return validate_selection(question, proposal, catalogue, eligible, requested_surface)
