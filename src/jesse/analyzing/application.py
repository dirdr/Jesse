"""Run a predefined analysis through observation and artifact boundaries."""
from typing import Protocol

from jesse.recording.domain import Observation
from .domain import compare_rates


class AnalysisRecords(Protocol):
    def load_observations(self) -> list[Observation]: ...
    def save_analysis(self, analysis: dict) -> None: ...


def analyze_measurements(records: AnalysisRecords) -> dict:
    analysis = compare_rates(records.load_observations())
    records.save_analysis(analysis)
    return analysis
