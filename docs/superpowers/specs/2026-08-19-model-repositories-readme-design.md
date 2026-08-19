# 模型渠道配置与 README 改造设计

## 目标

将模型目录从 Python 硬编码迁移为启动时加载的 JSON 配置，同时支持 Hugging Face 与 ModelScope 两个模型渠道；通过 `MODEL_REPO` 控制启用渠道，默认启用 `all`。模型页优先展示已安装模型，推荐模型按渠道切换。README 以英文为默认入口，并保留中文版本。

## 方案

### 模型配置

新增 `config/models.json`。每个模型条目包含展示信息、mflux backend 能力参数，以及 `huggingface`、`modelscope` 两个可选仓库 ID。配置模块在导入时读取项目配置，缺失、格式错误或重复模型键时给出明确异常；模型能力判断只基于配置条目及现有兼容家族兜底逻辑。

API 返回渠道化条目，包含 `source`、`repoId`、`repoUrl` 与展示字段。同一模型在 `all` 模式下可同时出现在两个渠道，但下载任务使用 `source/repoId` 作为唯一键。

### 下载与缓存

新增模型仓库适配层：

- Hugging Face 使用 `huggingface_hub.HfApi` 与 `hf_hub_download`。
- ModelScope 使用 `modelscope.hub.snapshot_download` 及 SDK 默认缓存目录。
- 不设置自定义缓存目录，不搬运文件，不限制 SDK 默认路径。

缓存列表分别扫描两套默认缓存，统一返回 `source` 字段。网络元数据仅在对应渠道可用时读取，失败不影响本地缓存展示。

`MODEL_REPO` 读取 `all`、`huggingface`、`modelscope` 三个值；空值默认 `all`，非法值回退 `all` 并记录警告。该开关同时影响推荐目录和下载入口，不影响已经存在的本地缓存展示。

### 页面

模型页的顺序调整为：下载任务、已安装模型、推荐模型。推荐区使用 DaisyUI tabs，Tab 内容由当前渠道过滤；每张卡显示对应仓库链接和下载操作。Alpine 状态保持单一 `source` 选择，刷新时并行加载缓存、目录和任务。

### 文档与验证

`README.md` 使用英文，顶部链接到 `README.zh-CN.md`；两个 README 都包含项目简介、功能、截图、安装、配置、使用、开发检查、贡献和许可证。实现完成后启动应用并重新截取生图、画廊、模型页截图，覆盖 `docs/images/` 中的旧图。

## 错误处理与兼容性

- 缺少某个渠道 SDK 时，应用启动不应因未启用该渠道而失败；配置为该渠道时 API 返回可读错误。
- 配置中的渠道 ID 为空时不生成该渠道卡片。
- 下载任务以 `source:repoId` 区分，避免两个渠道同名或同仓库 ID 互相覆盖。
- 现有 mflux 生成请求继续使用 `modelId`，由目录中的 repo ID 解析能力；对同一模型的不同渠道 ID 均映射到相同 backend。

## 验证

运行 Python 单元测试、`uv lock --check`、前端构建、Python 编译；启动开发服务后通过浏览器检查模型页顺序、两个 Tab、下载链接和 README 截图内容。
