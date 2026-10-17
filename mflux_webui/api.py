"""前后端分离的 JSON API。所有响应遵循 code/data/message 协议。"""

from pathlib import Path
from uuid import uuid4

from flask import Blueprint, current_app, jsonify, request
from werkzeug.utils import secure_filename

from .db import (
    clean_history,
    delete_history,
    get_all_history,
    get_history_by_timestamp,
)
from .generation_tasks import QueueFullError
from .mflux_service import MODEL_ID, MfluxService
from .model_cache import get_cached_models
from .model_downloader import download_manager
from .model_registry import catalog_models, configured_sources, get_model_spec

api = Blueprint("api", __name__, url_prefix="/api")


def success(data=None, message="ok", status=200):
    """返回成功响应。data 可为对象、数组或 None。"""
    return jsonify({"code": 0, "data": data, "message": message}), status


def failure(message, code=1, status=400, data=None):
    """返回失败响应；HTTP 状态表达传输错误，code 表达业务错误。"""
    return jsonify({"code": code, "data": data, "message": message}), status


def _images_dir():
    return Path(current_app.config["IMAGES_DIR"])


def _task_manager():
    return current_app.extensions["generation_task_manager"]


@api.get("/models/cache")
def model_cache():
    cached = get_cached_models()
    if cached["error"]:
        return failure(cached["error"], code=2101, status=503, data=[])
    return success(cached["models"])


@api.get("/models/catalog")
def model_catalog():
    cached = get_cached_models(include_hub_metadata=False)
    if cached["error"]:
        return failure(cached["error"], code=2101, status=503, data=[])
    return success(catalog_models(cached["models"], sources=configured_sources()))


@api.get("/models/downloads")
def model_downloads():
    return success(download_manager.list_tasks())


@api.post("/models/downloads")
def start_model_download():
    data = request.get_json(silent=True) or {}
    repo_id = data.get("repoId", "")
    source = data.get("source", "huggingface")
    try:
        return success(download_manager.start(repo_id, source=source), message="下载任务已创建", status=202)
    except ValueError as exc:
        return failure(str(exc), code=2201)


@api.delete("/models/downloads")
def cancel_model_download():
    data = request.get_json(silent=True) or {}
    repo_id = data.get("repoId", "")
    source = data.get("source", "huggingface")
    try:
        download_manager.cancel(repo_id, source=source)
        return success(message="取消请求已提交")
    except ValueError as exc:
        return failure(str(exc), code=2202)


@api.post("/generate")
def generate_image():
    data = (request.get_json(silent=True) or {}) if request.is_json else request.form
    prompt = data.get("prompt")
    model_id = data.get("modelId", MODEL_ID)
    if not prompt:
        return failure("请输入提示词", code=2301)
    if not get_model_spec(model_id):
        return failure("暂不支持该模型", code=2302)

    input_path = None
    input_paths = []
    try:
        mode = data.get("generationMode", "img2img")
        images = request.files.getlist("images") + request.files.getlist("image")
        images = [image for image in images if image.filename]
        service = MfluxService(_images_dir(), model_id=model_id, generation_mode=mode)
        service.validate_references(len(images), prompt)
        for input_image in images:
            suffix = Path(secure_filename(input_image.filename)).suffix.lower()
            if suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
                return failure("参考图仅支持 PNG、JPG、JPEG 或 WebP", code=2303)
            uploads_dir = _images_dir().parent / "uploads"
            uploads_dir.mkdir(parents=True, exist_ok=True)
            input_path = uploads_dir / f"{uuid4().hex}{suffix}"
            input_paths.append(input_path)
            input_image.save(input_path)

        validated = MfluxService.validate_params(
            data.get("width", 768), data.get("height", 1024),
            data.get("imageStrength") if input_path and mode == "img2img" else None,
        )
        options = service.validate_options(
            data.get("steps"), data.get("guidance"), data.get("seed"),
        )
        service.validate_generation_dimensions(validated["width"], validated["height"])
        task = _task_manager().submit({
            "model_id": model_id,
            "prompt": prompt,
            "width": validated["width"],
            "height": validated["height"],
            "seed": options["seed"],
            "steps": options["steps"],
            "guidance": options["guidance"],
            "image_strength": validated["image_strength"],
            "generation_mode": mode,
        }, **({"input_paths": input_paths} if mode == "reference" else {"input_path": input_path}))
        input_path = None
        input_paths = []
        return success(task, message="任务已加入队列", status=202)
    except QueueFullError as exc:
        return failure(str(exc), code=2305, status=429)
    except ValueError as exc:
        return failure(str(exc), code=2304)
    except Exception as exc:
        current_app.logger.exception("图片生成失败")
        return failure(f"生成失败：{exc}", code=2500, status=500)
    finally:
        for path in input_paths:
            path.unlink(missing_ok=True)


@api.get("/generate/tasks")
def generation_tasks():
    return success(_task_manager().list_tasks())


@api.get("/generate/tasks/<task_id>")
def generation_task(task_id):
    task = _task_manager().get_task(task_id)
    if not task:
        return failure("任务不存在或服务已重启", code=2405, status=404)
    return success(task)


@api.get("/history")
def history():
    clean_history()
    return success(get_all_history())


@api.delete("/history/<timestamp>")
def delete_image(timestamp):
    entry = get_history_by_timestamp(timestamp)
    if not entry:
        return failure("记录不存在", code=2404, status=404)
    try:
        image_path = Path(entry["image_path"])
        if image_path.exists():
            image_path.unlink()
        delete_history(timestamp)
        return success(message="删除成功")
    except Exception as exc:
        current_app.logger.exception("删除图片失败")
        return failure(f"删除失败：{exc}", code=2501, status=500)
