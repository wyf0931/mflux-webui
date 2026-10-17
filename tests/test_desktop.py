"""桌面后端的会话隔离和独立数据目录回归。"""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from flask import Flask

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("desktop_backend", ROOT / "desktop/backend.py")
backend = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backend)


class DesktopSessionTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.app = Flask(__name__)
        self.app.add_url_rule("/", endpoint="index", view_func=lambda: "桌面首页")
        self.app.add_url_rule("/api/test", endpoint="test", view_func=lambda: "ok", methods=["POST"])
        self.token = "a" * 64
        backend.protect_desktop_app(self.app, self.token, 54321, self.temporary.name)
        self.client = self.app.test_client()
        self.origin = "http://127.0.0.1:54321"

    def bootstrap(self):
        return self.client.get(f"/desktop/bootstrap?token={self.token}", base_url=self.origin)

    def test_requires_session_and_hides_token_in_http_only_cookie(self):
        self.assertEqual(self.client.get("/", base_url=self.origin).status_code, 403)
        response = self.bootstrap()
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'location.replace("/")', response.data)
        self.assertIn("HttpOnly", response.headers["Set-Cookie"])
        self.assertIn("SameSite=Strict", response.headers["Set-Cookie"])
        self.assertEqual(self.client.get("/", base_url=self.origin).status_code, 200)
        self.assertEqual(self.bootstrap().status_code, 403)

    def test_rejects_wrong_token_host_and_cross_origin_mutations(self):
        self.assertEqual(self.client.get("/desktop/bootstrap?token=bad", base_url=self.origin).status_code, 403)
        self.bootstrap()
        self.assertEqual(self.client.get("/", base_url="http://evil.example:54321").status_code, 403)
        self.assertEqual(self.client.post("/api/test", base_url=self.origin,
                                         headers={"Origin": "https://evil.example"}).status_code, 403)
        self.assertEqual(self.client.post("/api/test", base_url=self.origin,
                                         headers={"Origin": self.origin}).status_code, 200)

    def test_separate_data_directory_preserves_packaged_resources(self):
        with tempfile.TemporaryDirectory() as data_dir:
            result = subprocess.run([
                sys.executable, "-c",
                ("import json; from mflux_webui import app; "
                "from mflux_webui.db import DB_FILE; "
                "from mflux_webui.model_registry import MODEL_CONFIG_PATH; "
                "print(json.dumps([str(DB_FILE), app.config['IMAGES_DIR'], str(MODEL_CONFIG_PATH)]))"),
            ], cwd=ROOT, env={**os.environ, "MFLUX_DATA_DIR": data_dir},
                capture_output=True, text=True, check=True)
            database, images, models = json.loads(result.stdout)
            self.assertEqual(Path(database), Path(data_dir).resolve() / "db.json")
            self.assertEqual(Path(images), Path(data_dir).resolve() / "images")
            self.assertEqual(Path(models), ROOT / "config/models.json")

    def test_theme_survives_backend_restart_and_rejects_invalid_values(self):
        self.bootstrap()
        response = self.client.post("/desktop/theme", base_url=self.origin,
                                    json={"theme": "rausch-dark"}, headers={"Origin": self.origin})
        self.assertEqual(response.status_code, 200)
        restarted = Flask("restarted")
        backend.protect_desktop_app(restarted, self.token, 54321, self.temporary.name)
        self.assertEqual(restarted.config["DESKTOP_THEME"], "rausch-dark")
        self.assertEqual(self.client.post("/desktop/theme", base_url=self.origin,
                                         json={"theme": []}).status_code, 400)
