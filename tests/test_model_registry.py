import os
import unittest
from unittest.mock import patch

from mflux_webui.model_registry import catalog_models, configured_sources


class ModelRegistryTest(unittest.TestCase):
    def test_default_exposes_both_model_repositories(self):
        with patch.dict(os.environ, {}, clear=True):
            models = catalog_models()
            self.assertEqual(configured_sources(), ("huggingface", "modelscope"))
        self.assertEqual({model["source"] for model in models}, {"huggingface", "modelscope"})
        self.assertTrue(all(model["repoUrl"].startswith("https://") for model in models))

    def test_repository_switch_filters_catalog(self):
        with patch.dict(os.environ, {"MODEL_REPO": "modelscope"}):
            models = catalog_models()
            self.assertEqual(configured_sources(), ("modelscope",))
        self.assertEqual(len(models), 5)
        self.assertTrue(all(model["source"] == "modelscope" for model in models))

    def test_invalid_repository_value_falls_back_to_all(self):
        with patch.dict(os.environ, {"MODEL_REPO": "invalid"}):
            self.assertEqual(configured_sources(), ("huggingface", "modelscope"))
