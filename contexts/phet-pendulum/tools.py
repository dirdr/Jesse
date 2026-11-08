"""Recover the hidden Planet X gravity from displayed pendulum periods."""
import math

FIT_TRIALS = ("fit-1", "fit-2", "fit-3", "fit-4")
TRIALS = (*FIT_TRIALS, "mass", "amplitude")
SMALL_ANGLE_DEG = 15
MIN_SPAN_M = 0.3
MIN_R2 = 0.999


def _finite(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def analyze_reading(reading: dict) -> dict:
    trial_id = reading["trial_id"]
    if trial_id not in TRIALS:
        raise ValueError(f"Use one of {', '.join(TRIALS)}")
    for key in ("length_m", "mass_kg", "angle_deg", "period_s"):
        if reading[key] is not None and not _finite(reading[key]):
            raise ValueError(f"{key} must be a finite number or null when unreadable")
    for key in ("planet_x", "friction_none"):
        if not isinstance(reading[key], bool):
            raise ValueError(f"{key} must be true or false")
    if not reading["raw_reading"].strip() or not reading["evidence"]:
        raise ValueError("Preserve raw displayed text and evidence references")
    length, mass, angle, period = (reading[key] for key in ("length_m", "mass_kg", "angle_deg", "period_s"))
    problems = []
    if None in (length, mass, angle, period):
        problems.append("A required displayed value is unreadable")
    elif not (0.1 <= length <= 1.0 and 0.1 <= mass <= 1.5 and period > 0):
        problems.append("Length, mass or period is outside the simulator's range")
    if not reading["planet_x"] or not reading["friction_none"]:
        problems.append("Planet X and zero friction must both be verified")
    if trial_id != "amplitude" and angle is not None and abs(angle) > SMALL_ANGLE_DEG:
        problems.append(f"Swing larger than {SMALL_ANGLE_DEG}°; small-angle formula does not apply")
    g_single = 4 * math.pi ** 2 * length / period ** 2 if not problems else None
    return {"trial_id": trial_id, "length_m": length, "mass_kg": mass, "angle_deg": angle, "period_s": period,
            "g_single": g_single, "status": "incomplete" if problems else "measured",
            "reason": "; ".join(problems) if problems else "Displayed GUI reading."}


def _complete_elliptic_k(k: float) -> float:
    a, b = 1.0, math.sqrt(1 - k * k)
    for _ in range(30):
        a, b = (a + b) / 2, math.sqrt(a * b)
    return math.pi / (2 * a)


def fit_gravity(analyses: list[dict]) -> dict:
    by_id = {item["trial_id"]: item for item in analyses if item.get("status") == "measured"}
    fit = [by_id[trial] for trial in FIT_TRIALS if trial in by_id]
    result = {"fit_trials": len(fit), "g": None, "r2": None, "span_m": None, "mass_effect": None, "amplitude": None}
    if len(fit) < 2:
        return result
    lengths = [item["length_m"] for item in fit]
    squares = [item["period_s"] ** 2 for item in fit]
    slope = sum(l * t for l, t in zip(lengths, squares)) / sum(l * l for l in lengths)
    mean_t = sum(squares) / len(squares)
    total = sum((t - mean_t) ** 2 for t in squares)
    residual = sum((t - slope * l) ** 2 for l, t in zip(lengths, squares))
    g = 4 * math.pi ** 2 / slope
    result.update(g=g, r2=1 - residual / total if total else None, span_m=max(lengths) - min(lengths))
    if "mass" in by_id:
        control = by_id["mass"]
        expected = 2 * math.pi * math.sqrt(control["length_m"] / g)
        result["mass_effect"] = (control["period_s"] - expected) / expected
    if "amplitude" in by_id:
        control = by_id["amplitude"]
        small = 2 * math.pi * math.sqrt(control["length_m"] / g)
        theta = math.radians(abs(control["angle_deg"]))
        result["amplitude"] = {"angle_deg": control["angle_deg"], "measured_ratio": control["period_s"] / small,
                               "theory_ratio": 2 / math.pi * _complete_elliptic_k(math.sin(theta / 2)),
                               "naive_g": 4 * math.pi ** 2 * control["length_m"] / control["period_s"] ** 2}
    return result


def outcome(lab) -> tuple[str, str]:
    fit = fit_gravity(lab.analyses())
    missing = []
    if fit["fit_trials"] < 3:
        missing.append(f"{fit['fit_trials']} of at least 3 fit trials measured")
    if fit["span_m"] is not None and fit["span_m"] < MIN_SPAN_M:
        missing.append(f"lengths span {fit['span_m']:.2f} m, below {MIN_SPAN_M} m")
    if fit["r2"] is not None and fit["r2"] < MIN_R2:
        missing.append(f"fit R² {fit['r2']:.5f} is below {MIN_R2}")
    if missing or fit["g"] is None:
        return "inconclusive", "Not enough checked evidence: " + "; ".join(missing or ["no valid fit"]) + "."
    reason = f"g on Planet X = {fit['g']:.2f} m/s² from {fit['fit_trials']} trials (R² = {fit['r2']:.5f})."
    if fit["mass_effect"] is not None:
        reason += f" Mass control changed the period by {fit['mass_effect'] * 100:+.2f}%."
    return "supported_conclusion", reason


def tools(lab):
    def record_pendulum_trial(trial_id: str, length_m: float | None, mass_kg: float | None, angle_deg: float | None,
                              period_s: float | None, planet_x: bool, friction_none: bool,
                              raw_reading: str, evidence: list[str]) -> dict:
        """Save one displayed pendulum reading and return the updated gravity fit.

        Trial IDs: fit-1..fit-4 (small swings at different lengths), mass (fit-4 length, ~0.2 kg),
        amplitude (fit-4 length, ~60° swing). Values are the simulator's displayed readouts;
        angle_deg is your protractor estimate. Pass null for unreadable values and false for
        unverified conditions. Evidence must reference screenshots showing length, mass and period.
        """
        reading = dict(trial_id=trial_id, length_m=length_m, mass_kg=mass_kg, angle_deg=angle_deg,
                       period_s=period_s, planet_x=planet_x, friction_none=friction_none,
                       raw_reading=raw_reading, evidence=evidence)
        analysis = analyze_reading(reading)
        result = f"g ≈ {analysis['g_single']:.2f} m/s²" if analysis["g_single"] else "Unreadable"
        saved = lab.record(trial_id, reading, analysis=analysis,
                           fields={"Length": f"{length_m:.2f} m" if length_m is not None else "?",
                                   "Mass": f"{mass_kg:.2f} kg" if mass_kg is not None else "?",
                                   "Period": f"{period_s:.4f} s" if period_s is not None else "?"},
                           result=result, summary=f"Saved {trial_id}: T = {period_s} s at L = {length_m} m.")
        return {**saved, "fit": fit_gravity(lab.analyses())}

    return [record_pendulum_trial]


def report(lab) -> str:
    fit = fit_gravity(lab.analyses())
    rows = [item for item in lab.analyses() if item.get("trial_id") in TRIALS]
    lines = ["## Gravity fit", "", "Small-angle model: $T^2 = \\frac{4\\pi^2}{g} L$, so $g = 4\\pi^2 / \\text{slope}$.", "",
             "| Trial | Length (m) | Mass (kg) | Angle (°) | Period (s) | Single-trial g (m/s²) | Status |",
             "| --- | --- | --- | --- | --- | --- | --- |"]
    for item in rows:
        g = f"{item['g_single']:.3f}" if item.get("g_single") else "—"
        lines.append(f"| {item['trial_id']} | {item['length_m']} | {item['mass_kg']} | {item['angle_deg']} | "
                     f"{item['period_s']} | {g} | {item['status']} |")
    if fit["g"] is not None:
        lines += ["", f"Fitted gravity: **{fit['g']:.3f} m/s²** from {fit['fit_trials']} trials, "
                      f"R² = {fit['r2']:.5f}, length span {fit['span_m']:.2f} m."]
    if fit["mass_effect"] is not None:
        lines.append(f"Mass control: period differs from the fit prediction by {fit['mass_effect'] * 100:+.2f}%.")
    amplitude = fit["amplitude"]
    if amplitude:
        lines.append(f"Amplitude control at {amplitude['angle_deg']}°: period ratio {amplitude['measured_ratio']:.4f} "
                     f"(exact theory {amplitude['theory_ratio']:.4f}); the small-angle formula alone would give "
                     f"g = {amplitude['naive_g']:.2f} m/s².")
    decided, reason = outcome(lab)
    lines += ["", f"Python outcome rule: **{decided}**. {reason}"]
    return "\n".join(lines)
