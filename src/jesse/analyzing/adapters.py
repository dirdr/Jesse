"""Read raw observations and write separate, reproducible analysis artifacts."""
from dataclasses import fields
import json
from pathlib import Path

from jesse.recording.domain import Observation


def cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


class FileAnalysisRecords:
    def __init__(self, run_folder: Path):
        if not run_folder.is_dir():
            raise ValueError("The run directory does not exist")
        self.run_folder = run_folder

    def load_observations(self) -> list[Observation]:
        observations = []
        names = {field.name for field in fields(Observation)}
        for path in sorted((self.run_folder / "observations").glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload.get("run_id") != self.run_folder.name:
                raise ValueError(f"{path.name}: observation belongs to a different run")
            if payload.get("observation_id") != path.stem:
                raise ValueError(f"{path.name}: observation identity does not match its filename")
            observations.append(Observation(**{key: value for key, value in payload.items() if key in names}))
        return observations

    def save_analysis(self, analysis: dict) -> None:
        folder = self.run_folder / "analyses"
        folder.mkdir(exist_ok=True)
        path = folder / f"{analysis['analysis_id']}.json"
        payload = {"run_id": self.run_folder.name, **analysis}
        if path.exists() and json.loads(path.read_text(encoding="utf-8")) != payload:
            raise ValueError("Conflicting analysis for the same inputs and method")
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, indent=2, allow_nan=False), encoding="utf-8")
        temporary.replace(path)
        lines = [
            "# NetLogo rate comparison", "", f"Status: **{analysis['status']}**", "",
            "This analysis describes the recorded readings. Replay verification remains required.", "",
            "| VOLUME | Mean rate | Unit | Independent trials |", "| --- | --- | --- | --- |",
        ]
        for group in analysis["derived_values"]:
            lines.append(f"| {group['volume']} | {group['mean_rate']:.6g} | {cell(group['unit'])} | {group['repeat_count']} |")
        if analysis["comparison"]:
            comparison = analysis["comparison"]
            lines += ["", f"The recorded mean rate {comparison['direction']}; the high-minus-low difference is {comparison['rate_difference']:.6g} {cell(comparison['unit'])}."]
        lines += ["", "## Checks and limitations", ""]
        lines += [f"- {cell(issue)}" for issue in analysis["issues"] + analysis["limitations"]]
        for excluded in analysis["excluded_observations"]:
            lines.append(f"- Excluded {cell(excluded['observation_id'])}: {cell(excluded['reason'])}")
        if analysis["suggested_follow_up"]:
            lines += ["", "## Suggested follow-up", "", analysis["suggested_follow_up"]["reason"]]
        lines += ["", "## Source observations", ""]
        lines += [f"- [{identifier}](../observations/{identifier}.json)" for identifier in analysis["input_observation_ids"]]
        lines += ["", "Method: `" + analysis["method"] + "`. Raw observations are unchanged.", ""]
        path.with_suffix(".md").write_text("\n".join(lines), encoding="utf-8")
