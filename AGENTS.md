# 项目协作说明

## 产品范围

本项目是 mflux WebUI：使用 Flask、Alpine.js 与 DaisyUI 提供 Krea 2 Turbo、Z-Image Turbo 和 FLUX.2 Klein 的模型库、文生图、文+图生图和画廊。不要重新引入 Ollama、Docker 或其他推理引擎，除非用户明确要求。

## 开发与运行

- 安装依赖：`uv sync && npm install`
- 构建前端：`npm run build`
- 前台启动：`uv run python app.py`
- 后台运维：`./ops.sh start|stop|status|restart`
- 自动化检查优先使用 `npm run build`、`uv run python -m unittest discover -s tests`、`uv lock --check` 和 Python 编译。

## 文档规则

所有面向项目的文档必须使用中文。专业术语可以保留英文，或使用中英文对照。代码标识符、命令、依赖名称和第三方 API 名称可以保留英文。
