"""Group finalized transcript segments into silence-delimited turns."""

import math


class TurnAssembler:
    def __init__(self, silence_seconds: float):
        if not math.isfinite(silence_seconds) or silence_seconds <= 0:
            raise ValueError("Silence duration must be a positive finite number.")
        self.silence_seconds = silence_seconds
        self.speaking = False
        self.pending_ids: set[str] = set()
        self.final_ids: set[str] = set()
        self.segments: list[tuple[float, str]] = []
        self.last_activity: float | None = None

    def speech_start(self, now: float) -> None:
        self.speaking = True
        self.last_activity = now

    def speech_end(self, now: float) -> None:
        self.speaking = False
        self.last_activity = now

    def partial(self, utterance_id: str, now: float) -> bool:
        if utterance_id in self.final_ids:
            return False
        self.pending_ids.add(utterance_id)
        self.last_activity = now
        return True

    def final(self, utterance_id: str, text: str, start: float, now: float) -> bool:
        if utterance_id in self.final_ids:
            return False
        self.final_ids.add(utterance_id)
        self.pending_ids.discard(utterance_id)
        if text.strip():
            self.segments.append((start, text.strip()))
        self.last_activity = now
        return True

    def take_ready(self, now: float, *, finishing: bool = False) -> str | None:
        if self.pending_ids:
            return None
        if not finishing and (
            self.speaking
            or self.last_activity is None
            or now - self.last_activity < self.silence_seconds
        ):
            return None
        if not self.segments:
            return None
        text = " ".join(text for _, text in sorted(self.segments, key=lambda item: item[0]))
        self.segments.clear()
        return text
