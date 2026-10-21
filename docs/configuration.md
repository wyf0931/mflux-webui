# 模型与配置

[返回项目首页](../README.md) · [文档索引](README.md)

## 模型目录

推荐模型配置位于 [`config/models.json`](../config/models.json)，应用启动时加载。每个条目可以分别配置 Hugging Face ID 和 ModelScope ID，并按模型能力声明默认步数、引导系数与调度器。

当前包含的模型：

| 模型 | 量化 | 大小 | 默认步数 | 引导系数 |
| --- | --- | --- | --- | --- |
| Qwen Image 2.1 Turbo | q4 | 约 10.0 GB | 8 | 1.0（固定） |
| Krea 2 Turbo | q4 | 约 14.7 GB | 8 | 1.0 |
| Krea 2 Turbo | q8 | 约 20.7 GB | 8 | 1.0 |
| Z-Image Turbo | 4-bit | 约 5.5 GB | 4 | 不使用 |
| FLUX.2 Klein 4B | 4-bit | 约 4.3 GB | 4 | 1.0 |
| FLUX.2 Klein 9B | q4 | 约 8.9 GB | 4 | 1.0 |

下载使用 `huggingface_hub` 与 `modelscope` 自己管理的默认缓存目录，应用不会搬运或覆盖缓存文件。预留磁盘空间时按模型大小并考虑统一内存占用。

## 下载渠道

通过 `MODEL_REPO` 控制启用的推荐与下载渠道：

| 值 | 启用渠道 |
| --- | --- |
| `all` | Hugging Face 与 ModelScope，默认值 |
| `huggingface` | 仅 Hugging Face |
| `modelscope` | 仅 ModelScope |

个别模型只在其中一个渠道提供，配置中缺失的渠道不会出现在模型库对应 Tab 中。

## 环境变量

复制环境示例文件并按需修改：

```bash
cp .env.example .env
```

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `MODEL_REPO` | `all` | 启用的模型下载渠道，见上表。 |
| `MFLUX_MODEL_IDLE_TTL_SECONDS` | `300` | 模型空闲多久后自动卸载，单位为秒。 |
| `MFLUX_QUEUE_MAX_SIZE` | `10` | 最多等待的生成任务数，不包含正在推理的任务。 |
| `MFLUX_DATA_DIR` | `data/` | 覆盖数据库、图片与参考图的保存目录；桌面版由应用自动设置。 |
| `MFLUX_VLM_MODEL` | `lmstudio-community/Qwen3-VL-8B-Instruct-MLX-4bit` | 参考图提示词使用的本地视觉模型。 |

完整清单与注释见 [`.env.example`](../.env.example)。

## 数据位置

| 内容 | 位置 |
| --- | --- |
| 生成图片 | `data/images/` |
| 生成历史、队列记录及任务日志 | `data/db.json` |
| 临时参考图 | `data/uploads/` |
| 应用日志 | `logs/app.log` |
| 模型权重 | SDK 默认缓存目录 |

桌面版使用独立的 Application Support 目录，见 [macOS 桌面版](desktop.md)。

## 依赖版本

项目使用 mflux 0.22.0，并通过 `pyproject.toml` 的 `tool.uv.sources` 固定上游合并提交 `602b26d242eb7ea9df2a765162a7f35c45c7a143`（对应 PR [#859](https://github.com/mflux-community/mflux/pull/859)），补齐 Qwen Image 2.1 Turbo 的模型配置、采样曲线与社区保存格式兼容。PyPI 的 0.22.0 不包含这些改动，因此统一使用 `uv sync` 安装，不要单独安装全局 mflux。

升级 mflux 前需核对原有模型的加载与生成 API，详见 [Qwen Image 2.1 Turbo 接入](qwen-image-21-turbo.md)。
