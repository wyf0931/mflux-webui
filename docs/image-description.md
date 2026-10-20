# 参考图提示词

生图页支持用本地视觉模型分析一张参考图，直接得到可用于生成的提示词，避免手写描述。

## 前置条件

视觉模型使用 `mlx-vlm` 在本机运行，默认仓库为：

```text
lmstudio-community/Qwen3-VL-8B-Instruct-MLX-4bit
```

需要先下载权重（约 5.8 GB）：

```bash
hf download lmstudio-community/Qwen3-VL-8B-Instruct-MLX-4bit
```

可用 `MFLUX_VLM_MODEL` 覆盖为已缓存的其它 mlx-vlm 视觉模型：

```bash
MFLUX_VLM_MODEL=mlx-community/Qwen2.5-VL-7B-Instruct-4bit uv run python app.py
```

服务不会在分析时自动下载权重；本地缺少模型时接口返回提示与下载命令。

## 使用流程

1. 点击提示词旁的「✨ 从参考图生成」，选择一张图片后会自动打开分析弹窗。
2. 也可以先添加参考图（选择、粘贴或从剪贴板读取），再点击参考图卡片上的「AI 描述」。
3. 可选填写关注点，例如“聚焦人物”“服装细节”“光线氛围”；留空则分析整张图。
4. 点击「开始分析」，通常需要 10 秒左右。
5. 在「Prompt」与「结构化」两个 tab 间切换：
   - Prompt：一句英文提示词，可直接用于文生图，支持复制或「填入提示词」。
   - 结构化：按构图与布局、主体与动作、环境与背景、光线与曝光、色彩与配色、镜头与参数、风格与质感列出，支持复制为 Markdown 表格。

分析结果只用于当前弹窗，不写入生成历史，也不会自动提交生成任务。

## 接口

`POST /api/describe`，`multipart/form-data`：

| 字段 | 说明 |
| --- | --- |
| `image` | 参考图，PNG / JPG / JPEG / WebP，每次一张 |
| `focus` | 可选关注点，最长 300 字符 |

成功响应：

```json
{
  "code": 0,
  "data": {
    "model": "lmstudio-community/Qwen3-VL-8B-Instruct-MLX-4bit",
    "duration": 9.8,
    "prompt": "A young woman sits beside a window, soft natural light...",
    "structure": [
      { "label": "构图与布局", "value": "主体居中偏右..." },
      { "label": "光线与曝光", "value": "柔和自然光..." }
    ]
  },
  "message": "ok"
}
```

模型输出被要求为单个 JSON 对象；解析失败时降级为纯文本 Prompt，结构化列表为空。

## 实现说明

- `mflux_webui/vlm_service.py` 负责提示词构造、JSON 解析与模型缓存；模型在首次分析时懒加载，之后复用。
- 推理串行执行，避免并发占用 MLX；上传的临时图片在请求结束后删除。
- 视觉模型常驻内存约占 6 GB，与图像模型同时使用时需要预留足够内存。
- macOS 桌面版已打包 `mlx-vlm` 运行环境，但安装包不包含视觉模型权重，仍需先按上文下载。
