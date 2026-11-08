"""The reverse proxy keeps CSRF protection valid on the configured HTTPS origin."""
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from jesse.conversation.application import RunManager
from jesse.conversation.web import create_app


class DeploymentHttpTests(unittest.TestCase):
    def test_public_host_requires_explicit_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            client = TestClient(create_app(RunManager(Path(directory))), base_url="http://unapproved.example")
            self.assertEqual(client.get("/").status_code, 403)

    def test_proxy_origin_allows_same_origin_writes_and_rejects_forged_requests(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict("os.environ", {
            "JESSE_ALLOWED_HOSTS": "jesse.adrienpelfresne.com",
            "JESSE_PUBLIC_URL": "https://jesse.adrienpelfresne.com",
        }):
            manager = RunManager(Path(directory))
            manager.start = lambda question: "synthetic-deployment-run"
            client = TestClient(create_app(manager), base_url="http://jesse.adrienpelfresne.com")
            token = re.search(r'name="jesse-token" content="([^"]+)"', client.get("/").text).group(1)
            headers = {"x-jesse-token": token, "origin": "https://jesse.adrienpelfresne.com"}
            self.assertEqual(client.post("/api/runs", headers=headers, json={"text": "Synthetic question"}).status_code, 202)
            self.assertEqual(client.post("/api/runs", headers={"origin": headers["origin"]}, json={"text": "Q"}).status_code, 403)
            self.assertEqual(client.post("/api/runs", headers={**headers, "origin": "https://unapproved.example"}, json={"text": "Q"}).status_code, 403)
            self.assertEqual(client.get("/healthz").json(), {"status": "ok"})


if __name__ == "__main__":
    unittest.main()
