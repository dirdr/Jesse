"""Speak Jesse's announcements with OpenAI text-to-speech, in the researcher's language.

Only events marked `speak` in a run are synthesized; each is localized to the language of the run's question first.
"""
import json
import os
from pathlib import Path
import re

SPEECH_URL = "https://api.openai.com/v1/audio/speech"
CHAT_URL = "https://api.openai.com/v1/chat/completions"
MODEL = "gpt-4o-mini-tts"
VOICE = "ash"
# An original character voice for Jesse; it does not imitate any real person.
INSTRUCTIONS = (
    "You are Jesse, a young lab assistant from the American Southwest. Casual, energetic, a little jumpy, "
    "genuinely hyped about science. Speak fast with relaxed slang energy, but say every number and unit clearly. "
    "Speak in the language of the text, with a natural native accent for that language."
)
TRANSLATE = (
    "You localize short spoken announcements from a lab assistant called Jesse. Rewrite the announcement in the "
    "language the researcher used in their question, in a casual spoken tone. Keep every number, unit, trial name "
    "and outcome exactly as given; do not add or remove facts. If it is already in that language, return it unchanged. "
    "Reply with the announcement only."
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
    path = folder / "speech" / f"{event_id}.mp3"
    if path.exists():
        return path
    text = spoken_text(folder, event_id)
    if text is None:
        return None
    question = researcher_question(folder)
    if question:
        try:
            text = (translate or _translate)(text, question)
        except Exception:
            pass  # Speak the original announcement rather than nothing.
    audio = (synthesize or _synthesize)(text)
    path.parent.mkdir(exist_ok=True)
    (path.parent / f"{event_id}.txt").write_text(text, encoding="utf-8")
    temporary = path.with_suffix(".tmp")
    temporary.write_bytes(audio)
    temporary.replace(path)
    return path
