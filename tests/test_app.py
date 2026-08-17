import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app as app_module
from mflux_service import GenerationResult, MODEL_ID


class AppTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.images_dir = Path(self.temp_dir.name) / "images"
        self.images_dir.mkdir()
        app_module.app.config["TESTING"] = True

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_image_to_image_upload_is_forwarded_and_removed(self):
        captured = {}
        test_case = self

        class Service:
            def generate(self, **kwargs):
                captured.update(kwargs)
                self_path = Path(kwargs["input_image"])
                test_case.assertTrue(self_path.is_file())
                return GenerationResult(
                    image_path=str(self_path), filename="result.png", duration=1.0,
                    model=MODEL_ID, width=768, height=1376, prompt=kwargs["prompt"],
                )

        with patch.object(app_module, "IMAGES_DIR", self.images_dir), \
             patch.object(app_module, "_mflux_service", return_value=Service()), \
             patch.object(app_module, "add_history_entry"):
            response = app_module.app.test_client().post(
                "/api/generate",
                data={
                    "prompt": "把衣服变为紫色", "width": "768", "height": "1376",
                    "steps": "12", "seed": "42", "imageStrength": "0.35",
                    "image": (io.BytesIO(b"fake image"), "reference.png"),
                },
                content_type="multipart/form-data",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(captured["image_strength"], "0.35")
        self.assertEqual(list((self.images_dir.parent / "uploads").glob("*")), [])

    @patch.object(app_module, "get_cached_models", return_value={"models": [], "error": None})
    def test_model_cache_api_is_available(self, _cache):
        response = app_module.app.test_client().get("/api/models/cache")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["models"], [])

    def test_invalid_image_strength_returns_bad_request(self):
        response = app_module.app.test_client().post(
            "/api/generate",
            data={
                "prompt": "一只猫", "width": "768", "height": "1376", "imageStrength": "2",
                "image": (io.BytesIO(b"fake image"), "reference.png"),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("0 到 1", response.get_json()["error"])
