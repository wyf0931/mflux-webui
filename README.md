# mflux WebUI

在 Apple Silicon Mac 上本地生成图片的 WebUI：Flask 后端、Alpine.js 与 daisyUI 5 前端，推理由 mflux 与 MLX 驱动，模型权重与生成过程都不离开本机。

支持文生图、参考图生图、Qwen 多参考图编辑、模型缓存管理、异步队列、任务日志与历史画廊。除网页版外提供 [macOS 桌面版](docs/desktop.md)：Tauri 2 打包，安装后直接打开，无需安装 Python 或 Node.js，首次使用时下载模型。安装包见 [GitHub Releases](https://github.com/wyf0931/mflux-webui/releases)。

## 功能亮点

- **模型**：Qwen Image 2.1 Turbo、Krea 2 Turbo、Z-Image Turbo、FLUX.2 Klein，q4 / q8 / 4-bit 多种量化版本。
- **参考图**：本地选择或 ⌘V / Ctrl+V 粘贴，自动预览，可替换、移除，生成时上传。
- **Qwen 多参考图编辑**：高级选项中切换生成方式，按顺序添加 1–10 张图片，用“图一、图二”或 `<image1>`、`<image2>` 指定引用；原单图保持构图模式继续可用。
- **参考图提示词**：本地 Qwen3-VL 分析参考图，生成一句提示词与结构化维度，支持复制或填入。
- **参数**：随模型切换默认值；Qwen Turbo 默认 8 步、引导系数固定为 1.0。
- **队列**：查看状态、模型别名、耗时和结果；失败时通过“查看日志”弹窗查看完整堆栈。
- **界面**：daisyUI 的 Rausch 浅色主题与深色扩展，中文字体回退与手机布局。
- **渠道**：Hugging Face / ModelScope 双渠道，沿用各 SDK 的默认模型缓存目录。

## 界面预览

| 生图 | 画廊 | 模型库 |
| --- | --- | --- |
| ![生图页面](docs/images/generate.png) | ![画廊页面](docs/images/gallery.png) | ![模型库页面](docs/images/models.png) |

| 生成队列 | 完整日志弹窗 |
| --- | --- |
| ![生成队列](docs/images/queue.png) | ![完整日志弹窗](docs/images/task-logs.png) |

截图使用示例任务，不包含用户的生成历史。

## 快速开始

环境要求：macOS Apple Silicon、Python 3.11 或更新版本、Node.js 20 或更新版本、npm 和 [uv](https://docs.astral.sh/uv/)。

```bash
git clone https://github.com/wyf0931/mflux-webui.git
cd mflux-webui
uv sync
npm install
npm run build
uv run python app.py
```

打开 <http://127.0.0.1:8090>，在「模型库」下载模型后即可生成。模型权重首次使用需要下载，请预留磁盘空间与统一内存。

后台运行使用 `./ops.sh start|stop|status|logs`，详见 [开发与运维](docs/development.md)。

## 文档

| 文档 | 内容 |
| --- | --- |
| [文档索引](docs/README.md) | 全部文档的分类导航 |
| [使用指南](docs/usage.md) | 文生图、图生图、Qwen 多参考图编辑、队列与任务日志 |
| [模型与配置](docs/configuration.md) | 模型目录、下载渠道、环境变量、数据位置 |
| [参考图提示词](docs/image-description.md) | 本地 Qwen3-VL 视觉模型的前置条件与输出结构 |
| [macOS 桌面版](docs/desktop.md) | 安装、独立数据目录、本机打包、GitHub Actions 与 Release |
| [开发与运维](docs/development.md) | 安装、构建、后台运行、自动化检查、项目结构 |
| [主题与组件约定](docs/theme.md) | daisyUI 主题变量、系统字体、组件及交互规范 |
| [Qwen Image 2.1 Turbo 接入](docs/qwen-image-21-turbo.md) | 固定依赖、HF 模型与兼容性问题排查 |
| [项目协作说明](AGENTS.md) | 开发命令与代码协作要求 |

## 开发检查

```bash
npm run build
node --test tests/js/*.test.cjs
uv run python -m unittest discover -s tests
uv lock --check
uv run python -m compileall app.py mflux_webui tests
uv run --with ruff ruff check app.py mflux_webui tests
```

欢迎提交 Issue 和 Pull Request。提交前请说明用户可见的行为变化，Bug 请提供复现步骤，并运行上述检查。

## 许可证

本项目使用 [ISC License](LICENSE)。
