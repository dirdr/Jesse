"""Build the H-agent message from a Gladia transcript."""


def build_spoken_request(transcript: str) -> str:
    """Wrap a recognized spoken request as a researcher message for H."""
    if not transcript.strip():
        raise ValueError("Transcript must contain a spoken request.")

    return (
        "Researcher request transcribed by Gladia "
        "(the transcript may contain recognition errors):\n\n"
        f"{transcript.strip()}"
    )
