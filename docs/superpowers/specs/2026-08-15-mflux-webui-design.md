# mflux WebUI 精简改造设计

## 目标

将项目收敛为专注于 mflux 的本地图像生成 WebUI。应用使用 Flask 实现，提供生成、画廊、设置和本地 Hugging Face（HF）模型缓存查看能力；不再支持 Ollama 或 Docker 部署。

## 运行与依赖

Python 依赖通过 uv 管理，mflux 固定为 `0.18.1` 的主依赖，而非可选 extra。项目保留 `uv run python app.py` 作为最短启动命令，并提供 `ops.sh start|stop|status|restart`：后台进程的 PID 写入 `logs/app.pid`，标准输出和错误输出写入 `logs/app.log`。

Dockerfile、Docker 忽略规则及所有 Ollama 配置、依赖、文档和界面入口都会删除。

## 应用边界

应用不再保留多引擎抽象、引擎选择器或 Ollama HTTP 客户端。mflux 生成服务通过公开的 `mflux-generate` 命令工作：传入模型、提示词、尺寸、随机种子、步数、引导系数、量化位数和输出路径；命令失败或没有产出图片时返回明确错误。

模型列表仅使用 mflux 0.18.1 支持的标识：`schnell`、`dev`、`krea-dev` 和 `qwen`。图片使用微秒级时间戳命名，避免并发请求覆盖文件。历史记录保留模型、尺寸、提示词、耗时和 mflux 参数。

## 本地 HF 模型缓存

通过 `huggingface_hub.scan_cache_dir()` 只读扫描本机 Hugging Face 缓存。新增模型页面和 JSON API，展示每个缓存仓库的名称、revision、占用大小、缓存路径和文件数量。扫描失败、缓存不存在或版本元数据损坏时，页面显示可理解的空状态或错误信息，不联网也不下载模型。

## 数据与界面

设置只保留 mflux 量化位数。首页固定为 mflux 生成表单；画廊去除引擎字段和按引擎筛选，保留模型筛选、预览和删除。产品名称统一为 mflux WebUI。

## 质量要求

新增 `AGENTS.md`，规定项目范围、开发运行方式，以及所有文档必须使用中文（专业术语可保留英文或中英文对照）。README 改为中文的 mflux-only 使用说明。

使用标准库 `unittest` 覆盖 mflux CLI 参数构造、命令错误、缺失输出文件和 HF 缓存扫描。完成锁文件校验、Python 编译和 Flask 路由 smoke test。真实生成不纳入自动化测试，因为它依赖本机模型、缓存和兼容硬件。
