"""Transcribe live Gladia turns and optionally prepare or submit them to H."""

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
    LiveV2LanguageConfig,
    LiveV2MessagesConfig,
    LiveV2PreProcessingConfig,
    LiveV2WebSocketMessage,
)

from .prompt import build_spoken_request
from .planning import VoicePlanningQueue
from .turns import TurnAssembler

SAMPLE_RATE = 16000
BLOCK_SIZE = 3200
START_TIMEOUT = 30
STOP_TIMEOUT = 30
TURN_SILENCE = 1.5
# Restrict detection to the languages researchers actually speak; open auto-detection drifts on short or noisy turns.
LANGUAGES = ("fr", "en")
# Close to 1 rejects more background sound (other voices, speakers) as non-speech.
SPEECH_THRESHOLD = 0.8


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
    input_device: int | None = None,
    languages: tuple[str, ...] = LANGUAGES,
    speech_threshold: float = SPEECH_THRESHOLD,
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
            language_config=LiveV2LanguageConfig(languages=list(languages), code_switching=len(languages) > 1),
            pre_processing=LiveV2PreProcessingConfig(audio_enhancer=True, speech_threshold=speech_threshold),
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

        stream_options = {
            "samplerate": SAMPLE_RATE, "channels": 1,
            "dtype": "int16", "blocksize": BLOCK_SIZE,
        }
        if input_device is not None:
            stream_options["device"] = input_device
        with stream_factory(**stream_options) as stream:
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--silence-seconds", type=float, default=TURN_SILENCE,
        help="seconds without speech before completing a turn (default: 1.5)",
    )
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument(
        "--prepare", action="store_true",
        help="enrich each completed turn for an H prompt preview without starting H",
    )
    modes.add_argument(
        "--run", action="store_true",
        help="enrich completed turns and send them to one interactive H browser session",
    )
    parser.add_argument("--planner-model", help="OpenAI model for preparing voice turns")
    parser.add_argument("--list-inputs", action="store_true", help="list microphone devices and exit")
    parser.add_argument("--input-device", type=int, metavar="INDEX", help="microphone device index")
    args = parser.parse_args(argv)
    try:
        TurnAssembler(args.silence_seconds)
    except ValueError as error:
        parser.error(str(error))
    if not args.list_inputs and not os.environ.get("GLADIA_API_KEY", "").strip():
        print("Blocked: set GLADIA_API_KEY in the environment.", file=sys.stderr)
        return 1
    if not args.list_inputs and (args.prepare or args.run) and not any(
        os.environ.get(name, "").strip() for name in ("OPENAI_API_KEY", "OPENAI_KEY")
    ):
        print("Blocked: set OPENAI_API_KEY or OPENAI_KEY for voice planning.", file=sys.stderr)
        return 1
    if not args.list_inputs and args.run and not os.environ.get("HAI_API_KEY", "").strip():
        print("Blocked: set HAI_API_KEY for the H session.", file=sys.stderr)
        return 1
    try:
        import sounddevice
    except OSError as error:
        print(f"Voice preview failed: {error}", file=sys.stderr)
        return 1
    try:
        if args.list_inputs:
            for index, device in enumerate(sounddevice.query_devices()):
                if device["max_input_channels"] > 0:
                    print(f'{index}: {device["name"]} ({device["max_input_channels"]} input channels)')
            return 0
        device = sounddevice.query_devices(args.input_device, kind="input")
        print(f'Microphone: {device["name"]}', flush=True)
        if args.run:
            print("Audio is streamed to Gladia; final turns are sent to OpenAI and H.", flush=True)
            print("Ctrl+C stops listening and cancels the H session, including unfinished work.", flush=True)
        else:
            print("Audio is streamed to Gladia. No message is sent to H.", flush=True)
        if args.prepare or args.run:
            workflow = None
            if args.run:
                from .workflow import VoiceWorkflow

                model = args.planner_model or os.environ.get("OPENAI_MODEL", "gpt-5-mini")
                workflow = VoiceWorkflow(model)

            def plan(transcript: str) -> int:
                if workflow is not None:
                    return workflow.submit(transcript)
                if args.prepare:
                    from .preparation import PydanticRequestPreparer, print_prepared_request

                    model = args.planner_model or os.environ.get("OPENAI_MODEL", "gpt-5-mini")
                    result = PydanticRequestPreparer(model).prepare(transcript)
                    print_prepared_request(transcript, result)
                return 0

            planning = VoicePlanningQueue(plan, operation="H submission" if args.run else "planning")

            def submit_turn(transcript: str) -> None:
                print_turn(transcript)
                planning.submit(transcript)

            try:
                run_live_preview(
                    GladiaClient(), sounddevice.RawInputStream,
                    on_turn=submit_turn, silence_seconds=args.silence_seconds,
                    input_device=args.input_device,
                )
            finally:
                planning_ok = planning.close()
                workflow_ok = workflow.close() if workflow is not None else True
            if not planning_ok or not workflow_ok:
                return 1
        else:
            run_live_preview(
                GladiaClient(), sounddevice.RawInputStream,
                silence_seconds=args.silence_seconds, input_device=args.input_device,
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
