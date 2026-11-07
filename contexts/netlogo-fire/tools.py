"""Record GUI readings and compare the two bounded Fire conditions."""
import math
from statistics import mean

TRIALS = {"low-1": 55, "high-1": 70, "low-2": 55, "high-2": 70}


def analyze_reading(reading: dict) -> dict:
    trial_id = reading["trial_id"]
    if trial_id not in TRIALS:
        raise ValueError("Use low-1, high-1, low-2 or high-2")
    for key in ("density_percent", "percent_burned", "ticks"):
        value = reading[key]
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)):
            raise ValueError(f"{key} must be a finite number or null when unreadable")
    for key in ("fresh_setup", "completed", "settings_verified"):
        if not isinstance(reading[key], bool):
            raise ValueError(f"{key} must be true or false")
    density, burned, ticks = (reading[key] for key in ("density_percent", "percent_burned", "ticks"))
    if density is not None and not 0 <= density <= 99:
        raise ValueError("Density must be between 0 and 99 percent")
    if burned is not None and not 0 <= burned <= 100:
        raise ValueError("Percent burned must be between 0 and 100")
    if ticks is not None and (ticks < 0 or ticks != int(ticks)):
        raise ValueError("Ticks must be a nonnegative integer model step count")
    if not reading["raw_reading"].strip() or not reading["evidence"] or not all(isinstance(item, str) and item.strip() for item in reading["evidence"]):
        raise ValueError("Preserve raw displayed text and nonempty evidence references")
    problems = []
    if density != TRIALS[trial_id]:
        problems.append(f"Expected {TRIALS[trial_id]}% density; retain the actual reading")
    if any(value is None for value in (density, burned, ticks)):
        problems.append("A required displayed value is unreadable")
    if not all(reading[key] for key in ("fresh_setup", "completed", "settings_verified")) or ticks == 0:
        problems.append("Verify a fresh Setup, unchanged settings and natural completion after Go")
    return {"trial_id": trial_id, "density_percent": density, "percent_burned": burned,
            "ticks": ticks, "status": "incomplete" if problems else "measured",
            "reason": "; ".join(problems) if problems else "GUI reading; replay review pending."}


def compare_trials(analyses: list[dict]) -> dict:
    valid = [item for item in analyses if item.get("status") == "measured"]
    groups = {str(density): [item["percent_burned"] for item in valid if item["density_percent"] == density]
              for density in (55, 70)}
    summaries = {density: {"count": len(values), "mean_percent_burned": mean(values),
                           "min_percent_burned": min(values), "max_percent_burned": max(values)}
                 for density, values in groups.items() if values}
    difference = summaries["70"]["mean_percent_burned"] - summaries["55"]["mean_percent_burned"] if len(summaries) == 2 else None
    complete = all(len(values) == 2 for values in groups.values())
    return {"status": "repeated_comparison" if complete else "preliminary", "conditions": summaries,
            "difference_percentage_points": difference,
            "suggested_follow_up": "Report both condition means and ranges; replay review remains required." if complete else
            "Complete the remaining scheduled fresh trials within the original four-trial and time limits.",
            "limitation": "Descriptive comparison of these runs only; no critical threshold or probability estimate."}


def tools(lab):
    def record_fire_trial(trial_id: str, density_percent: float | None, percent_burned: float | None,
                          ticks: int | None, fresh_setup: bool, completed: bool, settings_verified: bool,
                          raw_reading: str, evidence: list[str]) -> dict:
        """Save displayed Fire readings, preserving incomplete trials, and return a checked comparison.

        Use low-1=55%, high-1=70%, low-2=55%, high-2=70%. Each needs a fresh
        Setup and natural Go completion. Evidence must cover setup and final readings.
        Pass null for unreadable numbers and false for unverified conditions.
        Percent burned is the monitor value; ticks are model steps, not seconds.
        """
        reading = dict(trial_id=trial_id, density_percent=density_percent, percent_burned=percent_burned,
                       ticks=ticks, fresh_setup=fresh_setup, completed=completed,
                       settings_verified=settings_verified, raw_reading=raw_reading, evidence=evidence)
        analysis = analyze_reading(reading)
        saved = lab.record(trial_id, reading, analysis=analysis,
                           fields={"Density": f"{density_percent:g}%" if density_percent is not None else "Unreadable",
                                   "Ticks": str(ticks) if ticks is not None else "Unreadable"},
                           result=f"{percent_burned:g}% burned" if percent_burned is not None else "Unreadable",
                           summary=f"Saved {trial_id}: {percent_burned}% burned at {density_percent}% density ({analysis['status']}).")
        return {**saved, "comparison": compare_trials(lab.analyses())}

    return [record_fire_trial]


def report(lab) -> str:
    comparison = compare_trials(lab.analyses())
    lines = ["## Density comparison", "", "Displayed burned percentage: $100 \\times N_{burned} / N_{initial}$.", "",
             "| Density | Completed trials | Mean burned | Range |",
             "| --- | --- | --- | --- |"]
    for density, summary in comparison["conditions"].items():
        lines.append(f"| {density}% | {summary['count']} | {summary['mean_percent_burned']:.2f}% | "
                     f"{summary['min_percent_burned']:.1f}–{summary['max_percent_burned']:.1f}% |")
    difference = comparison["difference_percentage_points"]
    if difference is not None:
        lines += ["", f"High minus low mean burned percentage: **{difference:+.2f} percentage points**."]
    lines += ["", f"Comparison: **{comparison['status']}**. {comparison['suggested_follow_up']}", "",
              comparison["limitation"], "", "Model: Wilensky, U. (1997), [NetLogo Fire](https://ccl.northwestern.edu/netlogo/models/Fire)."]
    return "\n".join(lines)
