import contextlib
import io
import os
import sys
import types
import unittest
from unittest.mock import patch

from jesse.voice.live import BLOCK_SIZE, SAMPLE_RATE, main, run_live_preview


def transcript(text, is_final, utterance_id="one"):
    starts = {"one": 0, "two": 1, "three": 2}
    return types.SimpleNamespace(
        type="transcript",
        data=types.SimpleNamespace(
            id=utterance_id,
            is_final=is_final,
            utterance=types.SimpleNamespace(text=text, start=float(starts.get(utterance_id, 0))),
        ),
    )


class FakeSession:
    def __init__(self):
        self.handlers = {}
        self.audio = []
        self.stopped = False
        self.closed = False
        self.ready = True
        self.finish_on_stop = True

    def on(self, name):
        def register(callback):
            self.handlers[name] = callback
            return callback
        return register

    def wait_until_ready(self, timeout):
        return self.ready

    def send_audio(self, audio):
        self.audio.append(audio)
        self.handlers["message"](transcript("Compare", False))
        self.handlers["message"](transcript("Compare the rates.", True))
        self.handlers["message"](transcript("Compare the rates.", True))
        self.handlers["message"](transcript("Repeat the first trial.", True, "two"))

    def stop_recording(self):
        self.stopped = True
        if self.finish_on_stop:
            self.handlers["message"](transcript("Final words.", True, "three"))
            self.handlers["ended"](types.SimpleNamespace(code=1000, reason=None))

    def end_session(self):
        self.closed = True

    def join(self, timeout):
        return True


class FakeClient:
    def __init__(self, session):
        self.session = session
        self.options = None

    def live(self):
        return self

    def start_session(self, options):
        self.options = options
        return self.session


class FakeStream:
    def __init__(self, **options):
        self.options = options
        self.reads = 0
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.closed = True

    def read(self, frames):
        if self.reads:
            raise KeyboardInterrupt
        self.reads += 1
        return b"\x01\x00", False


class LiveVoiceTests(unittest.TestCase):
    def test_streams_and_prints_final_messages_only_once(self):
        session = FakeSession()
        client = FakeClient(session)
        streams = []

        def stream_factory(**options):
            stream = FakeStream(**options)
            streams.append(stream)
            return stream

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            run_live_preview(client, stream_factory)

        self.assertEqual(client.options.model, "solaria-1")
        self.assertEqual(client.options.encoding, "wav/pcm")
        self.assertTrue(client.options.messages_config.receive_partial_transcripts)
        self.assertTrue(client.options.messages_config.receive_speech_events)
        self.assertEqual(client.options.endpointing, 0.3)
        self.assertEqual(client.options.maximum_duration_without_endpointing, 15)
        self.assertEqual(streams[0].options, {
            "samplerate": SAMPLE_RATE, "channels": 1, "dtype": "int16", "blocksize": BLOCK_SIZE
        })
        self.assertEqual(session.audio, [b"\x01\x00"])
        self.assertTrue(streams[0].closed)
        self.assertTrue(session.stopped)
        self.assertTrue(session.closed)
        text = output.getvalue()
        self.assertIn("Partial (not sent): Compare", text)
        self.assertEqual(text.count("--- Message for H (not sent) ---"), 1)
        self.assertIn("Researcher request transcribed by Gladia "
                      "(the transcript may contain recognition errors):\n\n"
                      "Compare the rates. Repeat the first trial. Final words.", text)
        self.assertIn("Final words.", text)

    def test_custom_turn_callback_receives_raw_transcript_after_finalization(self):
        session = FakeSession()
        received = []
        with contextlib.redirect_stdout(io.StringIO()):
            run_live_preview(
                FakeClient(session), FakeStream,
                on_turn=received.append, on_partial=lambda text: None,
            )
        self.assertEqual(
            received, ["Compare the rates. Repeat the first trial. Final words."]
        )

    def test_completed_turn_is_delivered_during_listening(self):
        session = FakeSession()
        clock = [0.0]
        received = []

        def send_audio(audio):
            session.audio.append(audio)
            session.handlers["message"](types.SimpleNamespace(type="speech_start"))
            session.handlers["message"](transcript("First request.", True))
            session.handlers["message"](types.SimpleNamespace(type="speech_end"))

        session.send_audio = send_audio

        class ClockedStream(FakeStream):
            def read(self, frames):
                self.reads += 1
                if self.reads == 1:
                    return b"\x00\x00", False
                if self.reads == 2:
                    clock[0] = 1.49
                    return b"\x00\x00", False
                if self.reads == 3:
                    self_test.assertEqual(received, [])
                    clock[0] = 1.5
                    return b"\x00\x00", False
                self_test.assertEqual(received, ["First request."])
                raise KeyboardInterrupt

        self_test = self
        # Send only the first chunk's events; later chunks represent silence.
        original_send = session.send_audio

        def send_once(audio):
            if not session.audio:
                original_send(audio)

        session.send_audio = send_once
        session.finish_on_stop = False

        def stop():
            session.handlers["ended"](types.SimpleNamespace(code=1000, reason=None))

        session.stop_recording = stop
        with patch("jesse.voice.live.time.monotonic", side_effect=lambda: clock[0]):
            with contextlib.redirect_stdout(io.StringIO()):
                run_live_preview(FakeClient(session), ClockedStream, on_turn=received.append)

    def test_incomplete_partial_on_stop_is_reported_without_emitting_turn(self):
        session = FakeSession()

        def stop():
            session.handlers["message"](transcript("Incomplete", False, "unfinished"))
            session.handlers["ended"](types.SimpleNamespace(code=1000, reason=None))

        session.stop_recording = stop
        received = []
        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, "without final transcripts"):
                run_live_preview(
                    FakeClient(session), FakeStream,
                    on_turn=received.append, on_partial=lambda text: None,
                )
        self.assertEqual(received, [])
    def test_overflow_fails_and_closes_session(self):
        class OverflowStream(FakeStream):
            def read(self, frames):
                return b"", True

        session = FakeSession()
        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, "overflowed"):
                run_live_preview(FakeClient(session), OverflowStream)
        self.assertFalse(session.stopped)
        self.assertTrue(session.closed)

    def test_failed_connection_closes_session_without_recording(self):
        session = FakeSession()
        session.ready = False
        with self.assertRaisesRegex(RuntimeError, "did not connect"):
            run_live_preview(FakeClient(session), FakeStream)
        self.assertTrue(session.closed)
        self.assertEqual(session.audio, [])

    def test_unexpected_disconnect_is_reported(self):
        session = FakeSession()

        class DisconnectStream(FakeStream):
            def read(self, frames):
                session.handlers["ended"](types.SimpleNamespace(code=1006, reason="lost"))
                return b"\x01\x00", False

        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, "1006.*lost"):
                run_live_preview(FakeClient(session), DisconnectStream)
        self.assertEqual(session.audio, [])
        self.assertTrue(session.closed)

    def test_stop_timeout_is_reported(self):
        session = FakeSession()
        session.finish_on_stop = False
        with patch("jesse.voice.live.STOP_TIMEOUT", 0):
            with contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(RuntimeError, "final transcript may be missing"):
                    run_live_preview(FakeClient(session), FakeStream)
        self.assertTrue(session.closed)

    def test_missing_key_is_reported(self):
        with patch.dict(os.environ, {}, clear=True):
            with contextlib.redirect_stderr(io.StringIO()) as output:
                self.assertEqual(main([]), 1)
        self.assertIn("GLADIA_API_KEY", output.getvalue())

    def test_microphone_device_errors_are_reported(self):
        class DeviceError(Exception):
            pass

        def query_devices(*, kind):
            raise DeviceError("no input device")

        sounddevice = types.SimpleNamespace(
            PortAudioError=DeviceError, query_devices=query_devices
        )
        with patch.dict(os.environ, {"GLADIA_API_KEY": "test-key"}):
            with patch.dict(sys.modules, {"sounddevice": sounddevice}):
                with contextlib.redirect_stderr(io.StringIO()) as output:
                    self.assertEqual(main([]), 1)
        self.assertIn("no input device", output.getvalue())
