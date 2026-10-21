import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mflux_webui.disk_space import (
    GENERATION_MIN_FREE_BYTES,
    GIB,
    InsufficientSpaceError,
    check_download_space,
    check_generation_space,
    format_size,
    free_bytes,
)


class DiskSpaceTest(unittest.TestCase):
    def test_generation_allows_enough_space(self):
        with patch("mflux_webui.disk_space.free_bytes", return_value=10 * GIB):
            self.assertEqual(check_generation_space("/tmp"), 10 * GIB)

    def test_generation_rejects_low_space(self):
        with patch("mflux_webui.disk_space.free_bytes", return_value=GIB // 2), \
                self.assertRaises(InsufficientSpaceError) as context:
            check_generation_space("/tmp")
        message = str(context.exception)
        self.assertIn("磁盘空间不足", message)
        self.assertIn("生成图片", message)
        self.assertIn(format_size(GENERATION_MIN_FREE_BYTES), message)
        self.assertEqual(context.exception.available_bytes, GIB // 2)

    def test_download_requires_model_size_plus_margin(self):
        required = 10 * GIB
        with patch("mflux_webui.disk_space.free_bytes", return_value=11 * GIB), \
                self.assertRaises(InsufficientSpaceError) as context:
            check_download_space("/tmp", required)
        self.assertEqual(context.exception.required_bytes, required + 2 * GIB)
        self.assertIn("下载模型", str(context.exception))

    def test_download_allows_space_above_budget(self):
        with patch("mflux_webui.disk_space.free_bytes", return_value=30 * GIB):
            self.assertEqual(check_download_space("/tmp", 10 * GIB), 30 * GIB)

    def test_free_bytes_reads_real_volume(self):
        with tempfile.TemporaryDirectory() as temporary:
            self.assertGreater(free_bytes(temporary), 0)
            # 不存在的路径应回退到最近的已存在父目录，而不是抛异常。
            self.assertGreater(free_bytes(Path(temporary) / "missing" / "deeper"), 0)

    def test_free_bytes_returns_zero_when_volume_unreadable(self):
        with patch("mflux_webui.disk_space.shutil.disk_usage", side_effect=OSError("boom")):
            self.assertEqual(free_bytes(Path("/tmp")), 0)

    def test_format_size(self):
        self.assertEqual(format_size(2 * GIB), "2.0 GB")
        self.assertEqual(format_size(512 * 1024**2), "512 MB")


if __name__ == "__main__":
    unittest.main()
