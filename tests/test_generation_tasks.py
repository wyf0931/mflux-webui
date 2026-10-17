import tempfile
import unittest
from pathlib import Path
from typing import ClassVar
from unittest.mock import patch

import mflux_webui.db as db_module
from mflux_webui.generation_tasks import (
    GenerationTaskManager,
    ModelCache,
    QueueFullError,
)
from mflux_webui.mflux_service import GenerationResult, MfluxService


class FakeService:
    loaded_models: ClassVar[list] = []
    generated_prompts: ClassVar[list] = []

    def __init__(self, images_dir, model_id):
        self.images_dir = Path(images_dir)
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.model_id = model_id

    def _load_model(self):
        model = object()
        self.loaded_models.append(model)
        return model

    def load_model(self):
        return self._load_model()

    def generate(self, prompt, width, height, model=None, **_kwargs):
        if prompt == "broken":
            raise RuntimeError("推理失败")
        self.generated_prompts.append((prompt, model))
        output_path = self.images_dir / f"{prompt}.png"
        output_path.touch()
        return GenerationResult(
            image_path=str(output_path), filename=output_path.name, duration=2.0,
            model=self.model_id, width=width, height=height, prompt=prompt,
        )


class GenerationTaskManagerTest(unittest.TestCase):
    def test_qwen_text_and_edit_modes_do_not_share_model_instances(self):
        cache = ModelCache()
        plain = MfluxService(self.temp_dir.name, "mflux-community/qwen-image-2-1-turbo-mflux-q4")
        edit = MfluxService(self.temp_dir.name, plain.model_id, "reference")
        one, two, three = object(), object(), object()
        with patch.object(MfluxService, "load_model", side_effect=[one, two, three]) as loader:
            self.assertIs(cache.get(plain), one)
            self.assertIs(cache.get(plain), one)
            self.assertIs(cache.get(edit), two)
            self.assertNotIn(plain.cache_key, cache._models)
            self.assertIs(cache.get(plain), three)
            self.assertNotIn(edit.cache_key, cache._models)
            self.assertEqual(loader.call_count, 3)

    def test_reference_files_are_removed_after_success_and_failure(self):
        for prompt in ("multi", "broken"):
            paths = [Path(self.temp_dir.name) / f"{prompt}-{i}.png" for i in range(2)]
            for path in paths:
                path.touch()
            params = {**self.params(prompt), "generation_mode": "reference"}
            task = self.manager.submit(params, input_paths=paths)
            self.manager._run_task(task["taskId"])
            self.assertTrue(all(not path.exists() for path in paths))
            result = self.manager.get_task(task["taskId"])
            self.assertEqual(result["status"], "failed" if prompt == "broken" else "succeeded")

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_file = Path(self.temp_dir.name) / "db.json"
        self.db_patch = patch.object(db_module, "DB_FILE", self.db_file)
        self.db_patch.start()
        db_module._ensure_db_file()
        FakeService.loaded_models = []
        FakeService.generated_prompts = []
        self.manager = GenerationTaskManager(
            Path(self.temp_dir.name) / "images", queue_max_size=2, model_idle_ttl_seconds=1,
            service_factory=FakeService, start_worker=False,
        )

    def tearDown(self):
        self.db_patch.stop()
        self.temp_dir.cleanup()

    @staticmethod
    def params(prompt):
        return {"model_id": "model-a", "prompt": prompt, "width": 768, "height": 1024, "steps": 8,
                "seed": None, "guidance": None, "image_strength": None}

    def test_tasks_run_fifo_and_reuse_loaded_model(self):
        first = self.manager.submit(self.params("first"))
        second = self.manager.submit(self.params("second"))

        self.manager._run_task(first["taskId"])
        self.manager._run_task(second["taskId"])

        self.assertEqual([prompt for prompt, _model in FakeService.generated_prompts], ["first", "second"])
        self.assertEqual(len(FakeService.loaded_models), 1)
        self.assertEqual(self.manager.get_task(second["taskId"])["status"], "succeeded")

    def test_queue_limit_and_pending_position(self):
        first = self.manager.submit(self.params("first"))
        second = self.manager.submit(self.params("second"))

        self.assertEqual(first["position"], 1)
        self.assertEqual(second["ahead"], 1)
        with self.assertRaises(QueueFullError):
            self.manager.submit(self.params("third"))

    def test_expired_model_is_unloaded_and_loaded_again(self):
        task = self.manager.submit(self.params("first"))
        self.manager._run_task(task["taskId"])

        self.manager.model_cache._models["model-a"]["last_used"] = 0
        with patch.object(self.manager.model_cache, "_clock", return_value=2):
            self.manager.model_cache.unload_expired()
        next_task = self.manager.submit(self.params("second"))
        self.manager._run_task(next_task["taskId"])

        self.assertEqual(len(FakeService.loaded_models), 2)

    def test_worker_consumes_queue_and_continues_after_failure(self):
        manager = GenerationTaskManager(
            Path(self.temp_dir.name) / "worker-images", queue_max_size=2,
            service_factory=FakeService, start_worker=True,
        )
        broken = manager.submit(self.params("broken"))
        successful = manager.submit(self.params("successful"))

        manager._queue.join()

        self.assertEqual(manager.get_task(broken["taskId"])["status"], "failed")
        self.assertEqual(manager.get_task(successful["taskId"])["status"], "succeeded")
        logs = manager.get_task(broken["taskId"])["logs"]
        self.assertIn("Traceback", logs)
        self.assertIn("推理失败", logs)
        self.assertIn(broken["taskId"], logs)
        self.assertTrue(all("logs" not in task for task in manager.list_tasks()["tasks"]))

    def test_task_alias_matches_model_catalog_and_old_errors_remain_available(self):
        params = self.params("alias")
        params["model_id"] = "mflux-community/qwen-image-2-1-turbo-mflux-q4"
        task = self.manager.submit(params)
        detail = self.manager.get_task(task["taskId"])
        self.assertEqual(detail["modelName"], "Qwen Image 2.1 Turbo · q4")
        db_module.update_generation_task(task["taskId"], {"status": "failed", "error": "历史完整错误", "logs": None})
        self.assertEqual(self.manager.get_task(task["taskId"])["logs"], "历史完整错误")
