# 开发与运维

[返回项目首页](../README.md) · [文档索引](README.md)

## 环境要求

- macOS Apple Silicon（M1 及以上），支持 MLX
- Python 3.11 或更高版本，依赖由 [uv](https://docs.astral.sh/uv/) 管理
- Node.js 20 或更新版本与 npm

内存与磁盘档位、各模型的实测峰值内存和耗时见 [推荐配置](../README.zh-CN.md#推荐配置)（中文）或 [Recommended configurations](../README.md#recommended-configurations)（英文），这里不重复列出。开发时同时运行浏览器、IDE 与全量模型库，建议至少 32 GB 统一内存和 60 GB 可用磁盘。

## 安装与构建

```bash
git clone https://github.com/wyf0931/mflux-webui.git
cd mflux-webui
uv sync
npm install
npm run build
```

`uv sync` 会按 `pyproject.toml` 的固定提交安装带 Qwen Image 2.1 Turbo 支持的 mflux，不需要额外安装全局 mflux。前端构建使用 Tailwind CLI 与 esbuild，产物输出到 `mflux_webui/static/`，无需另启 Vite 开发服务。

常用脚本：

| 命令 | 作用 |
| --- | --- |
| `npm run build` | 构建 CSS 与 JS 前端资源 |
| `npm run watch:css` | 监听并重建 Tailwind 样式 |
| `npm run build:js` | 仅打包 Alpine.js 入口 |
| `npm run desktop:dev` | macOS 桌面版开发模式 |
| `npm run desktop:build` | 打包 macOS 桌面版 |

桌面版依赖单独分组，安装方式见 [macOS 桌面版](desktop.md)。

## 启动

```bash
uv run python app.py
```

打开 <http://127.0.0.1:8090>。

## 后台运行

```bash
./ops.sh start
./ops.sh status
./ops.sh status --watch
./ops.sh logs 100
./ops.sh restart
./ops.sh stop
```

日志写入 `logs/app.log`，进程 ID 写入 `logs/app.pid`。`status --watch` 每 5 秒刷新进程 PID 和运行时长；`logs` 会显示最近日志并持续跟踪，不会把监控输出写入日志文件。

## 自动化检查

```bash
npm run build
node --test tests/js/*.test.cjs
uv run python -m unittest discover -s tests
uv lock --check
uv run python -m compileall app.py mflux_webui tests
uv run --with ruff ruff check app.py mflux_webui tests
```

## 项目结构

```text
mflux_webui/       Flask 应用包、路由、服务、前端资源与模板
config/            推荐模型配置
scripts/           桌面版打包与后端自检脚本
desktop/           桌面版后端入口、前端启动页与打包配置
src-tauri/         Tauri 2 外壳
tests/             单元测试与 mock 推理测试
data/              运行时图片、历史数据与临时参考图
docs/              使用、配置、开发文档与设计记录
logs/              应用日志与 PID
app.py             兼容旧命令的开发启动入口
ops.sh             后台启停与日志监控脚本
```

## 参与贡献

欢迎提交 Issue 和 Pull Request。提交前请说明用户可见的行为变化，Bug 请提供复现步骤，并运行上面的自动化检查。协作要求与文档规范见 [项目协作说明](../AGENTS.md)。
