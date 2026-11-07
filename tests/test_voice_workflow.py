import contextlib
from dataclasses import dataclass
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import types
import unittest
from unittest.mock import patch

from jesse.voice.live import main
from jesse.voice.preparation import PreparedRequest
from jesse.voice.workflow import VoiceWorkflow


PREPARED = PreparedRequest(
    objective="Étudier le pH", supplied_information=["pH 4,76"],
    missing_information=["Concentration"], suggested_approach=["Vérifier le calcul"],
    limitations=["Outils non vérifiés"],
)


@dataclass
class FakeResult:
    status: str


class FakeHandle:
    id = "session-1"

    def __init__(self):
        self.cancelled = threading.Event()

    def get(self):
        return types.SimpleNamespace(agent_view_url="https://example.test/view", status="running")

    def stream(self, **kwargs):
        yield {"type": "AnswerEvent", "data": {"kind": "answer_event", "answer": "Réponse H"}}
        self.cancelled.wait(5)

    def wait_for_completion(self, **kwargs):
        return FakeResult(status="interrupted")

    def cancel(self):
        self.cancelled.set()


class FakeClient:
    def __init__(self):
        self.handle = FakeHandle()
        self.starts = []
        self.messages = []
        self.sessions = self

    def start_session(self, **kwargs):
        self.starts.append(kwargs)
        return self.handle

    def send_session_messages(self, session_id, *, request):
        self.messages.append((session_id, request.message))


class VoiceWorkflowTests(unittest.TestCase):
    def test_microphone_turns_are_enriched_and_sent_to_the_same_h_session(self):
        questions = ["Une solution de pH 4,76.", "Et avec davantage de sel ?"]
        client = FakeClient()
        sounddevice = types.SimpleNamespace(
            query_devices=lambda *args, **kwargs: {"name": "synthetic"},
            RawInputStream=object,
            PortAudioError=type("PortAudioError", (Exception,), {}),
        )

        def capture(client, stream_factory, *, on_turn, silence_seconds, input_device):
            for question in questions:
                on_turn(question)

        with tempfile.TemporaryDirectory() as directory:
            previous = Path.cwd()
            try:
                os.chdir(directory)
                with patch.dict(os.environ, {"GLADIA_API_KEY": "test", "OPENAI_API_KEY": "test", "HAI_API_KEY": "test"}, clear=True):
                    with patch.dict(sys.modules, {"sounddevice": sounddevice}):
                        with patch("jesse.voice.live.run_live_preview", side_effect=capture):
                            with patch("pydantic_ai.Agent.run_sync", return_value=types.SimpleNamespace(output=PREPARED)) as model:
                                with patch("hai_agents.Client", return_value=client):
                                    with contextlib.redirect_stdout(io.StringIO()):
                                        self.assertEqual(main(["--run"]), 0)
                self.assertEqual([json.loads(call.args[0])["transcript"] for call in model.call_args_list], questions)
                self.assertEqual(len(client.starts), 1)
                self.assertEqual(json.loads(client.starts[0]["messages"])["original_transcript"], questions[0])
                self.assertEqual(client.starts[0]["idle_timeout_s"], 600)
                self.assertEqual(client.messages[0][0], client.handle.id)
                self.assertEqual(json.loads(client.messages[0][1])["original_transcript"], questions[1])
                self.assertEqual(json.loads(client.messages[0][1])["prepared_request"]["objective"], PREPARED.objective)
                folder = next((Path(directory) / "runs").iterdir())
                self.assertEqual(json.loads((folder / "turn-0002.json").read_text())["status"], "accepted")
                self.assertTrue(client.handle.cancelled.is_set())
            finally:
                os.chdir(previous)

    def test_missing_h_key_blocks_before_capture(self):
        with patch.dict(os.environ, {"GLADIA_API_KEY": "test", "OPENAI_API_KEY": "test"}, clear=True):
            with contextlib.redirect_stderr(io.StringIO()) as output:
                self.assertEqual(main(["--run"]), 1)
        self.assertIn("HAI_API_KEY", output.getvalue())

    def test_delivery_failure_is_not_retried_or_reported_as_delivered(self):
        client = FakeClient()
        with tempfile.TemporaryDirectory() as directory:
            workflow = VoiceWorkflow("test", client=client, root=Path(directory))
            with patch.object(workflow.preparer, "prepare", return_value=PREPARED):
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    workflow.submit("première question")
                    with patch.object(client, "send_session_messages", side_effect=RuntimeError("secret")):
                        with self.assertRaises(RuntimeError):
                            workflow.submit("suite")
                    self.assertTrue(workflow.close())
            receipt = json.loads((workflow.folder / "turn-0002.json").read_text())
            self.assertEqual(receipt["status"], "delivery_unknown")
            self.assertNotIn("secret", json.dumps(receipt))
            self.assertEqual(len(client.starts), 1)

    def test_failed_first_session_is_not_silently_recreated(self):
        client = FakeClient()
        with tempfile.TemporaryDirectory() as directory:
            workflow = VoiceWorkflow("test", client=client, root=Path(directory))
            with patch.object(workflow.preparer, "prepare", return_value=PREPARED):
                with patch.object(client, "start_session", side_effect=RuntimeError("unavailable")) as start:
                    with contextlib.redirect_stdout(io.StringIO()):
                        with self.assertRaises(RuntimeError):
                            workflow.submit("question")
                        with self.assertRaisesRegex(RuntimeError, "no new session"):
                            workflow.submit("suite")
                    self.assertEqual(start.call_count, 1)


if __name__ == "__main__":
    unittest.main()
