import unittest
from unittest.mock import Mock

from mflux_webui.mflux_service import MODEL_ID
from mflux_webui.model_downloader import ModelDownloadManager


class ModelDownloadManagerTest(unittest.TestCase):
    def setUp(self):
        self.manager = ModelDownloadManager()
        self.manager._executor = Mock()

    def tearDown(self):
        self.manager._executor.shutdown(wait=False) if hasattr(self.manager._executor, "shutdown") else None

    def test_starts_curated_model_download(self):
        task = self.manager.start(MODEL_ID)
        self.assertEqual(task["status"], "queued")
        self.manager._executor.submit.assert_called_once()

    def test_separates_modelscope_tasks_from_huggingface_tasks(self):
        task = self.manager.start("krea/Krea-2-Turbo", source="modelscope")
        self.assertEqual(task["source"], "modelscope")
        self.assertEqual(task["taskId"], "modelscope:krea/Krea-2-Turbo")

    def test_rejects_unrelated_or_unknown_model(self):
        with self.assertRaisesRegex(ValueError, "仅支持"):
            self.manager.start("mlx-community/Qwen3.8-27B-4bit")
