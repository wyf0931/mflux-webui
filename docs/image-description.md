# AI 描述

「AI 描述」是独立的功能页（导航中的 **AI 描述**，路径 `/describe`），用本地 Qwen3-VL 分析一张图片，输出一句英文提示词与七项结构化维度，避免手写描述。

这一页与生图页完全解耦：不需要选择模型、不需要排队，也不写入生成历史。分析结果可以复制，或一键带去生图页填入提示词。

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

1. 在「AI 描述」页添加一张图片：拖入页面、点击选择文件，或直接按 ⌘V / Ctrl+V 粘贴；支持的浏览器也可以点击「从剪贴板粘贴」。
2. 可选填写关注点，例如“聚焦人物”“服装细节”“光线氛围”，或点击下方预设标签快速填入；留空则均衡描述整张图。
3. 点击「开始描述」，页面右侧显示加载状态与已耗时，通常需要 10 秒左右，首次分析还要加载模型。
4. 结果分两张卡片展示：
   - **提示词 Prompt**：一句英文提示词，可复制，或点击「去生图」自动带入生图页的提示词框。
   - **结构化维度**：按构图与布局、主体与动作、环境与背景、光线与曝光、色彩与配色、镜头与参数、风格与质感列出，可复制为 Markdown 表格。
5. 更换或移除图片会清空上一次结果；同一张图可以修改关注点后重新描述。

页面顶部的标签显示当前视觉模型与下载状态：未下载时会提示，并提供跳转模型库的入口。

## 接口

`GET /api/describe/model` 返回当前视觉模型与是否已缓存，用于页面顶部的状态提示：

```json
{ "code": 0, "data": { "modelId": "lmstudio-community/Qwen3-VL-8B-Instruct-MLX-4bit", "cached": true }, "message": "ok" }
```

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

- `mflux_webui/templates/describe.html` 与 `main.js` 中的 `describePage` 组件实现页面；结果只保存在页面状态，刷新即清空。
- `mflux_webui/vlm_service.py` 负责提示词构造、JSON 解析与模型缓存；模型在首次分析时懒加载，之后复用。
- 推理串行执行，避免并发占用 MLX；上传的临时图片在请求结束后删除。
- 视觉模型常驻内存约占 6 GB，与图像模型同时使用时需要预留足够内存。
- macOS 桌面版已打包 `mlx-vlm` 运行环境，但安装包不包含视觉模型权重，仍需先按上文下载。
