"""Catalogue descriptions and validated routing decisions."""
from dataclasses import asdict, dataclass
from typing import Literal

Surface = Literal["web", "desktop"]


class PlannerUnavailable(RuntimeError):
    """A provider failure that can be shown without leaking request details."""


@dataclass(frozen=True)
class ExperimentDefinition:
    experiment_id: str
    application: str
    model: str
    supported_questions: tuple[str, ...]
    unsupported_questions: tuple[str, ...]
    surfaces: tuple[Surface, ...]
    parameters: tuple[str, ...]
    measurements: tuple[str, ...]
    assumptions: tuple[str, ...]
    protocol_resource: str
    analyzer: str
    completion_criteria: tuple[str, ...]
    interaction_status: str
    maximum_trials: int = 2

    def to_dict(self) -> dict:
        return asdict(self)


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


CATALOGUE = (
    ExperimentDefinition(
        experiment_id="netlogo-enzyme-feasibility",
        application="NetLogo", model="Enzyme Kinetics",
        supported_questions=(
            "Compare reaction velocity at two substrate quantities with fixed reaction constants.",
            "Begin investigating whether more substrate makes an enzyme reaction faster; the two-trial result is preliminary.",
        ),
        unsupported_questions=(
            "Prove saturation, estimate Km/Vmax, or make statistically verified claims from two trials.",
            "Measure a real sample, coolant heat capacity, traffic, fire, or a different simulator/model.",
            "Change reaction constants between trials, perform inhibitor assays, or modify the simulator code.",
        ),
        surfaces=("web", "desktop"),
        parameters=("VOLUME varies", "Kc fixed", "Kd fixed", "Kr fixed and nonzero", "PAUSE? enabled"),
        measurements=("Displayed reaction velocity after RECORD V", "Observed settings", "0–30 tick interval", "Actual rate units or unknown"),
        assumptions=("Simulator findings only", "Irreversible inhibitor mechanism", "Unknown units block numerical comparison", "Replay verification is pending"),
        protocol_resource="jesse.experiments.netlogo/protocol.md",
        analyzer="netlogo-enzyme-rate-comparison-v1",
        completion_criteria=("Two observed trials with distinct VOLUME", "Matching fixed conditions", "Readings linked to evidence", "Python comparison or explicit comparability blocker"),
        interaction_status="Web trials and analysis tool recorded; replay acceptance pending. Desktop implementation awaits interaction proof.",
    ),
)


def validate_selection(
    question: str, proposal: Proposal, catalogue: tuple[ExperimentDefinition, ...],
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
    definition = next((item for item in catalogue if item.experiment_id == proposal.experiment_id), None)
    if definition is None:
        return blocked("The proposed experiment is not in the approved catalogue.")
    if proposal.surface not in definition.surfaces or proposal.surface not in available_surfaces:
        return blocked("The proposed surface is unsupported or unavailable on this machine.")
    if requested_surface != "auto" and proposal.surface != requested_surface:
        return blocked("The proposed surface conflicts with the researcher's explicit choice.")
    return Selection("ready", question, proposal.reason, definition.experiment_id, proposal.surface, definition.maximum_trials)
