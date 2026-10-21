# 项目协作说明

## 产品范围

本项目是 mflux WebUI：使用 Flask、Alpine.js 与 DaisyUI 提供 Qwen Image 2.1 Turbo、Krea 2 Turbo、Z-Image Turbo 和 FLUX.2 Klein 的模型库、文生图、文+图生图、参考图提示词分析（本地 Qwen3-VL）和画廊。不要重新引入 Ollama、Docker 或其他推理引擎，除非用户明确要求。

## 开发与运行

- 安装依赖：`uv sync && npm install`
- 构建前端：`npm run build`
- 前端回归：`node --test tests/js/*.test.cjs`
- 前台启动：`uv run python app.py`
- macOS 桌面开发：`uv sync --locked --group desktop && npm ci && npm run desktop:dev`
- macOS 桌面打包：`./ops.sh build`（清理 → 回归 → 打包 → 自检 → 汇总到 `dist/desktop`），参数与环境说明见 `docs/desktop.md`；只清理缓存用 `./ops.sh clean [--deep] [--dry-run]`
- 后台运维：`./ops.sh start|stop|status|restart`
- 日志与监控：`./ops.sh logs [行数]`、`./ops.sh status --watch`
- 自动化检查优先使用 `npm run build`、`uv run python -m unittest discover -s tests`、`uv lock --check` 和 Python 编译。
- 静态检查可使用 `uv run --with ruff ruff check app.py mflux_webui tests`。

## 文档规则

所有面向项目的文档必须使用中文。专业术语可以保留英文，或使用中英文对照。代码标识符、命令、依赖名称和第三方 API 名称可以保留英文。

README 采用英文为主、中文为辅：`README.md` 为英文版，`README.zh-CN.md` 为中文镜像，两者结构一致，修改时同步更新并保留顶部语言切换链接。`docs/` 下的详细文档仍使用中文。

`README.md` 只保留项目定位、亮点、截图、环境与推荐配置、快速开始、依赖与许可证表、文档导航和开发检查；详细的使用、配置、开发说明放在 `docs/`，文档导航见 `docs/README.md`，新增文档需要在其中登记。不要写入个人本地环境（例如本机 HTTP 代理、私有路径、个人镜像地址）。

环境与性能数据必须是可复现的实测或明确标注的估算：注明测试机器、分辨率与步数，不要写“跑起来很快”这类无依据描述。

## 前端与模型适配

- 统一使用 daisyUI 5 组件、Tailwind CSS 4 布局和 Alpine.js 交互；主题与组件规范见 `docs/theme.md`。
- 保留系统中文字体回退，不依赖 Google Fonts 或专有字体。
- mflux 由 `pyproject.toml` 与 `uv.lock` 固定到包含 Qwen Turbo 支持的上游提交，安装使用 `uv sync`；升级必须核对原有模型的加载和生成 API。
- 生图与队列中的显示名称来自模型目录，不直接以长仓库 ID 作为主文案。
- 失败结果通过任务日志弹窗展示；列表接口不返回完整堆栈。
