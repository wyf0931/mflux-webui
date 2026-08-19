"""从 JSON 配置加载 mflux 模型目录与运行时能力声明。"""

import json
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")
MODEL_CONFIG_PATH = PROJECT_ROOT / "config" / "models.json"
MODEL_SOURCES = ("huggingface", "modelscope")
VALID_MODEL_REPOS = ("all", *MODEL_SOURCES)


@dataclass(frozen=True)
class ModelSpec:
    key: str
    repo_id: str
    source: str
    name: str
    family: str
    backend: str
    size_gb: float
    steps: int
    guidance: float | None
    scheduler: str | None
    supports_image_to_image: bool = True


def _load_model_config():
    try:
        with MODEL_CONFIG_PATH.open(encoding="utf-8") as config_file:
            config = json.load(config_file)
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"无法读取模型配置 {MODEL_CONFIG_PATH}: {exc}") from exc
    if not isinstance(config, dict) or not isinstance(config.get("models"), list):
        raise RuntimeError("模型配置必须包含 models 数组")
    return config["models"]


MODEL_CONFIG = _load_model_config()


def configured_sources():
    """返回当前启用的模型渠道；空值或非法值均按 all 处理。"""
    value = os.getenv("MODEL_REPO", "all").strip().casefold()
    return MODEL_SOURCES if value == "all" or value not in VALID_MODEL_REPOS else (value,)


def _spec_from_entry(entry, source, repo_id):
    return ModelSpec(
        key=entry["key"], repo_id=repo_id, source=source,
        name=entry["name"], family=entry["family"], backend=entry["backend"],
        size_gb=float(entry.get("sizeGB", 0)), steps=int(entry.get("steps", 4)),
        guidance=entry.get("guidance"), scheduler=entry.get("scheduler"),
        supports_image_to_image=bool(entry.get("supportsImageToImage", True)),
    )


def iter_model_specs(sources=None):
    """按配置顺序返回可用渠道的模型能力。"""
    sources = tuple(sources or configured_sources())
    for entry in MODEL_CONFIG:
        for source in sources:
            repo_id = entry.get(source)
            if repo_id:
                yield _spec_from_entry(entry, source, repo_id)


def get_model_spec(repo_id, source=None):
    """按仓库 ID 和可选渠道返回模型能力。"""
    if not repo_id:
        return None
    for spec in iter_model_specs((source,) if source else MODEL_SOURCES):
        if spec.repo_id.casefold() == repo_id.casefold():
            return spec

    normalized = repo_id.casefold().replace("_", "-")
    fallback = None
    if "krea-2" in normalized or "krea2" in normalized:
        fallback = ("Krea 2 Turbo", "krea2", 8, 1.0, "er_sde")
    elif "z-image" in normalized or "zimage" in normalized:
        fallback = ("Z-Image Turbo", "zimage", 4, None, None)
    elif any(token in normalized for token in ("flux2-klein-4b", "flux-2-klein-4b", "flux.2-klein-4b")):
        fallback = ("FLUX.2 Klein 4B", "flux2-4b", 4, 1.0, "flow_match_euler_discrete")
    elif any(token in normalized for token in ("flux2-klein-9b", "flux-2-klein-9b", "flux.2-klein-9b")):
        fallback = ("FLUX.2 Klein 9B", "flux2-9b", 4, 1.0, "flow_match_euler_discrete")
    if not fallback:
        return None
    family, backend, steps, guidance, scheduler = fallback
    return ModelSpec(repo_id, repo_id, source or "huggingface", repo_id, family, backend, 0, steps, guidance, scheduler)


def _repo_url(source, repo_id):
    host = "huggingface.co" if source == "huggingface" else "modelscope.cn/models"
    return f"https://{host}/{repo_id}"


def catalog_models(installed_ids=(), sources=None):
    """返回带渠道、仓库链接和安装状态的受控模型目录。"""
    installed = {
        (item.get("source", "huggingface"), item["repoId"]) if isinstance(item, dict) else (None, item)
        for item in installed_ids
    }
    models = []
    for spec in iter_model_specs(sources):
        is_installed = (spec.source, spec.repo_id) in installed or (None, spec.repo_id) in installed
        models.append({
            "key": spec.key, "source": spec.source, "repoId": spec.repo_id,
            "repoUrl": _repo_url(spec.source, spec.repo_id), "name": spec.name,
            "family": spec.family, "sizeGB": spec.size_gb, "steps": spec.steps,
            "installed": is_installed, "supportsImageToImage": spec.supports_image_to_image,
        })
    return models
