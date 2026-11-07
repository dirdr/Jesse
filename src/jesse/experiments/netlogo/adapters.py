"""H API and filesystem implementations for this vertical slice."""
import json
from pathlib import Path

class HDesktopAgent:
    def run(self, instructions: str) -> tuple[dict, str]:
        from hai_agents import Client
        client = Client()
        agent = client.agents.create_agent(
            name="jesse-netlogo-desktop",
            description="Bounded NetLogo desktop feasibility test",
            environments=[{"id": "local-mac", "kind": "desktop", "shell": False}],
        )
        result = client.run_session(agent=agent, messages=instructions)
        payload = result.model_dump(mode="json") if hasattr(result, "model_dump") else {
            "status": str(result.status), "answer": str(result.answer)
        }
        return payload, str(result.answer)

class FileExperimentRecords:
    def __init__(self, folder: Path):
        self.folder = folder

    def save(self, session: dict, report: str) -> None:
        (self.folder / "session.json").write_text(json.dumps(session, indent=2))
        (self.folder / "report.md").write_text(report)
