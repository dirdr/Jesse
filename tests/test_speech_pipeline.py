"""Exercise the panel's real speech routes through rewriting, provider selection and audio caching."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from fastapi.testclient import TestClient
import httpx

from jesse.conversation import speech
from jesse.conversation.application import RunManager
from jesse.conversation.web import create_app
from jesse.personality import LAB_PARTNER, PLAIN, delivery_instructions
from jesse.investigating.runner import build_prompt
from context_fixtures import synthetic_context


EVENT = "a" * 32
LINE = "Hold up, man. Trial 1 is still uncertain: 50 mL, 22.5 °C."


def write_run(root):
    folder = root / "voice-test"
    folder.mkdir()
    (folder / "conversation.jsonl").write_text("\n".join(json.dumps(event) for event in [
        {"id": "q", "kind": "question", "author": "researcher", "text": "Compare the coolant."},
        {"id": EVENT, "text": "Trial 1 is uncertain: 50 mL, 22.5 °C.", "speak": True},
    ]))
    (folder / "events.jsonl").write_text(json.dumps({"type": "AgentEvent", "timestamp": "t", "data": {
        "kind": "policy_event", "content": "Checking the coolant setup.", "tool_reqs": [
            {"tool_name": "update_plan", "args": {"goals": [{"title": "Check the setup", "status": "running"}]}},
            {"tool_name": "click_web", "args": {"element": "Coolant I"}},
        ]}}))
    return folder


class SpeechPipelineTests(unittest.TestCase):
    def test_all_panel_speech_routes_rewrite_before_fish_synthesis_and_cache(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.dict("os.environ", {
            "OPENAI_KEY": "writer-test", "FISH_API_KEY": "fish-test", "JESSE_FISH_VOICE": "selected-voice",
            "ELEVENLABS_API_KEY": "also-configured", "JESSE_FISH_MODEL": "s2-pro",
        }, clear=True):
            root = Path(directory)
            folder = write_run(root)
            # A pre-personality cached clip must not mask the new writer or voice.
            (folder / "speech").mkdir()
            (folder / "speech" / f"{EVENT}.mp3").write_bytes(b"old-neutral-audio")
            client = TestClient(create_app(RunManager(root)))
            requests = []

            def post(url, **kwargs):
                requests.append((url, kwargs))
                if url == speech.CHAT_URL:
                    messages = kwargs["json"]["messages"]
                    self.assertTrue(messages[0]["content"].startswith(LAB_PARTNER))
                    self.assertIn("status_to_rephrase", json.loads(messages[1]["content"]))
                    return httpx.Response(200, json={"choices": [{"message": {"content": LINE}}]},
                                          request=httpx.Request("POST", url))
                self.assertEqual(url, speech.FISH_URL)
                self.assertEqual(kwargs["headers"]["Authorization"], "Bearer fish-test")
                self.assertEqual(kwargs["headers"]["model"], "s2-pro")
                self.assertEqual(kwargs["json"], {"text": LINE, "reference_id": "selected-voice", "format": "mp3"})
                return httpx.Response(200, content=b"ID3fish-audio", request=httpx.Request("POST", url))

            with mock.patch("httpx.post", side_effect=post):
                self.assertTrue(client.get("/api/speech").json()["available"])
                for suffix in (EVENT, "steps/0", "actions/0"):
                    for _ in range(2):
                        response = client.get(f"/api/runs/voice-test/speech/{suffix}")
                        self.assertEqual(response.status_code, 200)
                        self.assertEqual(response.content, b"ID3fish-audio")
                        self.assertEqual(response.headers["content-type"], "audio/mpeg")
            self.assertEqual([url for url, _ in requests], [speech.CHAT_URL, speech.FISH_URL] * 3)
            for transcript in (folder / "speech").glob("*/*.txt"):
                self.assertEqual(transcript.read_text(), LINE)

    def test_plain_mode_reaches_operator_writer_and_openai_delivery(self):
        with mock.patch.dict("os.environ", {"OPENAI_KEY": "test", "JESSE_PERSONA": "plain"}, clear=True):
            prompt = build_prompt(synthetic_context(), "web", "Compare coolant.")
            self.assertIn(PLAIN, prompt)
            self.assertNotIn(LAB_PARTNER, prompt)
            response = httpx.Response(200, json={"choices": [{"message": {"content": "Checking the setup."}}]},
                                      request=httpx.Request("POST", speech.CHAT_URL))
            with mock.patch("httpx.post", return_value=response) as post:
                text = speech._translate("Checking the setup.", "Compare coolant.")
                self.assertTrue(post.call_args.kwargs["json"]["messages"][0]["content"].startswith(PLAIN))
            with mock.patch("httpx.post", return_value=httpx.Response(200, content=b"mp3",
                            request=httpx.Request("POST", speech.SPEECH_URL))) as post:
                self.assertEqual(speech._synthesize(text), b"mp3")
                self.assertEqual(post.call_args.kwargs["json"]["input"], text)
                self.assertEqual(post.call_args.kwargs["json"]["instructions"], delivery_instructions())

    def test_cache_changes_with_personality_provider_voice_and_writer(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.dict("os.environ", {}, clear=True):
            folder = write_run(Path(directory))
            synthesize = mock.Mock(return_value=b"mp3")
            translate = lambda text, question: text
            paths = [speech.cached_speech(folder, EVENT, synthesize, translate)]
            for setting in ({"JESSE_PERSONA": "plain"}, {"FISH_API_KEY": "test"},
                            {"JESSE_FISH_VOICE": "other-voice"}, {"JESSE_FISH_MODEL": "s2-pro"},
                            {"JESSE_SPEECH_MODEL": "other-writer"}):
                os.environ.update(setting)
                paths.append(speech.cached_speech(folder, EVENT, synthesize, translate))
            self.assertEqual(len(set(paths)), len(paths))
            self.assertEqual(synthesize.call_count, len(paths))

    def test_fish_only_works_without_an_openai_writer(self):
        with mock.patch.dict("os.environ", {"FISH_API_KEY": "test"}, clear=True):
            self.assertTrue(speech.speech_available())
            with mock.patch("httpx.post") as post:
                self.assertEqual(speech._translate("Opening the lab.", "Compare coolant."), "Opening the lab.")
                post.assert_not_called()

    def test_fish_error_surfaces_as_502_without_caching_or_switching_voices(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.dict("os.environ", {
            "FISH_API_KEY": "test", "ELEVENLABS_API_KEY": "fallback", "OPENAI_KEY": "writer",
        }, clear=True):
            root = Path(directory)
            folder = write_run(root)
            client = TestClient(create_app(RunManager(root)))
            rejected = httpx.Response(401, request=httpx.Request("POST", speech.FISH_URL))
            with mock.patch.object(speech, "_translate", return_value=LINE), mock.patch("httpx.post", return_value=rejected) as post:
                response = client.get(f"/api/runs/voice-test/speech/{EVENT}")
                self.assertEqual(response.status_code, 502)
                self.assertEqual(post.call_count, 1)
                self.assertEqual(post.call_args.args[0], speech.FISH_URL)
            self.assertEqual(list(folder.glob("speech/**/*.mp3")), [])


if __name__ == "__main__":
    unittest.main()
