import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from mflux_webui.mflux_service import MODEL_ID, MfluxService


class MfluxServiceTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.service = MfluxService(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_loader_selects_turbo_config_and_preserves_existing_backends(self):
        config = MagicMock()
        krea, zimage, flux2, qwen, edit = (MagicMock() for _ in range(5))
        modules = {
            "mflux.models.common.config": MagicMock(ModelConfig=config),
            "mflux.models.krea2": MagicMock(Krea2=krea),
            "mflux.models.z_image": MagicMock(ZImageTurbo=zimage),
            "mflux.models.flux2": MagicMock(Flux2Klein=flux2),
            "mflux.models.qwen21.variants.txt2img.qwen_image_21": MagicMock(QwenImage21=qwen),
            "mflux.models.qwen21.variants.edit.qwen_image_21_edit": MagicMock(QwenImage21Edit=edit),
        }
        cases = [
            ("mflux-community/qwen-image-2-1-turbo-mflux-q4", qwen, "qwen_image_21_turbo"),
            ("mflux-community/krea-2-turbo-mflux-q4", krea, "krea2"),
            ("OsaurusAI/Z-Image-Turbo-mflux-4bit", zimage, None),
            ("Runpod/FLUX.2-klein-4B-mflux-4bit", flux2, "flux2_klein_4b"),
            ("mflux-community/flux2-klein-9b-mflux-q4", flux2, "flux2_klein_9b"),
        ]
        with patch.dict("sys.modules", modules), patch(
            "mflux_webui.mflux_service.resolve_krea_checkpoint", side_effect=lambda repo: repo,
        ):
            for repo_id, constructor, config_method in cases:
                with self.subTest(repo_id=repo_id):
                    service = MfluxService(self.temp_dir.name, repo_id)
                    self.assertIs(service.load_model(), constructor.return_value)
                    kwargs = {"model_path": repo_id}
                    if config_method:
                        kwargs["model_config"] = getattr(config, config_method).return_value
                    constructor.assert_called_with(**kwargs)
            reference = MfluxService(self.temp_dir.name, cases[0][0], "reference")
            self.assertIs(reference.load_model(), edit.return_value)
            edit.assert_called_once_with(model_path=cases[0][0], model_config=config.qwen_image_21_turbo.return_value)
        config.qwen_image_21.assert_not_called()

    @patch.object(MfluxService, "_load_model")
    def test_turbo_uses_eight_steps_and_linear_schedule(self, load_model):
        service = MfluxService(self.temp_dir.name, "mflux-community/qwen-image-2-1-turbo-mflux-q4")
        model = load_model.return_value
        model.generate_image.return_value.save.side_effect = lambda path: Path(path).touch()
        service.generate("海边的海鹦", 1024, 1024, seed=42)
        kwargs = model.generate_image.call_args.kwargs
        self.assertEqual(kwargs["num_inference_steps"], 8)
        self.assertEqual(kwargs["guidance"], 1.0)
        self.assertEqual(kwargs["scheduler"], "linear")

    @patch.object(MfluxService, "_load_model")
    def test_turbo_rejects_cfg_before_loading_weights(self, load_model):
        service = MfluxService(self.temp_dir.name, "mflux-community/qwen-image-2-1-turbo-mflux-q4")
        with self.assertRaisesRegex(ValueError, "引导系数必须为 1.0"):
            service.generate("海边的海鹦", 1024, 1024, guidance=3.5)
        load_model.assert_not_called()

    def test_advanced_options_reject_invalid_numbers_and_preserve_seed_zero(self):
        options = self.service.validate_options("8", "1", "0")
        self.assertEqual(options, {"steps": 8, "guidance": 1.0, "seed": 0})
        for params in ({"steps": "nan"}, {"steps": "8.5"}, {"steps": 0},
                       {"guidance": "inf"}, {"seed": -1}, {"seed": "1.5"},
                       {"seed": 4_294_967_296}):
            with self.subTest(params=params), self.assertRaises(ValueError):
                self.service.validate_options(**params)

    def test_reference_editing_translates_ordered_image_references(self):
        service = MfluxService(self.temp_dir.name, "mflux-community/qwen-image-2-1-turbo-mflux-q4", "reference")
        self.assertEqual(service.validate_references(2, "图一的人穿上图2的衣服，保留<image1>背景"),
                         "<image1>的人穿上<image2>的衣服，保留<image1>背景")
        for count, prompt in ((0, "编辑"), (11, "编辑"), (2, "图三"), (2, "<image0>")):
            with self.subTest(count=count, prompt=prompt), self.assertRaises(ValueError):
                service.validate_references(count, prompt)
        model = MagicMock()
        model.generate_image.return_value.save.side_effect = lambda path: Path(path).touch()
        references = [Path("one.png"), Path("two.png")]
        result = service.generate("图一参考图二", 768, 1024, input_images=references, model=model)
        arguments = model.generate_image.call_args.kwargs
        self.assertEqual(arguments["image_paths"], references)
        self.assertEqual(arguments["prompt"], "<image1>参考<image2>")
        self.assertNotIn("image_path", arguments)
        self.assertNotIn("image_strength", arguments)
        self.assertEqual(result.metadata["referenceCount"], 2)
        self.assertEqual(result.metadata["generationMode"], "reference")
        with self.assertRaisesRegex(ValueError, "至少需要 2"):
            service.validate_options(1)
        with self.assertRaisesRegex(ValueError, "32 的倍数"):
            service.validate_generation_dimensions(784, 1024)

    def test_other_models_cannot_use_reference_editing(self):
        self.service.generation_mode = "reference"
        with self.assertRaisesRegex(ValueError, "仅支持 Qwen"):
            self.service.validate_references(2, "图一和图二")

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
