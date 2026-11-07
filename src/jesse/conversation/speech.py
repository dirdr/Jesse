"""Speak Jesse's announcements with OpenAI text-to-speech, in the researcher's language.

Only events marked `speak` in a run are synthesized; each is localized to the language of the run's question first.
"""
import hashlib
import json
import os
from pathlib import Path
import re

SPEECH_URL = "https://api.openai.com/v1/audio/speech"
CHAT_URL = "https://api.openai.com/v1/chat/completions"
MODEL = "gpt-4o-mini-tts"
VOICE = "ash"
# The researcher knows what they want: Jesse reports state, it does not explain or perform.
INSTRUCTIONS = (
    "Brisk, neutral lab status readout. Calm and matter-of-fact, no enthusiasm, no pauses for effect. "
    "Say every number and unit clearly. Speak in the language of the text with a natural native accent."
)
TRANSLATE = (
    "Turn this lab status into a terse spoken update of at most 8 words, in the language of the researcher's question. "
    "Keep every number, unit, setting and trial name exactly. Use only facts and names present in the status; never "
    "invent identifiers. For an experiment choice, just name the simulator and what is compared. No filler, no greeting, "
    "no restating the question, no explanation, no opinion. Reply with the update only."
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


def researcher_question(folder: Path) -> str | None:
    path = folder / "conversation.jsonl"
    if not path.exists():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("kind") == "question" and event.get("author") == "researcher" and event.get("text"):
            return event["text"]
    return None


def _translate(text: str, question: str) -> str:
    import httpx

    response = httpx.post(CHAT_URL, timeout=30, headers={"Authorization": f"Bearer {openai_key()}"},
        json={"model": os.environ.get("OPENAI_MODEL") or "gpt-5-mini", "reasoning_effort": "minimal", "messages": [
            {"role": "system", "content": TRANSLATE},
            {"role": "user", "content": f"Researcher question:\n{question}\n\nAnnouncement:\n{text}"}]})
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip() or text


def _synthesize(text: str) -> bytes:
    import httpx

    response = httpx.post(SPEECH_URL, timeout=30, headers={"Authorization": f"Bearer {openai_key()}"},
        json={"model": os.environ.get("JESSE_TTS_MODEL") or MODEL, "voice": os.environ.get("JESSE_TTS_VOICE") or VOICE,
              "input": text, "instructions": INSTRUCTIONS, "response_format": "mp3"})
    response.raise_for_status()
    return response.content


def cached_speech(folder: Path, event_id: str, synthesize=None, translate=None) -> Path | None:
    """Return the mp3 for one spoken event, synthesizing it once and caching it in the run folder."""
    if not re.fullmatch(r"[a-f0-9]{32}", event_id):
        return None
    text = spoken_text(folder, event_id)
    return None if text is None else _spoken(folder, event_id, text, synthesize, translate)


def cached_step_speech(folder: Path, index: int, synthesize=None, translate=None) -> Path | None:
    """Return the mp3 announcing one step of the agent's current plan."""
    from .live import live_state

    plan = live_state(folder)["plan"]
    if not 0 <= index < len(plan):
        return None
    text = f"Step {index + 1}/{len(plan)}: {plan[index]['title']}"
    key = "step-" + hashlib.sha256(text.encode()).hexdigest()[:16]
    return _spoken(folder, key, text, synthesize, translate)


def _spoken(folder: Path, key: str, text: str, synthesize, translate) -> Path:
    path = folder / "speech" / f"{key}.mp3"
    if path.exists():
        return path
    question = researcher_question(folder)
    if question:
        try:
            text = (translate or _translate)(text, question)
        except Exception:
            pass  # Speak the original announcement rather than nothing.
    audio = (synthesize or _synthesize)(text)
    path.parent.mkdir(exist_ok=True)
    (path.parent / f"{key}.txt").write_text(text, encoding="utf-8")
    temporary = path.with_suffix(".tmp")
    temporary.write_bytes(audio)
    temporary.replace(path)
    return path
