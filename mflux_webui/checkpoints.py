"""选择完整的缓存快照，兼容 Krea 旧版 mflux 分片权重。"""

import json
from pathlib import Path


def complete_component(path):
    index = path / "model.safetensors.index.json"
    if index.is_file():
        try:
            names = json.loads(index.read_text(encoding="utf-8"))["weight_map"].values()
            return bool(names) and all(
                isinstance(name, str) and Path(name).name == name
                and name.endswith(".safetensors") and (path / name).is_file()
                for name in names
            )
        except (OSError, ValueError, KeyError, AttributeError):
            return False
    return any(file.is_file() for file in path.glob("*.safetensors"))


def resolve_krea_checkpoint(repo_id, cache_root=None):
    from huggingface_hub.constants import HF_HUB_CACHE

    repository = Path(cache_root or HF_HUB_CACHE) / f"models--{repo_id.replace('/', '--')}"
    snapshots = repository / "snapshots"
    if not snapshots.is_dir():
        return repo_id
    main = repository / "refs/main"
    revision = main.read_text().strip() if main.is_file() else ""
    candidates = sorted((p for p in snapshots.iterdir() if p.is_dir()),
                        key=lambda p: (p.name == revision, p.stat().st_mtime), reverse=True)
    for path in candidates:
        transformer = (
            (path / "turbo.safetensors").is_file()
            or ((path / "model.safetensors.index.json").is_file() and complete_component(path))
            or complete_component(path / "transformer")
        )
        if (transformer and complete_component(path / "vae")
                and complete_component(path / "text_encoder")
                and all((path / "tokenizer" / name).is_file()
                        for name in ("tokenizer.json", "tokenizer_config.json"))):
            return str(path)
    return repo_id
