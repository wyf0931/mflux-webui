import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import mflux_webui.api as api_module
from mflux_webui import create_app
from mflux_webui.mflux_service import MODEL_ID


class ApiTest(unittest.TestCase):
    def test_reference_upload_order_and_validation(self):
        manager = Mock()
        manager.submit.return_value = {"taskId": "multi", "status": "pending"}
        self.app.extensions["generation_task_manager"] = manager
        fields = {"prompt": "图一参考图二", "modelId": "mflux-community/qwen-image-2-1-turbo-mflux-q4",
                  "generationMode": "reference", "images": [
                      (io.BytesIO(b"one"), "one.png"), (io.BytesIO(b"two"), "two.png"),
                  ]}
        response = self.client.post("/api/generate", data=fields, content_type="multipart/form-data")
        self.assertEqual(response.status_code, 202)
        paths = manager.submit.call_args.kwargs["input_paths"]
        self.assertEqual([path.read_bytes() for path in paths], [b"one", b"two"])
        self.assertEqual(manager.submit.call_args.args[0]["generation_mode"], "reference")
        for path in paths:
            path.unlink()
        response = self.client.post("/api/generate", data={
            "prompt": "图三", "modelId": fields["modelId"], "generationMode": "reference",
            "images": [(io.BytesIO(b"one"), "one.png")],
        }, content_type="multipart/form-data")
        self.assertEqual(response.status_code, 400)
        self.assertIn("超出已上传", response.get_json()["message"])
        response = self.client.post("/api/generate", data={
            "prompt": "图一和图二", "modelId": fields["modelId"], "generationMode": "reference",
            "images": [(io.BytesIO(b"one"), "one.png"), (io.BytesIO(b"bad"), "two.gif")],
        }, content_type="multipart/form-data")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(list((self.images_dir.parent / "uploads").iterdir()), [])
        self.assertEqual(manager.submit.call_count, 1)

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.images_dir = Path(self.temp_dir.name) / "images"
        self.images_dir.mkdir()
        self.app = create_app()
        self.app.config.update(TESTING=True, IMAGES_DIR=str(self.images_dir))
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_image_to_image_upload_creates_async_task(self):
        captured = {}

        class Manager:
            def submit(self, params, input_path):
                captured["params"] = params
                captured["input_path"] = input_path
                return {"taskId": "task-1", "status": "pending", "position": 1, "ahead": 0, "queueLength": 1, "etaSeconds": 0}

        self.app.extensions["generation_task_manager"] = Manager()
        response = self.client.post("/api/generate", data={
            "prompt": "把衣服变为紫色", "width": "768", "height": "1376", "steps": "12",
            "seed": "42", "imageStrength": "0.35", "image": (io.BytesIO(b"fake image"), "reference.png"),
        }, content_type="multipart/form-data")

        payload = response.get_json()
        self.assertEqual(response.status_code, 202)
        self.assertEqual(payload["code"], 0)
        self.assertEqual(payload["message"], "任务已加入队列")
        self.assertEqual(payload["data"]["taskId"], "task-1")
        self.assertEqual(captured["params"]["image_strength"], 0.35)
        self.assertTrue(captured["input_path"].is_file())
        captured["input_path"].unlink()

    @patch.object(api_module, "get_cached_models", return_value={"models": [], "error": None})
    def test_model_cache_uses_standard_response(self, _cache):
        payload = self.client.get("/api/models/cache").get_json()
        self.assertEqual(payload, {"code": 0, "data": [], "message": "ok"})

    @patch.object(api_module, "get_cached_models", return_value={"models": [], "error": None})
    def test_model_catalog_uses_local_cache_only(self, cache):
        payload = self.client.get("/api/models/catalog").get_json()
        self.assertEqual(payload["code"], 0)
        cache.assert_called_once_with(include_hub_metadata=False)
        self.assertTrue(any(model["repoId"] == MODEL_ID for model in payload["data"]))

    @patch.object(api_module.download_manager, "start", return_value={"repoId": MODEL_ID, "status": "queued"})
    def test_download_uses_standard_response(self, _start):
        response = self.client.post("/api/models/downloads", json={"repoId": MODEL_ID})
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.get_json()["code"], 0)

    def test_invalid_image_strength_uses_standard_error(self):
        response = self.client.post("/api/generate", data={
            "prompt": "一只猫", "width": "768", "height": "1376", "imageStrength": "2",
            "image": (io.BytesIO(b"fake image"), "reference.png"),
        }, content_type="multipart/form-data")
        payload = response.get_json()
        self.assertEqual(response.status_code, 400)
        self.assertNotEqual(payload["code"], 0)
        self.assertIn("0 到 1", payload["message"])

    def test_unknown_api_uses_standard_error(self):
        response = self.client.get("/api/not-found")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json(), {"code": 2404, "data": None, "message": "接口不存在"})

    def test_invalid_turbo_options_are_rejected_before_enqueue_and_upload_is_cleaned(self):
        manager = Mock()
        self.app.extensions["generation_task_manager"] = manager
        response = self.client.post("/api/generate", data={
            "modelId": "mflux-community/qwen-image-2-1-turbo-mflux-q4",
            "prompt": "改成水彩画", "guidance": "3.5",
            "image": (io.BytesIO(b"clipboard bytes"), "clipboard.png"),
        }, content_type="multipart/form-data")
        self.assertEqual(response.status_code, 400)
        self.assertIn("引导系数必须为 1.0", response.get_json()["message"])
        manager.submit.assert_not_called()
        self.assertEqual(list((self.images_dir.parent / "uploads").iterdir()), [])

    @patch.object(api_module, "get_cached_models", return_value={"models": [], "error": None})
    def test_catalog_declares_model_specific_advanced_options(self, _cache):
        models = self.client.get("/api/models/catalog").get_json()["data"]
        qwen = next(model for model in models if model["family"] == "Qwen Image 2.1 Turbo")
        self.assertEqual(qwen["steps"], 8)
        self.assertEqual(qwen["guidance"], 1.0)
        self.assertEqual(qwen["guidanceMode"], "fixed")
        self.assertEqual(next(model for model in models if model["family"] == "Z-Image Turbo")["guidanceMode"], "ignored")

    def test_formatters(self):
        self.assertEqual(self.app.jinja_env.filters["timestamp"]("2026-03-30-16-24-59"), "2026-03-30 16:24:59")
        self.assertEqual(self.app.jinja_env.filters["duration"](212.4), "3分32.4秒")

    def test_gallery_exposes_reuse_generation_action(self):
        response = self.client.get("/gallery")
        self.assertEqual(response.status_code, 200)
        self.assertIn("使用此参数重新生成".encode(), response.data)

    def test_models_page_exposes_initial_scan_loading_state(self):
        response = self.client.get("/models")
        self.assertEqual(response.status_code, 200)
        self.assertIn("正在识别本地模型".encode(), response.data)

    def test_queue_page_and_task_api_are_available(self):
        class Manager:
            def get_task(self, task_id):
                return {"taskId": task_id, "status": "pending"}

            def list_tasks(self):
                return {"tasks": [], "queueLength": 0, "runningTaskId": None}

        self.app.extensions["generation_task_manager"] = Manager()
        self.assertEqual(self.client.get("/queue").status_code, 200)
        self.assertEqual(self.client.get("/api/generate/tasks").get_json()["data"]["queueLength"], 0)
        self.assertEqual(self.client.get("/api/generate/tasks/task-1").get_json()["data"]["taskId"], "task-1")
