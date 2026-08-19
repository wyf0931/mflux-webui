# 🎨 mflux WebUI

一个基于 Flask 的本地 mflux 图像生成界面。支持 Krea 2 Turbo、Z-Image Turbo 与 FLUX.2 Klein 的模型库管理、文生图、文 + 图生图和画廊。

## 功能

- 模型库：受控推荐、后台下载、已安装缓存与 Hugging Face 页面跳转
- 文生图：提示词、尺寸、步数、随机种子和引导系数
- 文 + 图生图：上传 PNG、JPG、JPEG 或 WebP 参考图，设置 0–1 的参考图强度
- 画廊：浏览、按模型筛选、打开原图、删除历史图片
- 本地模型：通过 Hugging Face SDK 管理缓存与下载
- 深色模式和移动端布局

## 环境要求

- macOS Apple Silicon 与 Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- mflux 模型首次生成时会按 mflux 的行为下载或读取本机缓存

## 启动

```bash
uv sync
npm install
npm run build
uv run python app.py
```

浏览器访问 <http://127.0.0.1:8090>。

也可以使用后台运维脚本：

```bash
./ops.sh start
./ops.sh status
./ops.sh restart
./ops.sh stop
```

日志写入 `logs/app.log`，进程 ID 写入 `logs/app.pid`。

## 使用方式

### 文生图

输入提示词后直接生成。默认尺寸为 768×1376、8 步推理。

### 文 + 图生图

上传参考图，设定参考图强度后输入提示词。例如，强度为 `0.35` 时，模型会较明显保留原图构图，同时按提示词改写内容。

应用通过 mflux Python API 调用模型，避免依赖外部命令进程。

上传的参考图仅作为临时文件使用，生成结束后会自动删除。

## 数据位置

| 内容 | 位置 |
| --- | --- |
| 生成图片 | `data/images/` |
| 生成历史 | `data/db.json` |
| 临时参考图 | `data/uploads/`（生成后清理） |
| 应用日志 | `logs/app.log` |

## 开发检查

```bash
uv run python -m unittest discover -s tests
uv lock --check
npm run build
uv run python -m compileall app.py api.py db.py mflux_service.py model_cache.py
```

## 架构

- Flask：页面壳、静态资源与 `/api` Blueprint 装配。
- Alpine.js：页面局部状态、表单、模型下载状态与画廊交互。
- Tailwind CSS + DaisyUI：统一视觉组件。
- mflux + Hugging Face Hub SDK：本地推理、缓存扫描与模型下载。

所有 API 统一返回以下 JSON 结构：

```json
{ "code": 0, "data": {}, "message": "ok" }
```

`code = 0` 表示成功；`data` 可为对象、数组或 `null`；非零 `code` 表示业务错误。
