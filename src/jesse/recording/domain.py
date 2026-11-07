"""Observation rules independent of simulator and provider SDKs."""
from dataclasses import asdict, dataclass
from datetime import datetime
import json
import math
import re
from typing import Any


@dataclass(frozen=True)
class Observation:
    observation_id: str
    trial_id: str
    observed_at: str
    settings: dict[str, Any]
    quantity: str
    value: float | None
    unit: str | None
    raw_reading: str
    evidence: list[str]
    interval: dict[str, Any]
    status: str
    reason: str | None = None

    def __post_init__(self) -> None:
        for name in ("observation_id", "trial_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,99}", value):
                raise ValueError(f"{name} must be a safe stable identifier")
        timestamp = datetime.fromisoformat(self.observed_at.replace("Z", "+00:00"))
        if timestamp.utcoffset() is None or timestamp.utcoffset().total_seconds() != 0:
            raise ValueError("observed_at must include the UTC timezone")
        if not isinstance(self.settings, dict) or not self.settings:
            raise ValueError("settings must contain observed control values")
        if not isinstance(self.interval, dict) or set(self.interval) != {"start", "end", "unit"}:
            raise ValueError("interval requires start, end and unit (null when unknown)")
        start, end = self.interval["start"], self.interval["end"]
        for value in (start, end, self.value):
            if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)):
                raise ValueError("readings and interval bounds must be finite numbers or null")
        if start is not None and end is not None and end <= start:
            raise ValueError("interval end must follow its start")
        for name in ("quantity", "raw_reading"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"{name} must be nonempty")
        for unit in (self.unit, self.interval["unit"]):
            if unit is not None and (not isinstance(unit, str) or not unit.strip()):
                raise ValueError("units must be nonempty text or null when unknown")
        if not isinstance(self.evidence, list) or not self.evidence or any(
            not isinstance(item, str) or not item.strip() for item in self.evidence
        ):
            raise ValueError("at least one evidence reference is required")
        if self.status not in ("observed", "unreadable", "interrupted"):
            raise ValueError("invalid observation status")
        if self.status == "observed" and self.value is None:
            raise ValueError("an observed reading needs a numerical value")
        if self.status != "observed" and (not isinstance(self.reason, str) or not self.reason.strip()):
            raise ValueError("incomplete readings require a reason")
        json.dumps(asdict(self), allow_nan=False)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
