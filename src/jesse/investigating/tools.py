"""Built-in tools any context can enable by name in context.toml."""
from collections.abc import Callable

from .lab import Lab

OBSERVATION_STATUSES = {"observed", "unreadable", "interrupted"}


def builtin_tools(lab: Lab, names: tuple[str, ...]) -> list[Callable]:
    def publish_update(update_id: str, kind: str, text: str) -> dict:
        """Tell the researcher a concise plan, finding, follow_up or blocker.

        Use one or two accessible sentences at meaningful milestones. No narration
        of routine clicks or private reasoning. Keep a stable update_id on retries.
        """
        return lab.update(update_id, kind, text)

    def acknowledge_researcher_message(event_id: str, status: str, text: str) -> dict:
        """Acknowledge a researcher message as acknowledged, applied or rejected.

        Read the message ID supplied with its text. Say applied only after checking
        the requested change actually took effect; explain a rejected change. Preserve
        original measurements and the fixed scope, trial limit and time budget.
        """
        return lab.acknowledge(event_id, status, text)

    def record_observation(trial_id: str, readings: dict[str, float | None], units: dict[str, str],
                           raw_reading: str, evidence: list[str], status: str = "observed",
                           note: str | None = None) -> dict:
        """Save actual readings from the screen immediately, before any interpretation.

        readings maps each measured quantity to its displayed value (null if unreadable);
        units maps the same names to the displayed unit. Preserve the raw displayed text and
        nonempty evidence references. status is observed, unreadable or interrupted. Reuse a
        trial_id only for an identical retry. Require recorded=true before continuing.
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

    available = {tool.__name__: tool for tool in (publish_update, acknowledge_researcher_message, record_observation)}
    return [available[name] for name in names]
