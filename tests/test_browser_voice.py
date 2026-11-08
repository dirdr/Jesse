"""Browser voice routes work on hosts without PortAudio or input devices."""
import os
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

from jesse.conversation.application import RunManager
from jesse.conversation.web import create_app


class BrowserVoiceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.manager = RunManager(Path(self.directory.name))
        self.client = TestClient(create_app(self.manager))
        token = re.search(r'name="jesse-token" content="([^"]+)"', self.client.get("/").text).group(1)
        self.headers = {"x-jesse-token": token}

    def test_browser_availability_does_not_probe_server_microphone(self):
        with patch.dict(os.environ, {"GLADIA_API_KEY": "server-secret"}), \
                patch("jesse.conversation.voice.voice_unavailable", side_effect=AssertionError("server audio queried")):
            self.assertEqual(self.client.get("/api/voice/browser").json(), {"available": True, "reason": None})

    def test_session_has_matching_pcm_format_and_keeps_key_server_side(self):
        response = httpx.Response(200, request=httpx.Request("POST", "https://api.gladia.io/v2/live"),
                                  json={"url": "wss://api.gladia.io/v2/live?token=temporary", "id": "session"})
        with patch.dict(os.environ, {"GLADIA_API_KEY": "server-secret"}), \
                patch("jesse.conversation.browser_voice.httpx.post", return_value=response) as post:
            result = self.client.post("/api/voice/session", headers=self.headers)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json(), {"url": "wss://api.gladia.io/v2/live?token=temporary"})
        self.assertNotIn("server-secret", result.text)
        self.assertEqual(post.call_args.kwargs["headers"], {"x-gladia-key": "server-secret"})
        config = post.call_args.kwargs["json"]
        self.assertEqual((config["encoding"], config["sample_rate"], config["bit_depth"], config["channels"]),
                         ("wav/pcm", 16000, 16, 1))
        self.assertTrue(config["messages_config"]["receive_final_transcripts"])

    def test_missing_key_and_provider_errors_are_actionable(self):
        with patch.dict(os.environ, {"GLADIA_API_KEY": ""}):
            self.assertFalse(self.client.get("/api/voice/browser").json()["available"])
            self.assertEqual(self.client.post("/api/voice/session", headers=self.headers).status_code, 409)
        with patch("jesse.conversation.web.create_browser_session", side_effect=RuntimeError("provider-secret")):
            response = self.client.post("/api/voice/session", headers=self.headers)
            self.assertEqual(response.status_code, 502)
            self.assertNotIn("provider-secret", response.text)

    def test_final_browser_turn_starts_then_steers_through_existing_controller(self):
        with patch.object(self.manager, "start", return_value="browser-run") as start:
            response = self.client.post("/api/voice/turn", headers=self.headers, json={"text": "Measure gravity"})
        self.assertEqual(response.json()["action"], "started")
        start.assert_called_once_with("Measure gravity")
        self.manager.current_id = "browser-run"
        with patch.object(self.manager, "snapshot", return_value={"active": True, "can_message": True}), \
                patch.object(self.manager, "message") as message:
            response = self.client.post("/api/voice/turn", headers=self.headers, json={"text": "Repeat it"})
        self.assertEqual(response.json()["action"], "steered")
        self.assertEqual(message.call_args.args[0], "browser-run")
        self.assertEqual(message.call_args.args[2:], ("Repeat it", "voice"))

    def test_browser_routes_reject_forged_and_empty_requests(self):
        self.assertEqual(self.client.post("/api/voice/session").status_code, 403)
        self.assertEqual(self.client.post("/api/voice/turn", json={"text": "Q"}).status_code, 403)
        for text in ("", "   ", "x" * 4001):
            self.assertEqual(self.client.post("/api/voice/turn", headers=self.headers, json={"text": text}).status_code, 422)
