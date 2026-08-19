"""mflux WebUI 支持的模型目录与运行时能力声明。"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelSpec:
    repo_id: str
    name: str
    family: str
    backend: str
    size_gb: float
    steps: int
    guidance: float | None
    scheduler: str | None
    supports_image_to_image: bool = True


CURATED_MODELS = (
    ModelSpec("mflux-community/krea-2-turbo-mflux-q4", "Krea 2 Turbo · q4", "Krea 2 Turbo", "krea2", 14.7, 8, 1.0, "er_sde"),
    ModelSpec("mflux-community/krea-2-turbo-mflux-q8", "Krea 2 Turbo · q8", "Krea 2 Turbo", "krea2", 20.7, 8, 1.0, "er_sde"),
    ModelSpec("OsaurusAI/Z-Image-Turbo-mflux-4bit", "Z-Image Turbo · 4-bit", "Z-Image Turbo", "zimage", 5.5, 4, None, None),
    ModelSpec("Runpod/FLUX.2-klein-4B-mflux-4bit", "FLUX.2 Klein 4B · 4-bit", "FLUX.2 Klein 4B", "flux2-4b", 4.3, 4, 1.0, "flow_match_euler_discrete"),
    ModelSpec("mflux-community/flux2-klein-9b-mflux-q4", "FLUX.2 Klein 9B · q4", "FLUX.2 Klein 9B", "flux2-9b", 8.9, 4, 1.0, "flow_match_euler_discrete"),
)


def get_model_spec(repo_id):
    """按仓库 ID 返回模型能力；同一系列的受支持量化仓库可复用适配器。"""
    normalized = repo_id.casefold().replace("_", "-")
    for spec in CURATED_MODELS:
        if spec.repo_id.casefold() == repo_id.casefold():
            return spec
    if "krea-2" in normalized or "krea2" in normalized:
        return ModelSpec(repo_id, repo_id, "Krea 2 Turbo", "krea2", 0, 8, 1.0, "er_sde")
    if "z-image" in normalized or "zimage" in normalized:
        return ModelSpec(repo_id, repo_id, "Z-Image Turbo", "zimage", 0, 4, None, None)
    if any(token in normalized for token in ("flux2-klein-4b", "flux-2-klein-4b", "flux.2-klein-4b")):
        return ModelSpec(repo_id, repo_id, "FLUX.2 Klein 4B", "flux2-4b", 0, 4, 1.0, "flow_match_euler_discrete")
    if any(token in normalized for token in ("flux2-klein-9b", "flux-2-klein-9b", "flux.2-klein-9b")):
        return ModelSpec(repo_id, repo_id, "FLUX.2 Klein 9B", "flux2-9b", 0, 4, 1.0, "flow_match_euler_discrete")
    return None


def catalog_models(installed_ids=()):
    """返回带安装状态的受控模型目录。"""
    installed = set(installed_ids)
    return [{
        "repoId": spec.repo_id, "name": spec.name, "family": spec.family,
        "sizeGB": spec.size_gb, "steps": spec.steps, "installed": spec.repo_id in installed,
        "supportsImageToImage": spec.supports_image_to_image,
    } for spec in CURATED_MODELS]
