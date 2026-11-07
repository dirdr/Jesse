"""Preview live Gladia transcripts as messages for H without sending them."""

import argparse
import os
import queue
import sys
import threading
import time
from collections.abc import Callable

from gladiaio_sdk import (
    GladiaClient,
    LiveV2InitRequest,
    LiveV2MessagesConfig,
    LiveV2WebSocketMessage,
)

from .prompt import build_spoken_request
from .turns import TurnAssembler

SAMPLE_RATE = 16000
BLOCK_SIZE = 3200
START_TIMEOUT = 30
STOP_TIMEOUT = 30
TURN_SILENCE = 1.5


def print_turn(transcript: str) -> None:
    print(
        "\n--- Message for H (not sent) ---\n"
        f"{build_spoken_request(transcript)}\n"
        "--- End message ---",
        flush=True,
    )


def print_partial(text: str) -> None:
    print(f"Partial (not sent): {text}", flush=True)


def run_live_preview(
    client,
    stream_factory,
    *,
    on_turn: Callable[[str], None] = print_turn,
    on_partial: Callable[[str], None] = print_partial,
    silence_seconds: float = TURN_SILENCE,
) -> None:
    turns = TurnAssembler(silence_seconds)
    session = client.live().start_session(
        LiveV2InitRequest(
            model="solaria-1",
            encoding="wav/pcm",
            sample_rate=SAMPLE_RATE,
            bit_depth=16,
            channels=1,
            endpointing=0.3,
            maximum_duration_without_endpointing=15,
            messages_config=LiveV2MessagesConfig(
                receive_partial_transcripts=True,
                receive_final_transcripts=True,
                receive_speech_events=True,
            ),
        )
    )
    ended = threading.Event()
    errors: list[str] = []
    events: queue.Queue[LiveV2WebSocketMessage] = queue.Queue()

    @session.on("message")
    def on_message(message):
        events.put(message)

    @session.on("error")
    def on_error(error):
        errors.append(str(error))
        ended.set()

    @session.on("ended")
    def on_ended(event):
        if event.code != 1000:
            errors.append(f"Gladia session ended ({event.code}): {event.reason}")
        ended.set()

    def process_events(*, finishing: bool = False) -> None:
        while True:
            try:
                message = events.get_nowait()
            except queue.Empty:
                break
            now = time.monotonic()
            if message.type == "speech_start":
                turns.speech_start(now)
            elif message.type == "speech_end":
                turns.speech_end(now)
            elif message.type == "transcript":
                data = message.data
                text = data.utterance.text.strip()
                if data.is_final:
                    turns.final(data.id, text, data.utterance.start, now)
                elif turns.partial(data.id, now) and text:
                    on_partial(text)
        turn = turns.take_ready(time.monotonic(), finishing=finishing)
        if turn is not None:
            on_turn(turn)

    try:
        if not session.wait_until_ready(timeout=START_TIMEOUT):
            if errors:
                raise RuntimeError(f"Gladia live session failed: {errors[0]}")
            raise RuntimeError("Gladia live session did not connect within 30 seconds.")
        if ended.is_set():
            reason = errors[0] if errors else "unexpected closure"
            raise RuntimeError(f"Gladia live session ended: {reason}")

        with stream_factory(
            samplerate=SAMPLE_RATE, channels=1, dtype="int16", blocksize=BLOCK_SIZE
        ) as stream:
            print("Listening. Speak naturally; press Ctrl+C to stop.", flush=True)
            try:
                while not ended.is_set():
                    process_events()
                    audio, overflowed = stream.read(BLOCK_SIZE)
                    if overflowed:
                        raise RuntimeError("Microphone input overflowed; audio was lost.")
                    if not ended.is_set():
                        session.send_audio(bytes(audio))
            except KeyboardInterrupt:
                print("\nStopping and waiting for final transcripts...", flush=True)

        if errors:
            raise RuntimeError(f"Gladia live session failed: {errors[0]}")
        if ended.is_set():
            raise RuntimeError("Gladia live session ended unexpectedly.")
        session.stop_recording()
        if not ended.wait(STOP_TIMEOUT):
            raise RuntimeError(
                "Gladia did not finish within 30 seconds; final transcript may be missing."
            )
        if errors:
            raise RuntimeError(f"Gladia live session failed: {errors[0]}")
        process_events(finishing=True)
        if turns.pending_ids:
            raise RuntimeError("Gladia ended without final transcripts for all utterances.")
    finally:
        session.end_session()
        session.join(timeout=5)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Preview Gladia live voice turns without sending to H.")
    parser.add_argument(
        "--silence-seconds", type=float, default=TURN_SILENCE,
        help="seconds without speech before completing a turn (default: 1.5)",
    )
    args = parser.parse_args(argv)
    try:
        TurnAssembler(args.silence_seconds)
    except ValueError as error:
        parser.error(str(error))
    if not os.environ.get("GLADIA_API_KEY"):
        print("Blocked: set GLADIA_API_KEY in the environment.", file=sys.stderr)
        return 1
    try:
        import sounddevice
    except OSError as error:
        print(f"Voice preview failed: {error}", file=sys.stderr)
        return 1
    try:
        sounddevice.query_devices(kind="input")
        print("Audio is streamed to Gladia. No message is sent to H.", flush=True)
        run_live_preview(
            GladiaClient(), sounddevice.RawInputStream, silence_seconds=args.silence_seconds
        )
    except KeyboardInterrupt:
        print("\nVoice preview stopped.", file=sys.stderr)
        return 1
    except (sounddevice.PortAudioError, OSError, RuntimeError, ValueError) as error:
        print(f"Voice preview failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
