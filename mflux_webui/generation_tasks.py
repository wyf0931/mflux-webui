"""单进程图片生成队列与模型空闲缓存。"""

import gc
import logging
import os
import queue
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from .db import (
    add_history_entry,
    create_generation_task,
    delete_incomplete_generation_tasks,
    get_generation_task,
    get_generation_tasks,
    trim_terminal_generation_tasks,
    update_generation_task,
)
from .mflux_service import MfluxService
from .model_registry import get_model_spec

DEFAULT_MODEL_IDLE_TTL_SECONDS = 300
DEFAULT_QUEUE_MAX_SIZE = 10
TERMINAL_STATUSES = {"succeeded", "failed", "cancelled"}


def _positive_int_from_env(name, default):
    try:
        value = int(os.getenv(name, str(default)).strip())
    except (AttributeError, ValueError):
        return default
    return value if value > 0 else default


class ModelCache:
    """在单 worker 内复用已加载模型，并在空闲后释放强引用。"""

    def __init__(self, idle_ttl_seconds=DEFAULT_MODEL_IDLE_TTL_SECONDS, clock=time.monotonic):
        self.idle_ttl_seconds = idle_ttl_seconds
        self._clock = clock
        self._models = {}

    def get(self, service):
        key = getattr(service, "cache_key", service.model_id)
        # 同一仓库的文本/视觉编辑实例不能混用，也不同时保留两套权重。
        other = service.model_id if key != service.model_id else service.model_id + "::reference"
        if other in self._models:
            del self._models[other]
            gc.collect()
        cached = self._models.get(key)
        if cached is None:
            cached = {"model": service.load_model(), "last_used": self._clock()}
            self._models[key] = cached
        return cached["model"]

    def mark_used(self, model_id):
        cached = self._models.get(model_id)
        if cached is not None:
            cached["last_used"] = self._clock()

    def unload_expired(self):
        now = self._clock()
        expired = [
            model_id for model_id, cached in self._models.items()
            if now - cached["last_used"] >= self.idle_ttl_seconds
        ]
        for model_id in expired:
            del self._models[model_id]
        if expired:
            gc.collect()
        return expired

    def clear(self):
        self._models.clear()
        gc.collect()


class QueueFullError(RuntimeError):
    pass


class GenerationTaskManager:
    """将 Web 请求转为 FIFO 任务，并由单线程独占 GPU 推理。"""

    def __init__(self, images_dir, *, queue_max_size=None, model_idle_ttl_seconds=None,
                 service_factory=MfluxService, start_worker=True, logger=None):
        self.images_dir = Path(images_dir)
        self.queue_max_size = queue_max_size or _positive_int_from_env(
            "MFLUX_QUEUE_MAX_SIZE", DEFAULT_QUEUE_MAX_SIZE
        )
        ttl = model_idle_ttl_seconds or _positive_int_from_env(
            "MFLUX_MODEL_IDLE_TTL_SECONDS", DEFAULT_MODEL_IDLE_TTL_SECONDS
        )
        self.model_cache = ModelCache(ttl)
        self._service_factory = service_factory
        self._queue = queue.Queue()
        self._submit_lock = threading.Lock()
        self._logger = logger or logging.getLogger(__name__)
        delete_incomplete_generation_tasks()
        self._worker = None
        if start_worker:
            self._worker = threading.Thread(target=self._work, name="mflux-generation-worker", daemon=True)
            self._worker.start()

    @staticmethod
    def _now():
        return datetime.now().astimezone().isoformat(timespec="microseconds")

    def submit(self, params, input_path=None, input_paths=None):
        with self._submit_lock:
            pending = self._pending_tasks()
            if len(pending) >= self.queue_max_size:
                raise QueueFullError("生成队列已满，请稍后重试")

            task_id = str(uuid4())
            task = {
                "task_id": task_id,
                "status": "pending",
                "created_at": self._now(),
                "started_at": None,
                "finished_at": None,
                "error": None,
                "logs": None,
                "filename": None,
                "timestamp": None,
                "duration": None,
                "metadata": None,
                "input_path": str(input_path) if input_path else None,
                "input_paths": [str(path) for path in input_paths or []],
                "params": params,
            }
            create_generation_task(task)
            self._queue.put(task_id)
            position = len(pending) + 1
            return {
                "taskId": task_id,
                "status": "pending",
                "position": position,
                "ahead": position - 1,
                "queueLength": position,
                "etaSeconds": self._estimate_eta(position - 1),
            }

    def get_task(self, task_id):
        task = get_generation_task(task_id)
        return self._serialize_task(task, include_logs=True) if task else None

    def list_tasks(self):
        tasks = [self._serialize_task(task) for task in get_generation_tasks()]
        return {
            "tasks": tasks,
            "queueLength": len(self._pending_tasks()),
            "runningTaskId": next((task["taskId"] for task in tasks if task["status"] == "running"), None),
        }

    def _pending_tasks(self):
        return sorted(
            (task for task in get_generation_tasks() if task["status"] == "pending"),
            key=lambda task: (task["created_at"], task["task_id"]),
        )

    def _estimate_eta(self, ahead):
        if ahead <= 0:
            return 0
        durations = [
            task["duration"] for task in get_generation_tasks()
            if task["status"] == "succeeded" and isinstance(task.get("duration"), (int, float))
        ][:5]
        if not durations:
            return None
        return round(sum(durations) / len(durations) * ahead)

    def _serialize_task(self, task, include_logs=False):
        spec = get_model_spec(task["params"]["model_id"])
        result = {
            "taskId": task["task_id"],
            "status": task["status"],
            "createdAt": task["created_at"],
            "startedAt": task.get("started_at"),
            "finishedAt": task.get("finished_at"),
            "prompt": task["params"]["prompt"],
            "modelId": task["params"]["model_id"],
            "modelName": spec.name if spec else task["params"]["model_id"],
            "width": task["params"]["width"],
            "height": task["params"]["height"],
            "steps": task["params"].get("steps"),
            "generationMode": task["params"].get("generation_mode", "img2img"),
            "referenceCount": len(task.get("input_paths") or []) or int(bool(task.get("input_path"))),
            "duration": task.get("duration"),
            "filename": task.get("filename"),
            "timestamp": task.get("timestamp"),
            "metadata": task.get("metadata"),
            "error": task.get("error"),
        }
        if include_logs:
            result["logs"] = task.get("logs") or task.get("error")
        if task["status"] == "pending":
            pending = self._pending_tasks()
            position = next((index + 1 for index, item in enumerate(pending) if item["task_id"] == task["task_id"]), None)
            result.update({
                "position": position,
                "ahead": position - 1 if position else 0,
                "queueLength": len(pending),
                "etaSeconds": self._estimate_eta(position - 1) if position else None,
            })
        return result

    def _work(self):
        while True:
            try:
                task_id = self._queue.get(timeout=1)
            except queue.Empty:
                self.model_cache.unload_expired()
                continue

            try:
                self._run_task(task_id)
            except Exception:
                self._logger.exception("生成任务 worker 发生未处理异常：%s", task_id)
            finally:
                self._queue.task_done()
                self.model_cache.unload_expired()

    def _run_task(self, task_id):
        task = get_generation_task(task_id)
        if not task or task.get("status") != "pending":
            return
        task = dict(task)

        update_generation_task(task_id, {"status": "running", "started_at": self._now()})
        input_path = Path(task["input_path"]) if task.get("input_path") else None
        input_paths = [Path(path) for path in task.get("input_paths", [])]
        params = dict(task["params"])
        try:
            service = self._service_factory(self.images_dir, model_id=params["model_id"])
            service.generation_mode = params.get("generation_mode", "img2img")
            model = self.model_cache.get(service)
            reference_options = {"input_images": input_paths} if service.generation_mode == "reference" else {}
            result = service.generate(
                prompt=params["prompt"], width=params["width"], height=params["height"],
                seed=params.get("seed"), steps=params.get("steps"), guidance=params.get("guidance"),
                input_image=input_path, image_strength=params.get("image_strength"), model=model,
                **reference_options,
            )
            self.model_cache.mark_used(getattr(service, "cache_key", service.model_id))
            timestamp = result.filename.removesuffix(".png")
            add_history_entry({
                "timestamp": timestamp, "model": result.model, "width": result.width,
                "height": result.height, "prompt": result.prompt, "image_path": result.image_path,
                "duration": result.duration, "metadata": result.metadata,
            })
            update_generation_task(task_id, {
                "status": "succeeded", "finished_at": self._now(), "filename": result.filename,
                "timestamp": timestamp, "duration": result.duration, "metadata": result.metadata,
            })
        except Exception as exc:
            task_logs = (
                f"任务 ID：{task_id}\n模型：{params['model_id']}\n\n{traceback.format_exc()}"
            )
            self._logger.exception("图片生成任务失败：%s", task_id)
            update_generation_task(task_id, {
                "status": "failed", "finished_at": self._now(), "error": f"生成失败：{exc}",
                "logs": task_logs,
            })
        finally:
            for path in [*input_paths, *([input_path] if input_path else [])]:
                path.unlink(missing_ok=True)
            trim_terminal_generation_tasks()
