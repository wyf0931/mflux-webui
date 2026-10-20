# 桌面版发布说明

macOS Apple Silicon 桌面版，使用 Tauri 2 与内置 Python/mflux 后端。

本版新增参考图提示词分析：在生图页对任意参考图点击「AI 描述」，可用本地 Qwen3-VL 生成一句英文提示词与七个结构化维度，支持复制或直接填入提示词。关注点可选填，例如“聚焦人物”“光线氛围”。视觉模型权重不含在安装包内，首次使用需执行 `hf download lmstudio-community/Qwen3-VL-8B-Instruct-MLX-4bit`，详见 `docs/image-description.md`。

同时保留上一版对 Krea 缓存与 Qwen Image 2.1 Turbo 多参考图编辑的修复；参考图支持中文文件名，保存时使用随机文件名，不改变原始图片。

- 安装 `.dmg` 后将应用拖入「应用程序」，也可以下载 `.app.zip` 解压使用。
- 无需安装 Python、Node.js、uv 或手动启动服务。
- 保留模型库、Hugging Face / ModelScope 下载、文生图、参考图生图、队列、任务日志、画廊与明暗主题。
- 首次使用请进入「模型库」下载模型；安装包不含模型权重。模型已缓存后可在本机离线生成。
- 仅支持 Apple Silicon Mac，要求 macOS 14 或更新版本；所需内存与磁盘空间取决于所选模型。
- 图片、数据库与日志保存于 `~/Library/Application Support/io.github.wyf0931.mflux-webui/`，更新应用不覆盖这些数据。

`SHA256SUMS.txt` 提供下载文件校验值。详细构建与签名说明见仓库的 `docs/desktop.md`。
