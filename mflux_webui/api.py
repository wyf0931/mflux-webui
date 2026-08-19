"""前后端分离的 JSON API。所有响应遵循 code/data/message 协议。"""

from pathlib import Path
from uuid import uuid4

from flask import Blueprint, current_app, jsonify, request
from werkzeug.utils import secure_filename

from .db import (
    add_history_entry,
    clean_history,
    delete_history,
    get_all_history,
    get_history_by_timestamp,
)
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


def _mflux_service(model_id):
    return MfluxService(_images_dir(), model_id=model_id)


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
    try:
        input_image = request.files.get("image")
        if input_image and input_image.filename:
            suffix = Path(secure_filename(input_image.filename)).suffix.lower()
            if suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
                return failure("参考图仅支持 PNG、JPG、JPEG 或 WebP", code=2303)
            uploads_dir = _images_dir().parent / "uploads"
            uploads_dir.mkdir(parents=True, exist_ok=True)
            input_path = uploads_dir / f"{uuid4().hex}{suffix}"
            input_image.save(input_path)

        result = _mflux_service(model_id).generate(
            prompt=prompt, width=data.get("width", 768), height=data.get("height", 1024),
            seed=data.get("seed"), steps=data.get("steps"), guidance=data.get("guidance"),
            input_image=input_path, image_strength=data.get("imageStrength"),
        )
        timestamp = result.filename.removesuffix(".png")
        add_history_entry({
            "timestamp": timestamp, "model": result.model, "width": result.width,
            "height": result.height, "prompt": result.prompt, "image_path": result.image_path,
            "duration": result.duration, "metadata": result.metadata,
        })
        return success({"filename": result.filename, "duration": result.duration, "timestamp": timestamp}, message="生成完成")
    except ValueError as exc:
        return failure(str(exc), code=2304)
    except Exception as exc:
        current_app.logger.exception("图片生成失败")
        return failure(f"生成失败：{exc}", code=2500, status=500)
    finally:
        if input_path and input_path.exists():
            input_path.unlink()


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
