"""mflux 0.18.1 的 Krea 2 Python API 适配层。"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import time

from mflux.models.common.config import ModelConfig
from mflux.models.krea2 import Krea2


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

    def __init__(self, images_dir):
        self.images_dir = Path(images_dir)
        self.images_dir.mkdir(parents=True, exist_ok=True)

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

    @staticmethod
    def _load_model():
        """以 mflux 的 Krea 2 配置加载已缓存的量化模型。"""
        return Krea2(model_config=ModelConfig.krea2(), model_path=MODEL_ID)

    def generate(self, prompt, width, height, seed=None, steps=None, guidance=None,
                 input_image=None, image_strength=None):
        image_strength = image_strength if input_image and image_strength not in (None, "") else None
        validated = self.validate_params(width, height, image_strength)
        steps = int(steps if steps not in (None, "") else DEFAULTS["steps"])
        guidance = float(guidance if guidance not in (None, "") else DEFAULTS["guidance"])
        seed = int(seed if seed not in (None, "") else time.time_ns() % 1_000_000_000)

        filename = f"{datetime.now().strftime('%Y-%m-%d-%H-%M-%S-%f')}.png"
        output_path = self.images_dir / filename
        started_at = time.monotonic()
        try:
            model = self._load_model()
            image = model.generate_image(
                seed=seed,
                prompt=prompt,
                num_inference_steps=steps,
                height=validated["height"],
                width=validated["width"],
                guidance=guidance,
                image_path=input_image,
                image_strength=validated["image_strength"],
                scheduler="er_sde",
            )
            image.save(output_path)
        except Exception as exc:
            raise RuntimeError(f"mflux 生成失败：{exc}") from exc

        if not output_path.is_file():
            raise RuntimeError("mflux 未生成输出图片")

        return GenerationResult(
            image_path=str(output_path), filename=filename,
            duration=time.monotonic() - started_at, model=MODEL_ID,
            width=validated["width"], height=validated["height"], prompt=prompt,
            metadata={"seed": seed, "steps": steps, "guidance": guidance,
                      "scheduler": "er_sde",
                      "imageStrength": validated["image_strength"] if input_image else None},
        )
