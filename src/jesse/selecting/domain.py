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
    source_urls: tuple[str, ...] = ()
    launch_url: str | None = None

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
        measurements=("Displayed V after RECORD V: a free-substrate depletion proxy", "Observed settings", "0–30 displayed tick interval", "Substrate molecules/model tick for documented version 7.0.4; otherwise confirm units"),
        assumptions=("Simulator findings only", "V includes substrate binding, not just product formation", "Irreversible inhibitor mechanism", "Unknown units block numerical comparison", "Replay verification is pending"),
        protocol_resource="jesse.experiments.netlogo/protocol.md",
        analyzer="netlogo-enzyme-rate-comparison-v2",
        completion_criteria=("Two observed trials with distinct VOLUME", "Matching fixed conditions", "Readings linked to evidence", "Python comparison or explicit comparability blocker"),
        interaction_status="Web trials and analysis tool recorded; replay acceptance pending. Desktop implementation awaits interaction proof.",
    ),
    ExperimentDefinition(
        experiment_id="chemcollective-coolant-feasibility",
        application="ChemCollective", model="Measuring the heat capacity of an engine coolant (activity 92)",
        supported_questions=("Estimate the specific heat capacity of Compound Y solution using insulated mixing calorimetry.",
            "Compare a new coolant's heat absorbed per gram per degree with the supplied ethylene glycol reference and attempt one fresh verification trial."),
        unsupported_questions=("Determine overall engine cooling performance or validate a physical coolant.",
            "Physically test the reference in a second GUI experiment; only its supplied specific heat is available in this protocol.",
            "Test arbitrary unknown chemicals, molecular polarity, or activities other than coolant activity 92."),
        surfaces=("web",),
        parameters=("Measured coolant and water volumes", "Stable initial solution temperatures", "Insulated sample containers and mixing vessel"),
        measurements=("Actual volumes in mL", "Initial and final temperatures in °C", "Raw readings and evidence references"),
        assumptions=("Simulator findings only", "Supplied reference 2.200 J/(g·°C)", "Compound Y density 2.78 g/mL",
            "Water specific heat 4.184 J/(g·°C)", "Approximate water density 1.00 g/mL", "Negligible container heat capacity and mixing enthalpy", "Repeat and replay review pending"),
        protocol_resource="jesse.experiments.coolant/protocol.md", analyzer="insulated-mixing-calorimetry-v1",
        completion_criteria=("GUI transfers and actual temperature readings", "Python checks insulation and stable initial readings",
            "Fresh independent verification attempt", "Evidence-linked report, inconclusive if verification is incomplete"),
        interaction_status="Experimental: one assisted GUI trial and calculation recorded; temperature drift and incomplete repeat prevented acceptance. Revised compact protocol awaits live acceptance.",
        source_urls=("https://chemcollective.org/activities/info/92", "https://chemcollective.org/assets/modules/activities/vlab/probs/freeze.doc"),
        launch_url="https://chemcollective.org/vlab/92",
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
