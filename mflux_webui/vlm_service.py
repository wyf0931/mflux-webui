"""用本地 mlx-vlm 视觉模型把参考图描述成生图提示词。"""

import json
import os
import re
import threading
import time
from typing import Any, cast

DEFAULT_MODEL_ID = "lmstudio-community/Qwen3-VL-8B-Instruct-MLX-4bit"
MAX_FOCUS_LENGTH = 300
MAX_TOKENS = 800

# 顺序即前端结构化表格的展示顺序。
STRUCTURE_FIELDS = (
    "构图与布局",
    "主体与动作",
    "环境与背景",
    "光线与曝光",
    "色彩与配色",
    "镜头与参数",
    "风格与质感",
)

INSTRUCTION = """你是专业的图像提示词工程师。分析这张参考图，只输出一个 JSON 对象，不要输出其它文字：
{{"prompt": "一句英文图像提示词，按主体、动作、环境、构图、光线、配色、镜头与质感顺序描述，可直接用于文生图", "structure": {{{fields}}}}}
要求：prompt 为英文；structure 每个字段用一句中文描述；镜头与参数给出合理推测（焦段、光圈、景深、快门）；不要出现“参考图”字样。{focus}"""


def configured_model_id():
    """返回视觉模型仓库 ID，可用 MFLUX_VLM_MODEL 覆盖。"""
    return os.getenv("MFLUX_VLM_MODEL", "").strip() or DEFAULT_MODEL_ID


def build_instruction(focus=""):
    """构造要求模型输出 JSON 的中文指令。"""
    fields = ", ".join(f'"{field}": ""' for field in STRUCTURE_FIELDS)
    focus = (focus or "").strip()[:MAX_FOCUS_LENGTH]
    focus_line = f"\n用户关注点：{focus}" if focus else "\n用户没有指定关注点，请均衡描述。"
    return INSTRUCTION.format(fields=fields, focus=focus_line)


def _extract_json(text):
    """从可能带代码围栏或前后缀的回复中取出第一个 JSON 对象。"""
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.MULTILINE).strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        return json.loads(cleaned[start:end + 1])
    except json.JSONDecodeError:
        return None


def _structure_rows(structure):
    """把 dict 或 list 形式的结构化结果归一为有序的 label/value 行。"""
    if isinstance(structure, dict):
        items = [{"label": key, "value": value} for key, value in structure.items()]
    elif isinstance(structure, list):
        items = [
            {"label": item.get("label") or item.get("name"), "value": item.get("value") or item.get("detail")}
            for item in structure if isinstance(item, dict)
        ]
    else:
        items = []

    rows = []
    for item in items:
        label = str(item.get("label") or "").strip()
        value = str(item.get("value") or "").strip()
        if label and value:
            rows.append({"label": label, "value": value})
    order = {field: index for index, field in enumerate(STRUCTURE_FIELDS)}
    # 固定维度优先且按固定顺序；模型额外给出的维度排在其后。
    return sorted(rows, key=lambda row: order.get(row["label"], len(order)))


def parse_description(text):
    """把模型输出解析为一句提示词与结构化行；JSON 不可用时降级为纯文本提示词。"""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("视觉模型没有返回描述内容")
    data = _extract_json(text)
    if not isinstance(data, dict):
        return {"prompt": text.strip(), "structure": []}

    rows = _structure_rows(data.get("structure"))
    prompt = str(data.get("prompt") or "").strip()
    if not prompt:
        # 模型偶尔只给出结构化结果，用维度内容拼出可用的提示词。
        prompt = "；".join(f"{row['label']}：{row['value']}" for row in rows)
    if not prompt:
        raise ValueError("视觉模型没有返回可用的提示词")
    return {"prompt": prompt, "structure": rows}


class VlmService:
    """进程内复用视觉模型；推理串行执行，避免并发占用 MLX。"""

    def __init__(self, model_id=None):
        self.model_id = model_id or configured_model_id()
        self._lock = threading.Lock()
        self._loaded = None

    def is_model_cached(self):
        """只使用已下载的权重，避免分析时意外拉取数 GB 模型。"""
        from huggingface_hub import try_to_load_from_cache

        cached = try_to_load_from_cache(self.model_id, "config.json")
        return isinstance(cached, str)

    def _load(self):
        from mlx_vlm import load
        from mlx_vlm.utils import load_config

        model, processor = load(self.model_id)
        return model, processor, load_config(self.model_id)

    def describe(self, image_path, focus=""):
        """分析一张本地图片，返回提示词、结构化维度、模型与耗时。"""
        if not self.is_model_cached():
            raise ValueError(f"本地未找到视觉模型 {self.model_id}，请先执行 hf download {self.model_id}")
        instruction = build_instruction(focus)
        started_at = time.monotonic()
        try:
            with self._lock:
                # 延迟导入 MLX，模型库、缓存接口和测试都不需要初始化 Metal。
                from mlx_vlm import generate
                from mlx_vlm.prompt_utils import apply_chat_template

                if self._loaded is None:
                    self._loaded = self._load()
                model, processor, config = self._loaded
                prompt = cast(str, apply_chat_template(processor, config, instruction, num_images=1))
                # mlx-vlm 的 generate 签名把 processor 标注成 tokenizer，实际接受 VLM processor。
                run = cast(Any, generate)
                output = run(
                    model, processor, prompt, image=[str(image_path)],
                    max_tokens=MAX_TOKENS, temperature=0.0, verbose=False,
                )
        except Exception as exc:
            raise RuntimeError(f"视觉模型分析失败：{exc}") from exc

        text = getattr(output, "text", None) or str(output)
        return {
            "model": self.model_id,
            "duration": round(time.monotonic() - started_at, 1),
            **parse_description(text),
        }
