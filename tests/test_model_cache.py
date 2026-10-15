import unittest
from pathlib import Path
from unittest.mock import patch

from huggingface_hub.errors import CacheNotFound

from mflux_webui.model_cache import (
    get_cached_models,
    get_model_family,
    is_mflux_image_model,
)


class ModelCacheTest(unittest.TestCase):
    @patch.dict("os.environ", {"MODEL_REPO": "huggingface"})
    @patch("mflux_webui.model_cache.scan_cache_dir", side_effect=CacheNotFound("尚未下载模型", Path("/missing-cache")))
    def test_first_launch_without_cache_returns_empty_models(self, _scan):
        self.assertEqual(get_cached_models(), {"models": [], "error": None})

    def test_recognizes_only_explicit_mflux_image_model_families(self):
        self.assertTrue(is_mflux_image_model("mflux-community/krea-2-turbo-mflux-q4"))
        self.assertTrue(is_mflux_image_model("filipstrand/Z-Image-Turbo-mflux-4bit"))
        self.assertTrue(is_mflux_image_model("mlx-community/FLUX.2-klein-9b-4bit"))
        self.assertTrue(is_mflux_image_model("Qwen/Qwen-Image-2512"))
        self.assertFalse(is_mflux_image_model("mlx-community/Qwen3.8-27B-4bit"))
        self.assertFalse(is_mflux_image_model("meta-llama/Llama-3.3-70B-Instruct"))

    def test_returns_human_readable_model_family(self):
        self.assertEqual(get_model_family("mflux-community/krea-2-turbo-mflux-q4"), "Krea 2 Turbo")
        self.assertEqual(get_model_family("filipstrand/Z-Image-Turbo-mflux-4bit"), "Z-Image")
        self.assertEqual(get_model_family("mlx-community/FLUX.2-klein-9b-4bit"), "FLUX.2")

    @patch("mflux_webui.model_cache.scan_cache_dir", side_effect=OSError("缓存不可读"))
    def test_returns_error_when_cache_cannot_be_read(self, _scan):
        result = get_cached_models()
        self.assertEqual(result["models"], [])
        self.assertIn("缓存不可读", result["error"])
