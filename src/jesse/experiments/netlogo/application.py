"""Execute the NetLogo experiment through injected boundaries."""
from .domain import PROMPT
from .ports import DesktopAgent, ExperimentRecords

def run_experiment(agent: DesktopAgent, records: ExperimentRecords) -> None:
    session, report = agent.run(PROMPT)
    records.save(session, report)
