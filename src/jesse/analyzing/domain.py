"""Conservative comparison of NetLogo Enzyme Kinetics rate readings."""
from collections import defaultdict
import hashlib
import json
import math
from statistics import mean, stdev

from jesse.recording.domain import Observation


def compare_rates(observations: list[Observation]) -> dict:
    ordered = sorted(observations, key=lambda item: item.observation_id)
    method = "netlogo-enzyme-rate-comparison-v1"
    fingerprint = json.dumps({"method": method, "observations": [item.to_dict() for item in ordered]}, sort_keys=True, allow_nan=False)
    analysis_id = "rates-" + hashlib.sha256(fingerprint.encode()).hexdigest()[:16]
    included = [item for item in ordered if item.status == "observed"]
    excluded = [{"observation_id": item.observation_id, "reason": item.reason or item.status} for item in ordered if item.status != "observed"]
    result = {
        "analysis_id": analysis_id,
        "method": method,
        "input_observation_ids": [item.observation_id for item in ordered],
        "included_observation_ids": [item.observation_id for item in included],
        "excluded_observations": excluded,
        "status": "insufficient_data", "issues": [], "derived_values": [],
        "comparison": None, "suggested_follow_up": None,
        "limitations": [
            "Readings and evidence still require replay verification.",
            "This comparison does not establish saturation, statistical significance or a physical laboratory result.",
        ],
    }
    if not included:
        result["issues"] = ["No readable numerical rate observations were recorded."]
        return result

    baseline = included[0]
    issues = []
    seen_trials = set()
    for item in included:
        prefix = item.observation_id + ": "
        if item.quantity.casefold().strip() not in {"reaction rate", "reaction velocity (v)", "reaction velocity", "velocity", "v"}:
            issues.append(prefix + "This analyzer accepts Enzyme Kinetics reaction-rate readings only.")
        if item.trial_id in seen_trials:
            issues.append(prefix + "Multiple readings from one trial cannot count as independent repeats.")
        seen_trials.add(item.trial_id)
        for control in ("VOLUME", "Kc", "Kd", "Kr"):
            value = item.settings.get(control)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                issues.append(prefix + f"{control} needs an observed nonnegative numerical setting.")
        if item.settings.get("Kr") == 0:
            issues.append(prefix + "Kr must be nonzero for this assay.")
        if item.settings.get("PAUSE?") is not True:
            issues.append(prefix + "The bounded assay requires PAUSE? enabled.")
        if item.interval != {"start": 0, "end": 30, "unit": "ticks"}:
            issues.append(prefix + "The RECORD V assay requires the same observed 0–30 tick interval.")
        if not item.unit:
            issues.append(prefix + "Rate units are unknown; confirm the displayed simulator units.")
        if (item.unit, item.quantity) != (baseline.unit, baseline.quantity):
            issues.append(prefix + "Quantity labels or units differ between readings.")
        if item.value < 0:
            issues.append(prefix + "Reaction rate cannot be negative in this protocol.")
        fixed = {key: value for key, value in item.settings.items() if key != "VOLUME"}
        baseline_fixed = {key: value for key, value in baseline.settings.items() if key != "VOLUME"}
        if fixed != baseline_fixed:
            issues.append(prefix + "Settings other than VOLUME differ between trials.")
    if issues:
        result.update(status="not_comparable", issues=issues, suggested_follow_up={
            "kind": "check_conditions", "reason": "Resolve the listed condition or measurement mismatches before comparing rates.",
        })
        return result

    groups = defaultdict(list)
    for item in included:
        groups[item.settings["VOLUME"]].append(item)
    for volume, readings in sorted(groups.items()):
        values = [item.value for item in readings]
        result["derived_values"].append({
            "volume": volume, "mean_rate": mean(values), "unit": baseline.unit,
            "repeat_count": len(values), "minimum_rate": min(values), "maximum_rate": max(values),
            "sample_standard_deviation": stdev(values) if len(values) > 1 else None,
            "input_observation_ids": [item.observation_id for item in readings],
        })
    if len(groups) < 2:
        result["issues"] = ["At least two distinct substrate settings are needed for a comparison."]
        result["suggested_follow_up"] = {"kind": "change_substrate", "reason": "Record a distinct VOLUME while keeping other conditions fixed."}
        return result

    low, high = result["derived_values"][0], result["derived_values"][-1]
    difference = high["mean_rate"] - low["mean_rate"]
    result["status"] = "compared"
    result["comparison"] = {
        "low_volume": low["volume"], "high_volume": high["volume"],
        "rate_difference": difference, "unit": baseline.unit,
        "rate_ratio": high["mean_rate"] / low["mean_rate"] if low["mean_rate"] != 0 else None,
        "direction": "increased" if difference > 0 else "decreased" if difference < 0 else "unchanged",
        "input_observation_ids": low["input_observation_ids"] + high["input_observation_ids"],
    }
    unrepeated = [group["volume"] for group in result["derived_values"] if group["repeat_count"] < 2]
    if unrepeated:
        result["limitations"].append("One or more settings have no independent repeat; variability is unknown.")
        result["suggested_follow_up"] = {
            "kind": "repeat", "volumes": unrepeated,
            "reason": "Repeat these settings independently before interpreting the difference.",
        }
    else:
        result["suggested_follow_up"] = {
            "kind": "review_evidence", "reason": "Verify the readings and choose further substrate levels under an agreed protocol and budget.",
        }
    return result
