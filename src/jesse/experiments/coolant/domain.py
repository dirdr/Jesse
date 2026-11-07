"""Assignment constants and calorimetry; independent of computer-use providers."""
from importlib.resources import files
import json
import math

ACTIVITY_URL = "https://chemcollective.org/vlab/92"
SOURCE_URL = "https://chemcollective.org/activities/info/92"
ASSIGNMENT_URL = "https://chemcollective.org/assets/modules/activities/vlab/probs/freeze.doc"
DEFAULT_QUESTION = "Compare this new coolant with the reference, run the experiment, verify your measurements, and explain which absorbs more heat per gram for the same temperature rise."
REFERENCE_SPECIFIC_HEAT = 2.200  # J/(g·°C), supplied ethylene glycol reference
COOLANT_DENSITY = 2.78  # g/mL, supplied Compound Y solution density
WATER_SPECIFIC_HEAT = 4.184  # J/(g·°C), supplied water value


def build_prompt(question: str = DEFAULT_QUESTION) -> str:
    return "\n\n".join((
        "Researcher question (context; execute the bounded protocol): " + json.dumps(question),
        files("jesse").joinpath("instructions.md").read_text(encoding="utf-8"),
        files(__package__).joinpath("protocol.md").read_text(encoding="utf-8"),
    ))


def analyze_reading(reading: dict) -> dict:
    """Check conditions before calculating heat lost by water = heat gained by Y.

    Values are agent-reported GUI observations. These checks do not verify replay.
    Preserve the reading separately, including when conditions prevent analysis.
    """
    numeric = ("coolant_volume_ml", "water_volume_ml", "coolant_initial_c", "water_initial_c", "final_c")
    for key in numeric:
        value = reading[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"{key} must be a finite number")
    if reading["coolant_volume_ml"] <= 0 or reading["water_volume_ml"] <= 0:
        raise ValueError("Transferred volumes must be positive")
    for key in ("samples_insulated", "mixing_vessel_insulated", "temperatures_verified"):
        if not isinstance(reading[key], bool):
            raise ValueError(f"{key} must be true or false")
    if not reading["raw_reading"].strip() or not reading["evidence"] or not all(isinstance(item, str) and item.strip() for item in reading["evidence"]):
        raise ValueError("Preserve raw displayed readings and nonempty evidence references")
    result = {
        "trial_id": reading["trial_id"], "method": "insulated-mixing-calorimetry-v1",
        "reference_specific_heat_j_g_c": REFERENCE_SPECIFIC_HEAT,
        "specific_heat_j_g_c": None, "comparison": None,
        "sources": [SOURCE_URL, ASSIGNMENT_URL],
        "assumptions": [
            "Water mass approximated from volume using density 1.00 g/mL; not a balance measurement",
            "Compound Y density 2.78 g/mL; water specific heat 4.184 J/(g·°C), supplied by assignment",
            "Negligible glassware heat capacity and mixing enthalpy; isolated heat exchange",
            "Agent-reported GUI readings; replay review and fresh verification remain required",
        ],
    }
    problems = []
    if not reading["samples_insulated"] or not reading["mixing_vessel_insulated"]:
        problems.append("Separate samples and mixing vessel must be insulated before measuring")
    if not reading["temperatures_verified"]:
        problems.append("Confirm stable actual initial temperatures immediately before mixing")
    if not reading["coolant_initial_c"] < reading["final_c"] < reading["water_initial_c"]:
        problems.append("Final temperature must lie between initially cooler coolant and hotter water")
    if problems:
        return {**result, "status": "needs_repeat", "reason": "; ".join(problems),
                "suggested_follow_up": "Use fresh aliquots, insulate filled containers, then set and verify initial temperatures before mixing."}
    water_mass = reading["water_volume_ml"]  # explicitly declared approximation
    coolant_mass = reading["coolant_volume_ml"] * COOLANT_DENSITY
    heat = water_mass * WATER_SPECIFIC_HEAT * (reading["water_initial_c"] - reading["final_c"])
    specific_heat = heat / (coolant_mass * (reading["final_c"] - reading["coolant_initial_c"]))
    if not math.isfinite(specific_heat) or specific_heat <= 0:
        raise ValueError("Derived specific heat must be finite and positive")
    return {**result, "status": "estimated", "specific_heat_j_g_c": specific_heat,
            "coolant_mass_g": coolant_mass, "approximate_water_mass_g": water_mass,
            "comparison": "higher" if specific_heat > REFERENCE_SPECIFIC_HEAT else "lower" if specific_heat < REFERENCE_SPECIFIC_HEAT else "equal",
            "reason": "Preliminary simulator estimate; agreement of two estimates is not statistical validation.",
            "suggested_follow_up": "Repeat once using fresh aliquots and compare estimates; retain both readings."}
