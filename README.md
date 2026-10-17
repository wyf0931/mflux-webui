# mflux WebUI

使用 Flask、Alpine.js、Tailwind CSS 4 与 daisyUI 5，在 Apple Silicon Mac 上通过 mflux 本地生成图像。
支持文生图、参考图生图、模型缓存管理、异步队列和历史画廊。

提供 [macOS 桌面版](docs/desktop.md)：使用 Tauri 2，安装后直接打开，无需安装 Python 或 Node.js；首次使用时下载模型。下载见 [GitHub Releases](https://github.com/wyf0931/mflux-webui/releases)。

- **模型**：Qwen Image 2.1 Turbo、Krea 2 Turbo、Z-Image Turbo、FLUX.2 Klein。
- **参考图**：本地选择或 ⌘V / Ctrl+V 粘贴，自动预览，可替换、移除，生成时上传。
- **Qwen 多参考图编辑**：高级选项中切换生成方式，按顺序添加 1–10 张图片，通过“图一、图二”或 `<image1>`、`<image2>` 指定引用；原单图保持构图模式继续可用。
- **参数**：随模型切换默认值；Qwen Turbo 默认 8 步、引导系数固定为 1.0。
- **队列**：查看状态、模型别名、耗时和结果；失败时通过“查看日志”弹窗查看完整错误。
- **界面**：基于 daisyUI 的 Rausch 浅色主题与深色扩展，支持系统中文字体和手机布局。
- **渠道**：Hugging Face / ModelScope，沿用各 SDK 的默认模型缓存目录。

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

打开 <http://127.0.0.1:8090>。

当前 mflux 固定为 0.22.0 加上上游 PR [#859](https://github.com/mflux-community/mflux/pull/859)
对应的合并提交，包含 Qwen Image 2.1 Turbo 加载与调度修复。使用 `uv sync` 即可安装正确版本。
模型首次使用需要下载权重，请预留磁盘空间与统一内存。

## 界面预览

| 生图 | 画廊 | 模型库 |
| --- | --- | --- |
| ![生图页面](docs/images/generate.png) | ![画廊页面](docs/images/gallery.png) | ![模型库页面](docs/images/models.png) |

| 生成队列 | 完整日志弹窗 |
| --- | --- |
| ![生成队列](docs/images/queue.png) | ![完整日志弹窗](docs/images/task-logs.png) |

截图使用示例任务，不包含用户的生成历史。

## 后台运行

```bash
./ops.sh start
./ops.sh status
./ops.sh status --watch
./ops.sh logs 100
./ops.sh restart
./ops.sh stop
```

日志位于 `logs/app.log`，PID 位于 `logs/app.pid`。
模型目录位于 [`config/models.json`](config/models.json)，环境变量参考 [`.env.example`](.env.example)。

## 文档

- [完整使用文档](README.zh-CN.md)：模型渠道、参数、剪贴板、任务队列与数据目录。
- [macOS 桌面版](docs/desktop.md)：安装、独立数据目录、本机打包、GitHub Actions 与 Release。
- [主题与组件约定](docs/theme.md)：daisyUI 主题变量、系统字体、组件及交互规范。
- [Qwen Image 2.1 Turbo 接入与排查](docs/qwen-image-21-turbo.md)：固定依赖、HF 模型与兼容性问题。
- [项目协作说明](AGENTS.md)：开发命令与代码协作要求。

## 开发检查

```bash
npm run build
node --test tests/js/*.test.cjs
uv run python -m unittest discover -s tests
uv lock --check
uv run python -m compileall app.py mflux_webui tests
uv run --with ruff ruff check app.py mflux_webui tests
```

生产界面继续使用 Tailwind CLI 与 esbuild 构建，无需另启 Vite 开发服务。

## 许可证

本项目使用 [ISC License](LICENSE)。
