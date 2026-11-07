"""Execute the NetLogo experiment through injected boundaries."""
from .domain import PROMPT
from .ports import DesktopAgent, ExperimentRecords

def run_experiment(agent: DesktopAgent, records: ExperimentRecords, instructions: str = PROMPT) -> str:
    session, report = agent.run(instructions, records)
    records.save(session, report)
    status = session.get("status")
    if status in ("failed", "interrupted"):
        outcome, reason = "blocked", "The desktop session did not complete. Inspect retained events and replay."
    elif status == "timed_out":
        outcome, reason = "inconclusive", "The session reached its execution limit. Prior evidence is retained."
    else:
        outcome, reason = "inconclusive", "Session finished; verify both trials and evidence in replay before accepting desktop feasibility."
    records.finish(outcome, reason)
    return outcome
