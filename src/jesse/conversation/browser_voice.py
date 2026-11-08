"""Create browser transcription sessions without accessing the server's audio devices."""
import os

import httpx


def browser_voice_unavailable() -> str | None:
    if not os.environ.get("GLADIA_API_KEY", "").strip():
        return "Configure GLADIA_API_KEY to use voice input."
    return None


def create_browser_session() -> dict:
    reason = browser_voice_unavailable()
    if reason:
        raise ValueError(reason)
    # Only the temporary session URL reaches the browser, never the API key.
    response = httpx.post(
        "https://api.gladia.io/v2/live", timeout=20,
        headers={"x-gladia-key": os.environ["GLADIA_API_KEY"].strip()},
        json={
            "model": "solaria-1", "encoding": "wav/pcm", "sample_rate": 16000,
            "bit_depth": 16, "channels": 1, "endpointing": 0.3,
            "maximum_duration_without_endpointing": 15,
            "language_config": {"languages": ["fr", "en"], "code_switching": True},
            "pre_processing": {"audio_enhancer": True, "speech_threshold": 0.8},
            "messages_config": {"receive_partial_transcripts": True,
                                "receive_final_transcripts": True, "receive_speech_events": True},
        },
    )
    response.raise_for_status()
    data = response.json()
    if not isinstance(data.get("url"), str) or not data["url"].startswith("wss://"):
        raise RuntimeError("Gladia did not return a secure transcription session.")
    return {"url": data["url"]}
