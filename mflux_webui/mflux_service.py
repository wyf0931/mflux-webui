"""mflux 0.18.1 的 Krea 2 Python API 适配层。"""

import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from .model_registry import get_model_spec

MODEL_ID = "mflux-community/krea-2-turbo-mflux-q4"
# Krea 2 Turbo 是 CFG 1.0 蒸馏模型；更高的引导系数会偏离官方采样设置并损伤画面质量。
DEFAULTS = {"width": 768, "height": 1376, "steps": 8, "guidance": 1.0}


@dataclass
class GenerationResult:
    image_path: str
    filename: str
    duration: float
    model: str
    width: int
    height: int
    prompt: str
    metadata: dict = field(default_factory=dict)


class MfluxService:
    """通过 mflux 的 Krea 2 Python API 生成图片。"""

    def __init__(self, images_dir, model_id=MODEL_ID):
        self.images_dir = Path(images_dir)
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.model_id = model_id
        self.spec = get_model_spec(model_id)
        if not self.spec:
            raise ValueError("暂不支持该模型")

    @staticmethod
    def validate_params(width, height, image_strength=None):
        try:
            width = int(width)
            height = int(height)
        except (TypeError, ValueError) as exc:
            raise ValueError("图片尺寸必须是数字") from exc

        width = max(256, min(2048, width)) // 16 * 16
        height = max(256, min(2048, height)) // 16 * 16
        if image_strength is not None:
            try:
                image_strength = float(image_strength)
            except (TypeError, ValueError) as exc:
                raise ValueError("参考图强度必须是数字") from exc
            if not 0 <= image_strength <= 1:
                raise ValueError("参考图强度必须在 0 到 1 之间")
        return {"width": width, "height": height, "image_strength": image_strength}

    def _load_model(self):
        """以 mflux 的 Krea 2 配置加载已缓存的量化模型。"""
        # 延迟导入 MLX，确保模型目录、缓存 API 和开发测试不需要在导入阶段初始化 Metal。
        from mflux.models.common.config import ModelConfig
        from mflux.models.flux2 import Flux2Klein
        from mflux.models.krea2 import Krea2
        from mflux.models.z_image import ZImageTurbo

        if self.spec.backend == "krea2":
            return Krea2(model_config=ModelConfig.krea2(), model_path=self.model_id)
        if self.spec.backend == "zimage":
            return ZImageTurbo(model_path=self.model_id)
        if self.spec.backend == "flux2-4b":
            return Flux2Klein(model_config=ModelConfig.flux2_klein_4b(), model_path=self.model_id)
        if self.spec.backend == "flux2-9b":
            return Flux2Klein(model_config=ModelConfig.flux2_klein_9b(), model_path=self.model_id)
        raise ValueError("暂不支持该模型")

    def load_model(self):
        """加载模型，供进程级模型缓存管理器调用。"""
        return self._load_model()

    def generate(self, prompt, width, height, seed=None, steps=None, guidance=None,
                 input_image=None, image_strength=None, model=None):
        image_strength = image_strength if input_image and image_strength not in (None, "") else None
        validated = self.validate_params(width, height, image_strength)
        steps = int(steps if steps not in (None, "") else self.spec.steps)
        guidance = float(guidance if guidance not in (None, "") else (self.spec.guidance if self.spec.guidance is not None else DEFAULTS["guidance"]))
        seed = int(seed if seed not in (None, "") else time.time_ns() % 1_000_000_000)

        filename = f"{datetime.now(UTC).astimezone().strftime('%Y-%m-%d-%H-%M-%S-%f')}.png"
        output_path = self.images_dir / filename
        started_at = time.monotonic()
        try:
            model = model or self.load_model()
            image = model.generate_image(
                seed=seed,
                prompt=prompt,
                num_inference_steps=steps,
                height=validated["height"],
                width=validated["width"],
                guidance=guidance,
                image_path=input_image,
                image_strength=validated["image_strength"],
                scheduler=self.spec.scheduler,
            )
            image.save(output_path)
        except Exception as exc:
            raise RuntimeError(f"mflux 生成失败：{exc}") from exc

        if not output_path.is_file():
            raise RuntimeError("mflux 未生成输出图片")

        return GenerationResult(
            image_path=str(output_path), filename=filename,
            duration=time.monotonic() - started_at, model=self.model_id,
            width=validated["width"], height=validated["height"], prompt=prompt,
            metadata={"seed": seed, "steps": steps, "guidance": guidance,
                      "scheduler": self.spec.scheduler,
                      "imageStrength": validated["image_strength"] if input_image else None},
        )
