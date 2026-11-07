"""One persona selection controls the worker, speech and persisted run identity."""
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest import mock

from fastapi.testclient import TestClient
import httpx

from jesse.conversation import speech
from jesse.conversation.application import RunManager
from jesse.conversation.web import create_app
from jesse.personality import get_persona, run_persona


class Process:
    active = True

    def poll(self):
        return None if self.active else 0


class PersonaTests(unittest.TestCase):
    def test_selection_is_saved_with_run_and_worker_and_cannot_change_mid_run(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.dict("os.environ", {}, clear=True):
            worker = Process()
            popen = mock.Mock(return_value=worker)
            manager = RunManager(Path(directory), popen=popen)
            client = TestClient(create_app(manager))
            token = re.search(r'name="jesse-token" content="([^"]+)"', client.get("/").text).group(1)
            headers = {"x-jesse-token": token}
            self.assertEqual(client.get("/api/personas").json()["selected"], "pinkman")
            self.assertEqual(client.post("/api/persona", json={"id": "plain"}, headers=headers).status_code, 200)
            response = client.post("/api/runs", json={"text": "Compare coolant."}, headers=headers)
            self.assertEqual(response.status_code, 202)
            run_id = response.json()["run_id"]
            folder = manager.folder(run_id)
            self.assertEqual(run_persona(folder).id, "plain")
            self.assertEqual(popen.call_args.kwargs["env"]["JESSE_PERSONA"], "plain")
            self.assertEqual(client.get(f"/api/runs/{run_id}").json()["persona"], "plain")
            self.assertEqual(client.post("/api/persona", json={"id": "pinkman"}, headers=headers).status_code, 409)
            worker.active = False
            self.assertEqual(client.post("/api/persona", json={"id": "pinkman"}, headers=headers).status_code, 200)
            self.assertEqual(run_persona(folder).id, "plain")
            self.assertEqual(client.post("/api/persona", json={"id": "unknown"}, headers=headers).status_code, 422)
            self.assertEqual(client.post("/api/persona", json={"id": "plain"}).status_code, 403)

    def test_persisted_pinkman_uses_its_own_voice_even_when_global_persona_is_plain(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.dict("os.environ", {
            "JESSE_PERSONA": "plain", "OPENAI_KEY": "writer", "FISH_API_KEY": "fish",
            "JESSE_FISH_VOICE": "wrong-voice", "JESSE_FISH_MODEL": "wrong-model",
        }, clear=True):
            folder = Path(directory)
            (folder / "persona.json").write_text(json.dumps({"id": "pinkman"}))
            event = "b" * 32
            (folder / "conversation.jsonl").write_text(json.dumps({"id": event, "text": "Opening the lab.", "speak": True}))
            requests = []

            def post(url, **kwargs):
                requests.append((url, kwargs))
                if url == speech.CHAT_URL:
                    self.assertTrue(kwargs["json"]["messages"][0]["content"].startswith(get_persona("pinkman").instructions))
                    return httpx.Response(200, json={"choices": [{"message": {"content": "Alright, opening the lab, man."}}]}, request=httpx.Request("POST", url))
                self.assertEqual(url, speech.FISH_URL)
                self.assertEqual(kwargs["json"]["reference_id"], get_persona("pinkman").voice)
                self.assertEqual(kwargs["headers"]["model"], get_persona("pinkman").model)
                return httpx.Response(200, content=b"fish-mp3", request=httpx.Request("POST", url))

            with mock.patch("httpx.post", side_effect=post):
                self.assertEqual(speech.cached_speech(folder, event).read_bytes(), b"fish-mp3")
            self.assertEqual(len(requests), 2)


if __name__ == "__main__":
    unittest.main()
