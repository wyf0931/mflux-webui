# 项目协作说明

## 产品范围

本项目是 mflux WebUI：使用 Flask、Alpine.js 与 DaisyUI 提供 Qwen Image 2.1 Turbo、Krea 2 Turbo、Z-Image Turbo 和 FLUX.2 Klein 的模型库、文生图、文+图生图、图生文（本地 Qwen3-VL 把图片转提示词）和画廊。不要重新引入 Ollama、Docker 或其他推理引擎，除非用户明确要求。

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

## 发布桌面版

发版由 Coding Agent 按下面的顺序执行。CI、签名与公证的机制细节见 `docs/desktop.md`，这里只列必须做的事。

1. **确认基线**：要发布的内容已合入 `main`，工作区干净，且 `npm run build`、`uv lock --check`、`uv run python -m unittest discover -s tests`、`node --test tests/js/*.test.cjs` 全部通过。
2. **提升版本号**：同时修改 `src-tauri/tauri.conf.json` 与 `src-tauri/Cargo.toml` 的 `version`，两处保持一致（`src-tauri/Cargo.lock` 在下次构建时自动更新，不要手改）。DMG 文件名、Release 标题与标签都由 `tauri.conf.json` 的版本推导；`package.json` 与 `pyproject.toml` 的版本不参与桌面版发布，不要顺手改。当前处于 `0.1.x`：修 bug 升 patch，新增用户可见功能升 minor。
3. **改写发布说明**：`docs/desktop-release-notes.md` 会被 CI 直接当作 Release 正文。只写本版用户可见的变化（新增、修复、行为变更、已知限制），保留安装步骤、系统要求（Apple Silicon、macOS 14+）、数据目录说明和“安装包不含模型权重”；用中文，面向用户，不写内部实现细节与工单号。未签名提示由 CI 自动追加，不要手写。
4. **本地验证**：运行 `./ops.sh build`（默认先清理旧产物，再跑回归、打包并自检安装包内置后端），确认 `dist/desktop/` 中的文件名带新版本号，`SHA256SUMS.txt` 有 `.dmg` 与 `.app.zip` 两条记录。
5. **同一次提交完成并打标签**：版本号、发布说明必须在标签指向的提交里，因为 CI 使用该提交的内容构建。

   ```bash
   git add -A && git commit -m "chore: 发布桌面版 <版本>"
   git tag desktop-v<版本>
   git push origin main --tags
   ```

   推送 `desktop-v*` 标签会触发 `.github/workflows/desktop.yml`，构建成功后自动发布该标签的预发布 Release；也可以 `gh workflow run desktop.yml -f publish=true` 手动触发。
6. **发布后核对**：用 `gh release view desktop-v<版本>` 确认标题、正文和 `.dmg`、`.app.zip`、`SHA256SUMS.txt` 三个附件齐全，标签指向的提交与本地一致；下载安装包做一次安装与首启检查。
7. **不要做的事**：不提交 `dist/`、`build/`、`src-tauri/target/` 等构建产物；不手动上传或覆盖 Release 附件；不自行把手动 Release 改为正式版，Release 默认为预发布，转正式版需要用户明确确认。

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
