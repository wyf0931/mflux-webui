"""读取 Hugging Face 与 ModelScope 的默认缓存，并补充模型元数据。"""

import os
from pathlib import Path

from huggingface_hub import HfApi, scan_cache_dir

from .model_registry import configured_sources

IMAGE_MODEL_FAMILIES = (
    "z-image", "zimage", "krea-2", "krea2", "krea-dev", "flux2", "flux-2", "flux.2",
    "flux1", "flux-1", "flux.1", "qwen-image", "fibo", "ernie-image", "ideogram4", "ideogram-4",
)


def is_mflux_image_model(repo_id):
    """判断缓存仓库是否属于 mflux 支持的图像生成模型家族。"""
    normalized_id = repo_id.casefold().replace("_", "-")
    return any(family in normalized_id for family in IMAGE_MODEL_FAMILIES)


def get_model_family(repo_id):
    normalized_id = repo_id.casefold().replace("_", "-")
    if "krea-2" in normalized_id or "krea2" in normalized_id:
        return "Krea 2 Turbo"
    if "z-image" in normalized_id or "zimage" in normalized_id:
        return "Z-Image"
    if any(name in normalized_id for name in ("flux2", "flux-2", "flux.2")):
        return "FLUX.2"
    if any(name in normalized_id for name in ("flux1", "flux-1", "flux.1")):
        return "FLUX.1"
    if "qwen-image" in normalized_id:
        return "Qwen-Image"
    if "ernie-image" in normalized_id:
        return "ERNIE Image"
    if "ideogram" in normalized_id:
        return "Ideogram"
    if "fibo" in normalized_id:
        return "FIBO"
    return "mflux 图像模型"


def get_hub_metadata(repo_id, source="huggingface"):
    """读取公开 Hub 元数据；网络不可用时保持本地缓存页可用。"""
    if source != "huggingface":
        return {}
    try:
        info = HfApi().model_info(repo_id, timeout=4)
    except Exception:
        return {}
    return {
        "pipelineTag": info.pipeline_tag, "library": info.library_name,
        "downloads": info.downloads, "likes": info.likes,
        "hubUpdatedAt": info.last_modified.isoformat() if info.last_modified else None,
    }


def _get_modelscope_cache_root():
    return Path(os.getenv("MODELSCOPE_CACHE", Path.home() / ".cache" / "modelscope" / "hub" / "models"))


def _get_modelscope_models():
    root = _get_modelscope_cache_root()
    if not root.is_dir():
        return []
    models = []
    for owner_dir in root.iterdir():
        if not owner_dir.is_dir() or owner_dir.name.startswith("."):
            continue
        for model_dir in owner_dir.iterdir():
            if not model_dir.is_dir():
                continue
            repo_id = f"{owner_dir.name}/{model_dir.name}"
            if not is_mflux_image_model(repo_id):
                continue
            files = [path for path in model_dir.rglob("*") if path.is_file()]
            newest = max((path.stat().st_mtime for path in files), default=None)
            models.append({
                "repoId": repo_id, "repoType": "model", "source": "modelscope",
                "size": sum(path.stat().st_size for path in files), "revisions": 1,
                "files": len(files), "family": get_model_family(repo_id),
                "lastAccessed": None, "lastModified": newest,
                "revision": None,
            })
    return models


def _get_huggingface_models(include_hub_metadata=True):
    try:
        cache_info = scan_cache_dir()
    except Exception as exc:
        return [], f"无法读取 Hugging Face 缓存：{exc}"
    models = []
    for repo in cache_info.repos:
        if repo.repo_type != "model" or not is_mflux_image_model(repo.repo_id):
            continue
        revisions = list(repo.revisions)
        newest_revision = max(revisions, key=lambda revision: revision.last_modified, default=None)
        model = {
            "repoId": repo.repo_id, "repoType": repo.repo_type, "source": "huggingface",
            "size": repo.size_on_disk, "revisions": len(revisions),
            "files": sum(len(revision.files) for revision in revisions),
            "family": get_model_family(repo.repo_id), "lastAccessed": repo.last_accessed_str,
            "lastModified": repo.last_modified_str,
            "revision": newest_revision.commit_hash[:8] if newest_revision else None,
        }
        if include_hub_metadata:
            model.update(get_hub_metadata(repo.repo_id))
        models.append(model)
    return models, None


def get_cached_models(include_hub_metadata=True):
    """返回已缓存且可由 mflux 使用的两个渠道的图像生成模型。"""
    sources = configured_sources()
    models, error = [], None
    if "huggingface" in sources:
        hf_models, error = _get_huggingface_models(include_hub_metadata)
        models.extend(hf_models)
    if "modelscope" in sources:
        models.extend(_get_modelscope_models())
    return {"models": sorted(models, key=lambda item: (item["source"], item["repoId"].lower())), "error": error}
