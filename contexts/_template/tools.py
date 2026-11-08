"""Optional custom tools. Delete this file if the built-in tools are enough.

`tools(lab)` returns plain Python functions; H sees each function's name, typed
arguments and docstring. `report(lab)` returns a Markdown section for report.md.
"""


def tools(lab):
    def record_measurement(trial_id: str, value: float, unit: str, raw_reading: str, evidence: list[str]) -> dict:
        """Save one displayed value with its unit, raw text and screenshot evidence."""
        return lab.record(trial_id, {"value": value, "unit": unit, "raw_reading": raw_reading, "evidence": evidence},
                          fields={"Value": f"{value:g} {unit}"}, summary=f"Saved {trial_id}: {value:g} {unit}.")

    return [record_measurement]


def report(lab) -> str:
    return f"## Summary\n\n{len(lab.observations())} trial(s) recorded."

