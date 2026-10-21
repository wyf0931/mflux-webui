import unittest
from unittest.mock import Mock, patch

from mflux_webui.mflux_service import MODEL_ID
from mflux_webui.model_downloader import ModelDownloadManager


class ModelDownloadManagerTest(unittest.TestCase):
    def setUp(self):
        self.manager = ModelDownloadManager()
        self.executor = Mock()
        self.manager._executor = self.executor
        # 下载前的空间检查依赖机器实际磁盘，测试统一模拟为充足空间。
        patcher = patch("mflux_webui.disk_space.free_bytes", return_value=1024**4)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_starts_curated_model_download(self):
        task = self.manager.start(MODEL_ID)
        self.assertEqual(task["status"], "queued")
        self.executor.submit.assert_called_once()

    def test_separates_modelscope_tasks_from_huggingface_tasks(self):
        task = self.manager.start("krea/Krea-2-Turbo", source="modelscope")
        self.assertEqual(task["source"], "modelscope")
        self.assertEqual(task["taskId"], "modelscope:krea/Krea-2-Turbo")

    def test_rejects_download_when_disk_is_full(self):
        with patch("mflux_webui.disk_space.free_bytes", return_value=1024**3), \
                self.assertRaisesRegex(Exception, "磁盘空间不足"):
            self.manager.start(MODEL_ID)

    def test_rejects_unrelated_or_unknown_model(self):
        with self.assertRaisesRegex(ValueError, "仅支持"):
            self.manager.start("mlx-community/Qwen3.8-27B-4bit")
