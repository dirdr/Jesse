"""Calorimetry tool for the ChemCollective coolant activity.

Jesse loads this file when the context runs. `tools(lab)` returns extra H tools;
`report(lab)` adds a section to report.md.
"""
import math

REFERENCE_SPECIFIC_HEAT = 2.200
COOLANT_DENSITY = 2.78
WATER_SPECIFIC_HEAT = 4.184
SOURCES = ["https://chemcollective.org/activities/info/92",
           "https://chemcollective.org/assets/modules/activities/vlab/probs/freeze.doc"]


def analyze_reading(reading: dict) -> dict:
    """Check conditions, then calculate heat lost by water = heat gained by Compound Y."""
    for key in ("coolant_volume_ml", "water_volume_ml", "coolant_initial_c", "water_initial_c", "final_c"):
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
        "specific_heat_j_g_c": None, "comparison": None, "sources": SOURCES,
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
    water_mass = reading["water_volume_ml"]
    coolant_mass = reading["coolant_volume_ml"] * COOLANT_DENSITY
    heat = water_mass * WATER_SPECIFIC_HEAT * (reading["water_initial_c"] - reading["final_c"])
    specific_heat = heat / (coolant_mass * (reading["final_c"] - reading["coolant_initial_c"]))
    if not math.isfinite(specific_heat) or specific_heat <= 0:
        raise ValueError("Derived specific heat must be finite and positive")
    comparison = "higher" if specific_heat > REFERENCE_SPECIFIC_HEAT else "lower" if specific_heat < REFERENCE_SPECIFIC_HEAT else "equal"
    return {**result, "status": "estimated", "specific_heat_j_g_c": specific_heat,
            "coolant_mass_g": coolant_mass, "approximate_water_mass_g": water_mass, "comparison": comparison,
            "reason": "Preliminary simulator estimate; agreement of two estimates is not statistical validation.",
            "suggested_follow_up": "Repeat once using fresh aliquots and compare estimates; retain both readings."}


def tools(lab):
    def record_calorimetry(trial_id: str, coolant_volume_ml: float, water_volume_ml: float,
                           coolant_initial_c: float, water_initial_c: float, final_c: float,
                           samples_insulated: bool, mixing_vessel_insulated: bool,
                           temperatures_verified: bool, raw_reading: str, evidence: list[str]) -> dict:
        """Save actual observed volumes/temperatures and return checked Python analysis.

        samples_insulated means BOTH separate samples were insulated before initial
        readings. temperatures_verified means actual initial temperatures were stable
        and checked immediately before mixing. Report false when uncertain. Preserve
        evidence references and raw readings. The controller approximates water density
        as 1.00 g/mL. At most two independent physical mixing trials are allowed.
        """
        reading = dict(trial_id=trial_id, coolant_volume_ml=coolant_volume_ml, water_volume_ml=water_volume_ml,
                       coolant_initial_c=coolant_initial_c, water_initial_c=water_initial_c, final_c=final_c,
                       samples_insulated=samples_insulated, mixing_vessel_insulated=mixing_vessel_insulated,
                       temperatures_verified=temperatures_verified, raw_reading=raw_reading, evidence=evidence)
        analysis = analyze_reading(reading)
        value = analysis["specific_heat_j_g_c"]
        return lab.record(
            trial_id, reading, analysis=analysis,
            fields={"Coolant": f"{coolant_volume_ml:g} mL at {coolant_initial_c:g} °C",
                    "Water": f"{water_volume_ml:g} mL at {water_initial_c:g} °C",
                    "Final": f"{final_c:g} °C"},
            result=f"{value:.3f} J/(g·°C)" if value is not None else None,
            summary=f"Saved {trial_id}: final temperature {final_c:g} °C.")

    return [record_calorimetry]


def report(lab) -> str:
    estimates = [item for item in lab.analyses() if item.get("status") == "estimated"]
    lines = ["## Calculation", "",
             "c_Y = m_water × 4.184 × (T_water − T_final) / [m_Y × (T_final − T_Y)]", "",
             f"Reference (supplied, not a GUI trial): **{REFERENCE_SPECIFIC_HEAT:.3f} J/(g·°C)**."]
    for item in estimates:
        lines.append(f"- {item['trial_id']}: {item['specific_heat_j_g_c']:.4g} J/(g·°C), {item['comparison']} than the reference")
    if len(estimates) == 2:
        difference = abs(estimates[1]["specific_heat_j_g_c"] - estimates[0]["specific_heat_j_g_c"])
        lines.append(f"- Difference between repeat estimates: {difference:.4g} J/(g·°C). Agreement alone is not statistical confidence.")
    elif estimates:
        lines.append("- A fresh repeat is still required before comparing with confidence.")
    return "\n".join(lines)
