"""读取本机 Hugging Face 缓存，并补充公开模型元数据。"""

from huggingface_hub import HfApi, scan_cache_dir


IMAGE_MODEL_FAMILIES = (
    "z-image",
    "zimage",
    "krea-2",
    "krea2",
    "krea-dev",
    "flux2",
    "flux-2",
    "flux.2",
    "flux1",
    "flux-1",
    "flux.1",
    "qwen-image",
    "fibo",
    "ernie-image",
    "ideogram4",
    "ideogram-4",
)


def is_mflux_image_model(repo_id):
    """判断缓存仓库是否属于 mflux 支持的图像生成模型家族。

    只识别明确的图像模型命名；例如 ``Qwen3`` 是语言模型，不能因带有
    ``qwen`` 一词而展示在这里。
    """
    normalized_id = repo_id.casefold().replace("_", "-")
    return any(family in normalized_id for family in IMAGE_MODEL_FAMILIES)


def get_model_family(repo_id):
    """返回适合界面展示的 mflux 图像模型家族名称。"""
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


def get_hub_metadata(repo_id):
    """读取公开 Hub 元数据；网络不可用时保持本地缓存页可用。"""
    try:
        info = HfApi().model_info(repo_id, timeout=4)
    except Exception:
        return {}

    return {
        "pipelineTag": info.pipeline_tag,
        "library": info.library_name,
        "downloads": info.downloads,
        "likes": info.likes,
        "hubUpdatedAt": info.last_modified.isoformat() if info.last_modified else None,
    }


def get_cached_models(include_hub_metadata=True):
    """返回已缓存且可由 mflux 使用的图像生成模型。

    模型选择等即时交互只需本地信息，可跳过 Hub 网络查询。
    """
    try:
        cache_info = scan_cache_dir()
    except Exception as exc:
        return {"models": [], "error": f"无法读取 Hugging Face 缓存：{exc}"}

    models = []
    for repo in cache_info.repos:
        if repo.repo_type != "model" or not is_mflux_image_model(repo.repo_id):
            continue
        revisions = list(repo.revisions)
        newest_revision = max(revisions, key=lambda revision: revision.last_modified, default=None)
        model = {
            "repoId": repo.repo_id,
            "repoType": repo.repo_type,
            "size": repo.size_on_disk,
            "revisions": len(revisions),
            "files": sum(len(revision.files) for revision in revisions),
            "family": get_model_family(repo.repo_id),
            "lastAccessed": repo.last_accessed_str,
            "lastModified": repo.last_modified_str,
            "revision": newest_revision.commit_hash[:8] if newest_revision else None,
        }
        if include_hub_metadata:
            model.update(get_hub_metadata(repo.repo_id))
        models.append(model)
    return {"models": sorted(models, key=lambda item: item["repoId"].lower()), "error": None}
