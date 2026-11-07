"""Speak Jesse's announcements with OpenAI text-to-speech. Only events marked `speak` in a run are synthesized."""
import json
import os
from pathlib import Path
import re

SPEECH_URL = "https://api.openai.com/v1/audio/speech"
MODEL = "gpt-4o-mini-tts"
VOICE = "ash"
# An original character voice for Jesse; it does not imitate any real person.
INSTRUCTIONS = (
    "You are Jesse, a young lab assistant from the American Southwest. Casual, energetic, a little jumpy, "
    "genuinely hyped about science. Speak fast with relaxed slang energy, but say every number and unit clearly."
)


def openai_key() -> str:
    return next((value for name in ("OPENAI_API_KEY", "OPENAI_KEY") if (value := os.environ.get(name, "").strip())), "")


def speech_available() -> bool:
    return bool(openai_key())


def spoken_text(folder: Path, event_id: str) -> str | None:
    path = folder / "conversation.jsonl"
    if not path.exists():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("id") == event_id and event.get("speak") and event.get("text"):
            return event["text"]
    return None


def _synthesize(text: str) -> bytes:
    import httpx

    response = httpx.post(SPEECH_URL, timeout=30, headers={"Authorization": f"Bearer {openai_key()}"},
        json={"model": os.environ.get("JESSE_TTS_MODEL") or MODEL, "voice": os.environ.get("JESSE_TTS_VOICE") or VOICE,
              "input": text, "instructions": INSTRUCTIONS, "response_format": "mp3"})
    response.raise_for_status()
    return response.content


def cached_speech(folder: Path, event_id: str, synthesize=None) -> Path | None:
    """Return the mp3 for one spoken event, synthesizing it once and caching it in the run folder."""
    if not re.fullmatch(r"[a-f0-9]{32}", event_id):
        return None
    path = folder / "speech" / f"{event_id}.mp3"
    if path.exists():
        return path
    text = spoken_text(folder, event_id)
    if text is None:
        return None
    audio = (synthesize or _synthesize)(text)
    path.parent.mkdir(exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_bytes(audio)
    temporary.replace(path)
    return path
