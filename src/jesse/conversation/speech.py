"""Speak Jesse's announcements with ElevenLabs (or OpenAI) text-to-speech, in the researcher's language.

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
# Jesse narrates like a confident expert: natural first-person sentences, strictly faithful to the lab status.
INSTRUCTIONS = (
    "Confident, expert lab assistant giving a live readout to a researcher. Warm but assured, crisp and steady pace, "
    "no hesitation. Say every number and unit clearly. Speak in the language of the text with a natural native accent."
)
TRANSLATE = (
    "You are Jesse, the best lab assistant there is, narrating a live simulator experiment to a researcher who knows "
    "exactly what they want. Write ONE short, natural, confident spoken sentence (at most 15 words), first person, "
    "present tense, in the language of the researcher's question. Perfect grammar and spelling. Translate interface "
    "terms naturally (stockroom, workbench, button, menu); keep chemical, assignment and simulator names as they are "
    "(Compound Y, Coolant I, NetLogo). Keep every number and unit exact and say them the way a native speaker reads them. "
    "Strictly faithful: state only facts present in the lab status. Never add quantities, temperatures, names or goals "
    "that are not in it, and never drop a measured value. Sound sure of yourself: no hedging, no apologies, no talk of "
    "failed attempts; say what you are doing now. No filler, no greeting, no restating the question. Reply with the sentence only."
)
# Fast and the most faithful of the models compared on real agent actions.
WRITER_MODEL = "gpt-4.1"


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
        json={"model": os.environ.get("JESSE_SPEECH_MODEL") or WRITER_MODEL, "messages": [
            {"role": "system", "content": TRANSLATE},
            {"role": "user", "content": f"Researcher question (reply in its language):\n{question}\n\nLab status:\n{text}"}]})
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip() or text


ELEVENLABS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format=mp3_44100_128"
ELEVENLABS_MODEL = "eleven_multilingual_v2"
# "Liam", a premade ElevenLabs library voice (young, confident American). Not a clone of anyone.
ELEVENLABS_VOICE = "TX3LPaxmHKxFdv7VOQHJ"


def elevenlabs_key() -> str:
    return os.environ.get("ELEVENLABS_API_KEY", "").strip()


def _synthesize(text: str) -> bytes:
    """ElevenLabs when its key is set; OpenAI text-to-speech otherwise."""
    import httpx

    if elevenlabs_key():
        voice = os.environ.get("JESSE_ELEVENLABS_VOICE") or ELEVENLABS_VOICE
        response = httpx.post(ELEVENLABS_URL.format(voice=voice), timeout=30, headers={"xi-api-key": elevenlabs_key()},
            json={"text": text, "model_id": os.environ.get("JESSE_ELEVENLABS_MODEL") or ELEVENLABS_MODEL,
                  "voice_settings": {"stability": 0.5, "similarity_boost": 0.75, "style": 0.3, "use_speaker_boost": True}})
        response.raise_for_status()
        return response.content
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


def cached_action_speech(folder: Path, index: int, synthesize=None, translate=None) -> Path | None:
    """Return the mp3 for one agent action: what the agent says it is doing, condensed."""
    from .live import live_state

    actions = live_state(folder)["actions"]
    if not 0 <= index < len(actions):
        return None
    action = actions[index]
    args = action.get("args") or {}
    text = action.get("text") or " ".join(str(part) for part in (action["tool"], args.get("element") or args.get("text") or "") if part)
    key = "action-" + hashlib.sha256(f"{index}:{text}".encode()).hexdigest()[:16]
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
