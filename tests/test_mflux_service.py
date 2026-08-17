import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mflux_service import MODEL_ID, MfluxService


class MfluxServiceTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.service = MfluxService(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch.object(MfluxService, "_load_model")
    def test_text_to_image_uses_krea_python_api(self, load_model):
        model = load_model.return_value
        model.generate_image.return_value.save.side_effect = lambda path: Path(path).touch()

        result = self.service.generate("一只猫", 768, 1376, steps=8, seed=42)

        model.generate_image.assert_called_once_with(
            seed=42, prompt="一只猫", num_inference_steps=8, height=1376, width=768,
            guidance=1.0, image_path=None, image_strength=None, scheduler="er_sde",
        )
        self.assertEqual(result.model, MODEL_ID)
        self.assertTrue(Path(result.image_path).is_file())

    @patch.object(MfluxService, "_load_model")
    def test_image_to_image_uses_reference_image(self, load_model):
        reference = Path(self.temp_dir.name) / "input.png"
        reference.touch()
        model = load_model.return_value
        model.generate_image.return_value.save.side_effect = lambda path: Path(path).touch()

        self.service.generate("换成紫色上衣", 768, 1376, input_image=reference, image_strength=0.35)

        kwargs = model.generate_image.call_args.kwargs
        self.assertEqual(kwargs["image_path"], reference)
        self.assertEqual(kwargs["image_strength"], 0.35)

    @patch.object(MfluxService, "_load_model", side_effect=RuntimeError("模型载入失败"))
    def test_api_failure_exposes_diagnostic(self, _load_model):
        with self.assertRaisesRegex(RuntimeError, "模型载入失败"):
            self.service.generate("一只猫", 768, 1376)

    def test_invalid_image_strength_is_rejected(self):
        reference = Path(self.temp_dir.name) / "input.png"
        reference.touch()
        with self.assertRaisesRegex(ValueError, "0 到 1"):
            self.service.generate("一只猫", 768, 1376, input_image=reference, image_strength=1.1)

    @patch.object(MfluxService, "_load_model")
    def test_empty_advanced_fields_use_official_defaults(self, load_model):
        model = load_model.return_value
        model.generate_image.return_value.save.side_effect = lambda path: Path(path).touch()

        self.service.generate("一只猫", 768, 1376, guidance="", seed="", image_strength="")

        kwargs = model.generate_image.call_args.kwargs
        self.assertEqual(kwargs["guidance"], 1.0)
        self.assertEqual(kwargs["scheduler"], "er_sde")
        self.assertIsNone(kwargs["image_path"])
