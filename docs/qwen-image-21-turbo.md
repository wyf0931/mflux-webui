# Qwen Image 2.1 Turbo 接入与排查

## 多参考图编辑

生成页面的高级选项提供“保持构图（单图）”与“多参考图编辑（1–10 张）”。前者仍使用 `QwenImage21` 的加噪图生图，后者使用 `QwenImage21Edit` 的原生视觉条件输入。参考图按上传顺序传给 `image_paths`，提示词支持“图一”“图2”及 `<image1>` 等编号。

编辑模式需要完整的 transformer、VAE、包含视觉编码器的 text_encoder、processor 与组件配置。当前目录中的完整 q4 仓库包含这些组件；仅文本导出不支持编辑。宽高必须为 32 的倍数，至少 2 步，默认 8 步。编辑和普通生成使用不同模型缓存键，切换时卸载同仓库的另一模式，避免误用模型实例。

## 依赖版本

项目使用 mflux 0.22.0，并通过 `tool.uv.sources` 固定到
`602b26d242eb7ea9df2a765162a7f35c45c7a143`。
该提交合并了上游 PR [#859](https://github.com/mflux-community/mflux/pull/859)，补齐 Turbo 专用模型配置、
采样曲线，以及社区保存格式中 VAE、文本编码器的兼容处理。单独安装 PyPI 的 0.22.0 不包含这些改动。

在项目目录运行：

```bash
uv sync
npm run build
```

升级时需同时更新 `pyproject.toml` 与 `uv.lock`，并核对 Krea 2、Z-Image、FLUX.2 Klein 原有加载与生成接口。
不要直接修改 `.venv` 中的第三方源码，也不要依赖全局 mflux 的安装版本。

## 模型与运行参数

- HF 仓库：[mflux-community/qwen-image-2-1-turbo-mflux-q4](https://huggingface.co/mflux-community/qwen-image-2-1-turbo-mflux-q4)。
- Python 加载器：`QwenImage21`，使用 `ModelConfig.qwen_image_21_turbo()`。
- 默认参数：8 步、guidance 1.0、`linear` 调度参数。上游根据 Turbo 配置自动选择专用的固定 sigma 曲线。
- 建议从 1024×1024 或相近像素面积开始。Q4 仓库已包含 VAE、Transformer、文本编码器和分词器。
- 当前 WebUI 支持文生图、保留构图的单参考图图生图及种子复用。
- Turbo 不使用 CFG，高级选项固定引导系数为 1.0；负面提示词与普通模型的采样器选项不作为可调控件提供。
- 上游步复用缓存对不足 10 个实际去噪步骤的运行不生效，因此默认 8 步界面不提供缓存加速开关。

上游使用说明见 [mflux Qwen Image 2.1 文档](https://github.com/mflux-community/mflux/blob/main/src/mflux/models/qwen21/README.md)。

## 下载与缓存

可从 WebUI 模型库下载，也可使用 HF CLI：

```bash
hf download mflux-community/qwen-image-2-1-turbo-mflux-q4
```

默认缓存位于 `~/.cache/huggingface/hub`，或由 Hugging Face 环境配置指定。
同一仓库的已缓存文件可复用，重新同步仓库会下载缺失文件。

核对缓存时应检查快照目录内文件是否可读，以及是否与远端文件大小、版本一致。
LFS 文件的本地 blob 文件名可能使用 SHA-256，不能仅按 Git blob ID 判断权重是否缺失。

## 常见问题

### VAE checkpoint mismatch，unexpected 包含 time_conv

例如错误包含 `decoder.up_blocks.0.upsampler.time_conv.weight`，且 `missing=[]`。
这表示加载器不兼容 checkpoint 中的额外时间卷积参数，不能据此判断缺少 VAE 模型。
上游 PR #859 已处理文本生图不使用的这部分参数。

确认项目已执行 `uv sync`，并使用 Turbo 专用配置；然后在任务队列空闲时运行：

```bash
./ops.sh restart
```

### 升级后仍运行旧模型代码

Python 进程会保留已导入的模块和已缓存的模型。完成依赖与代码更新后，应在队列空闲时重启服务。
不要中断正在运行的生成任务。

### 查看失败日志

队列“结果”列提供“查看日志”文字按钮。点击后按需读取任务详情并在原生对话框内展示。
更新后产生的失败任务包含完整堆栈；较早的任务可能只保存完整错误文本。
应用级日志仍可通过 `./ops.sh logs 100` 查看。

任务详情接口 `GET /api/generate/tasks/<task_id>` 返回 `modelName` 和 `logs`；
任务列表接口返回 `modelName`，不返回完整 `logs`，避免轮询时反复传输堆栈。
