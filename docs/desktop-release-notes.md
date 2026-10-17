macOS Apple Silicon 桌面版，使用 Tauri 2 与内置 Python/mflux 后端。

本版修复 Krea 已有完整分片缓存仍报缺少 `turbo.safetensors` 的问题，并为 Qwen Image 2.1 Turbo 增加原生多参考图编辑：高级选项中切换模式后可添加 1–10 张图片，通过“图一、图二”或 `<image1>`、`<image2>` 引用。

- 安装 `.dmg` 后将应用拖入「应用程序」，也可以下载 `.app.zip` 解压使用。
- 无需安装 Python、Node.js、uv 或手动启动服务。
- 保留模型库、Hugging Face / ModelScope 下载、文生图、参考图生图、队列、任务日志、画廊与明暗主题。
- 首次使用请进入「模型库」下载模型；安装包不含模型权重。模型已缓存后可在本机离线生成。
- 仅支持 Apple Silicon Mac，要求 macOS 14 或更新版本；所需内存与磁盘空间取决于所选模型。
- 图片、数据库与日志保存于 `~/Library/Application Support/io.github.wyf0931.mflux-webui/`，更新应用不覆盖这些数据。

`SHA256SUMS.txt` 提供下载文件校验值。详细构建与签名说明见仓库的 `docs/desktop.md`。
