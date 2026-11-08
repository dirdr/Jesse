"""The agent's tools: report progress, answer the researcher, record readings and analyze them."""
from collections.abc import Callable
import math

from .lab import Lab

OBSERVATION_STATUSES = {"observed", "unreadable", "interrupted"}


def _recorded_values(lab: Lab, name: str) -> dict[str, float]:
    values = {}
    for item in lab.observations():
        reading = (item.get("reading") or {})
        value = (reading.get("readings") or {}).get(name)
        if reading.get("status") == "observed" and isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
            values[item["trial_id"]] = float(value)
    return values


def fit(xs: list[float], ys: list[float], through_origin: bool) -> dict:
    n = len(xs)
    if through_origin:
        slope, intercept = sum(x * y for x, y in zip(xs, ys)) / sum(x * x for x in xs), 0.0
    else:
        mean_x, mean_y = sum(xs) / n, sum(ys) / n
        spread = sum((x - mean_x) ** 2 for x in xs)
        if spread == 0:
            raise ValueError("The x values are all equal; vary the setting before fitting")
        slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / spread
        intercept = mean_y - slope * mean_x
    mean_y = sum(ys) / n
    total = sum((y - mean_y) ** 2 for y in ys)
    residual = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(xs, ys))
    return {"slope": slope, "intercept": intercept, "r2": 1 - residual / total if total else None}


def agent_tools(lab: Lab) -> list[Callable]:
    def publish_update(update_id: str, kind: str, text: str) -> dict:
        """Tell the researcher a concise plan, finding, follow_up or blocker.

        Use kind=plan for your proposal before acting. One or two accessible sentences at
        meaningful milestones; no narration of routine clicks. Keep a stable update_id on retries.
        """
        return lab.update(update_id, kind, text)

    def acknowledge_researcher_message(event_id: str, status: str, text: str) -> dict:
        """Acknowledge a researcher message as acknowledged, applied or rejected.

        Read the message ID supplied with its text. Say applied only after checking the change
        actually took effect; explain a rejected change. Preserve earlier measurements.
        """
        return lab.acknowledge(event_id, status, text)

    def record_observation(trial_id: str, readings: dict[str, float | None], units: dict[str, str],
                           raw_reading: str, evidence: list[str], status: str = "observed",
                           note: str | None = None) -> dict:
        """Save readings exactly as displayed on screen, immediately, before any interpretation.

        readings maps each quantity (use the same snake_case names across trials, e.g. length_m,
        period_s) to its displayed value, or null if unreadable; units maps the same names to units.
        Include the settings you chose as readings too. Preserve the raw displayed text and evidence
        references. status is observed, unreadable or interrupted. Reuse a trial_id only for an
        identical retry. Require recorded=true before continuing.
        """
        if status not in OBSERVATION_STATUSES:
            raise ValueError("status must be observed, unreadable or interrupted")
        if not raw_reading.strip() or not evidence or not all(isinstance(item, str) and item.strip() for item in evidence):
            raise ValueError("Preserve the raw reading and nonempty evidence references")
        fields = {name: f"{value} {units.get(name, '')}".strip() for name, value in readings.items()}
        reading = {"readings": readings, "units": units, "raw_reading": raw_reading,
                   "evidence": evidence, "status": status, "note": note}
        return lab.record(trial_id, reading, analysis={"status": status}, fields=fields,
                          summary=f"Saved {trial_id}: " + ", ".join(f"{key} {value}" for key, value in fields.items()))

    def analyze_readings(analysis_id: str, x: str, y: str, y_power: float = 1.0, through_origin: bool = False) -> dict:
        """Fit a straight line to recorded readings: y**y_power against x, across observed trials.

        x and y are reading names used in record_observation. Only recorded values are used, so the
        result can be traced to evidence. Example: pendulum period vs length uses x=length_m,
        y=period_s, y_power=2, through_origin=true; then g = 4π² / slope. Returns slope, intercept,
        R², the trials used and the mean and spread of y. Needs at least two trials with both values.
        """
        xs, ys = _recorded_values(lab, x), _recorded_values(lab, y)
        trials = sorted(set(xs) & set(ys))
        if len(trials) < 2:
            raise ValueError(f"Need at least two observed trials with both {x} and {y}")
        points = [(xs[trial], ys[trial] ** y_power) for trial in trials]
        result = fit([p[0] for p in points], [p[1] for p in points], through_origin)
        raw = [ys[trial] for trial in trials]
        mean = sum(raw) / len(raw)
        spread = math.sqrt(sum((value - mean) ** 2 for value in raw) / (len(raw) - 1))
        target = y if y_power == 1 else f"{y}^{y_power:g}"
        r2 = f"{result['r2']:.5f}" if result["r2"] is not None else "n/a"
        summary = f"{target} vs {x}: slope {result['slope']:.6g}, intercept {result['intercept']:.6g}, R² {r2} ({len(trials)} trials)"
        return lab.save_analysis(analysis_id, {"kind": "fit", "x": x, "y": y, "y_power": y_power,
                                               "through_origin": through_origin, "trials": trials, **result,
                                               "y_mean": mean, "y_stdev": spread, "summary": summary})

    return [publish_update, acknowledge_researcher_message, record_observation, analyze_readings]
