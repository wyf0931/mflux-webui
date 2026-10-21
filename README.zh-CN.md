# mflux WebUI

[English](README.md) | **中文**

在 Apple Silicon Mac 上本地生成图片的 WebUI：Flask 后端、Alpine.js 与 daisyUI 5 前端，推理由 [mflux](https://github.com/mflux-community/mflux) 与 MLX 驱动，模型权重与提示词都不离开本机。

支持文生图、参考图生图、Qwen 多参考图编辑、模型缓存管理、异步队列、任务日志与历史画廊。另提供 [macOS 桌面版](docs/desktop.md)（Tauri 2），安装后直接打开，无需安装 Python 或 Node.js，首次使用时下载模型。安装包见 [GitHub Releases](https://github.com/wyf0931/mflux-webui/releases)。

## 功能亮点

- **模型**：Qwen Image 2.1 Turbo、Krea 2 Turbo、Z-Image Turbo、FLUX.2 Klein，提供 q4 / q8 / 4-bit 量化版本。
- **参考图**：本地选择或 ⌘V / Ctrl+V 粘贴，自动预览，可替换或移除，生成时才上传。
- **Qwen 多参考图编辑**：切换生成方式后按顺序添加 1–10 张图片，用“图一”“图二”或 `<image1>`、`<image2>` 指定引用；原单图保持构图模式继续可用。
- **AI 描述页**：导航中的独立页面，用本地 Qwen3-VL 把任意图片转成一句提示词与七项结构化维度，支持复制或一键带进生图页。
- **按模型适配参数**：步数与引导系数跟随所选模型；Qwen Turbo 默认 8 步、引导系数固定为 1.0。
- **队列**：展示状态、模型别名、耗时与结果，失败时通过日志弹窗查看完整堆栈。
- **界面**：daisyUI 的 Rausch 浅色主题与深色扩展，中文字体回退与手机布局。
- **渠道**：Hugging Face 与 ModelScope，沿用各 SDK 的默认模型缓存目录。

## 界面截图

| 生图 | 画廊 | 模型库 |
| --- | --- | --- |
| ![生图页面](docs/images/generate.png) | ![画廊页面](docs/images/gallery.png) | ![模型库页面](docs/images/models.png) |

| 生成队列 | 完整日志弹窗 |
| --- | --- |
| ![生成队列](docs/images/queue.png) | ![完整日志弹窗](docs/images/task-logs.png) |

截图使用示例任务，不包含用户的生成历史。

## 环境要求

需要支持 MLX 的 Apple Silicon Mac（M1 及以上）。不支持 Intel Mac、Windows 与 Linux。开发另需 Python 3.11+、Node.js 20+ 与 npm、[uv](https://docs.astral.sh/uv/)；桌面版用户不需要这些工具。

真正的瓶颈是统一内存：采样期间 MLX 需要同时持有全部权重和激活值，1024×1024 下的峰值约为模型磁盘占用的两倍。生成前请关闭其他占用内存较多的应用，并为 macOS 本身预留数 GB。

### 推荐配置

| 档位 | 硬件 | 可用磁盘 | 可流畅运行的场景 |
| --- | --- | --- | --- |
| 最低 | M1/M2，16 GB 统一内存 | 30 GB | FLUX.2 Klein 4B · 4-bit 在 1024×1024（峰值约 10 GB）；Z-Image Turbo 4-bit 在 768×768 |
| 推荐 | M2 Pro / M3 / M4，32 GB | 60 GB | Qwen Image 2.1 Turbo · q4 在 1024×1024（峰值约 20 GB）、FLUX.2 Klein 9B · q4 在 1024×1024 |
| 舒适 | M4 Pro 及以上，48 GB | 120 GB | Krea 2 Turbo · q4 在 1024×1024（峰值约 31 GB），并可同时使用参考图提示词分析 |
| 重度 | M4 Max 及以上，64 GB | 200 GB | Krea 2 Turbo · q8 在 1024×1024 或更大尺寸（峰值约 42 GB）、大尺寸多参考图编辑 |

磁盘预算：推荐模型单个 4.3–20.7 GB（六个模型合计约 64 GB），可选的 Qwen3-VL 8B 4-bit 权重 5.8 GB，Python 环境约 3 GB。

### 实测性能

测试环境：MacBook Pro（Apple M4 Pro，14 核，48 GB 统一内存），macOS 26.5.2，1024×1024，8 步 Turbo 采样。

| 模型 | 权重 | MLX 峰值内存 | 耗时 |
| --- | --- | --- | --- |
| Qwen Image 2.1 Turbo · q4 | 10.0 GB | 20.5 GB | 93 秒 |
| Krea 2 Turbo · q4 | 14.7 GB | 31.3 GB | 185 秒 |
| Qwen Image 2.1 Turbo · q4（512×512） | 10.0 GB | 14.3 GB | 22 秒 |

未加载模型时，Flask 后端常驻内存约 60 MB。上表未列出的模型在 1024×1024 下可按权重体积的约 2.1 倍估算峰值，512×512 下再减半。

## 快速开始

```bash
git clone https://github.com/wyf0931/mflux-webui.git
cd mflux-webui
uv sync
npm install
npm run build
uv run python app.py
```

打开 <http://127.0.0.1:8090>，在「模型库」下载模型后即可生成。`uv sync` 会把 mflux 固定到包含 Qwen Image 2.1 Turbo 支持的上游提交，请勿另行安装全局 mflux。

后台运行使用 `./ops.sh start|stop|status|logs`，详见 [开发与运维](docs/development.md)。

## 依赖与许可证

主要 Python 依赖，以及环境中实际安装的关键间接依赖：

| 依赖 | 版本 | 许可证 | 用途 |
| --- | --- | --- | --- |
| [mflux](https://github.com/mflux-community/mflux) | 0.22.0（`602b26d`） | MIT | 模型加载、调度器与推理 |
| [MLX](https://github.com/ml-explore/mlx) | 0.32.3 | MIT | Apple Silicon 数组计算框架 |
| [MLX-LM](https://github.com/ml-explore/mlx-lm) | 0.32.2 | MIT | 语言模型工具 |
| [mlx-vlm](https://github.com/Blaizzy/mlx-vlm) | 0.6.3 | MIT | 本地 Qwen3-VL 参考图提示词分析 |
| [Flask](https://github.com/pallets/flask) | 3.1.2 | BSD-3-Clause | HTTP 服务与页面渲染 |
| [huggingface_hub](https://github.com/huggingface/huggingface_hub) | 1.8.0 | Apache-2.0 | Hugging Face 缓存与下载 |
| [ModelScope](https://github.com/modelscope/modelscope) | 1.39.1 | Apache-2.0 | ModelScope 缓存与下载 |
| [Transformers](https://github.com/huggingface/transformers) | 5.15.1 | Apache-2.0 | 分词器、处理器与视觉模型配置 |
| [PyTorch](https://github.com/pytorch/pytorch) | 2.14.1 | BSD-3-Clause（复合许可） | 由模型依赖链引入 |
| [OpenCV Python](https://github.com/opencv/opencv-python) | 4.13.0.92 | Apache-2.0 | mlx-vlm 所需的图像处理 |
| [safetensors](https://github.com/huggingface/safetensors) | 0.8.0 | Apache-2.0 | 权重文件格式 |
| [tokenizers](https://github.com/huggingface/tokenizers) | 0.22.2 | Apache-2.0 | 文本分词 |
| [NumPy](https://github.com/numpy/numpy) | 2.4.4 | BSD-3-Clause | 数组运算 |
| [SciPy](https://github.com/scipy/scipy) | 1.17.1 | BSD-3-Clause | MLX 依赖链中的重采样工具 |
| [Pillow](https://github.com/python-pillow/Pillow) | 12.3.0 | MIT-CMU | 图片编解码 |
| [python-dotenv](https://github.com/theskumar/python-dotenv) | 1.2.3 | BSD-3-Clause | 读取 `.env` |
| [TinyDB](https://github.com/msiemens/tinydb) | 4.8.2 | MIT | 历史记录与队列存储 |
| [socksio](https://github.com/sethmlarson/socksio) | 1.0.0 | MIT | HTTP 客户端的 SOCKS 代理支持 |

前端与桌面工具链：

| 依赖 | 版本 | 许可证 | 用途 |
| --- | --- | --- | --- |
| [Alpine.js](https://github.com/alpinejs/alpine) | 3.16.2 | MIT | 页面交互 |
| [Tailwind CSS](https://github.com/tailwindlabs/tailwindcss) | 4.3.3 | MIT | 布局工具类 |
| [daisyUI](https://github.com/saadeghi/daisyui) | 5.7.17 | MIT | 组件库与主题 |
| [esbuild](https://github.com/evanw/esbuild) | 0.28.2 | MIT | JavaScript 打包 |
| [Tauri](https://github.com/tauri-apps/tauri) | 2.x | MIT OR Apache-2.0 | 桌面外壳（Rust） |
| [PyInstaller](https://github.com/pyinstaller/pyinstaller) | 6.22.3 | GPL-2.0-or-later（含 bootloader exception） | 桌面版后端打包，仅构建期使用 |

说明：

- 项目不使用也不下载 LaMa 等修补（inpainting）模型，生成全部通过上表中的 mflux 模型系列完成。
- 模型权重不随项目分发，各自在 Hugging Face 或 ModelScope 上遵循对应许可证；商用前请阅读模型卡。
- 项目本身使用 [ISC License](LICENSE)。

## 文档

| 文档 | 内容 |
| --- | --- |
| [文档索引](docs/README.md) | 全部文档的分类导航 |
| [使用指南](docs/usage.md) | 文生图、图生图、Qwen 多参考图编辑、队列与任务日志 |
| [模型与配置](docs/configuration.md) | 模型目录、下载渠道、环境变量、数据位置 |
| [AI 描述](docs/image-description.md) | 独立描述页的使用流程、前置条件、输出结构与接口 |
| [macOS 桌面版](docs/desktop.md) | 安装、独立数据目录、本机打包、GitHub Actions 与 Release |
| [开发与运维](docs/development.md) | 安装、构建、后台运行、自动化检查、项目结构 |
| [主题与组件约定](docs/theme.md) | daisyUI 主题变量、系统字体、组件与交互规范 |
| [Qwen Image 2.1 Turbo 接入](docs/qwen-image-21-turbo.md) | 固定依赖、模型要求与兼容性排查 |
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
