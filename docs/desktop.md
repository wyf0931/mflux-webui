# macOS 桌面应用

桌面版使用 Tauri 2 包装现有 WebUI，保留全部模型与生成功能。Python、mflux、MLX 和页面资源内置于应用中，用户无需安装开发工具或执行启动命令。只支持 Apple Silicon Mac，最低 macOS 14；不支持 Intel Mac、Windows 或 Linux 桌面版。

## 安装与首次使用

从 [GitHub Releases](https://github.com/wyf0931/mflux-webui/releases) 下载桌面版 `.dmg`，将 **mflux WebUI** 拖入「应用程序」，再打开应用。也可以下载 `.app.zip` 解压使用。

首次启动自动准备本地服务，然后进入生图页面。没有模型时进入「模型库」，从 Hugging Face 或 ModelScope 下载所需模型；下载完成后回到生图页面即可使用。安装包不含模型权重。已有完整缓存的模型可以离线生成，需要的内存与磁盘空间仍取决于模型。

外部模型仓库链接在默认浏览器打开，画廊与队列中的图像通过系统默认看图应用打开，可使用系统提供的缩放、保存与导出功能。关闭主窗口会退出应用并停止后端；正在生成或下载的任务会被中断。

预发布包如果没有 Developer ID 签名与 Apple 公证，首次打开可能被 Gatekeeper 阻止。确认来源后可在「系统设置 → 隐私与安全性」按 macOS 提供的提示允许打开。正式分发应配置签名与公证，不要求用户关闭系统安全功能。

## 数据与日志

桌面数据目录为：

```text
~/Library/Application Support/io.github.wyf0931.mflux-webui/
  db.json
  preferences.json
  images/
  uploads/
  logs/backend.log
  tmp/              后端临时文件
  matplotlib/       后端绘图库缓存
```

模型仍使用 HF / ModelScope SDK 的默认缓存目录，与源码运行方式共享已下载模型。源码模式仍使用项目内的 `data/`，桌面版不会自动迁移源码模式的画廊与任务记录。复制历史时应同时处理数据库中的图片绝对路径。

启动失败时可在启动页面重试或打开日志目录。运行中本地服务意外退出时，系统对话框提供重新启动或退出选项。应用使用随机端口，不占用源码服务的 `8090`；本地服务只监听 `127.0.0.1`，通过一次性启动握手建立会话。启动令牌不会写入访问日志。

桌面主题选择保存到 `preferences.json`，重启后保留；Web 模式继续使用浏览器的 localStorage。

## 磁盘与内存

生成期间 MLX 会把权重和激活值全部放在统一内存里，内存吃紧时 macOS 会向磁盘换页。磁盘接近写满时，不但图片与模型下载会失败，后端进程也可能在启动阶段就因为无法创建临时文件而退出。

为避免这类失败，应用做了以下处理：

- 后端临时文件固定写入数据目录下的 `tmp/`，绘图库缓存写入 `matplotlib/`，不依赖系统临时目录是否可用。
- 启动时把剩余磁盘空间写入 `logs/backend.log`；低于 2 GB 时记为警告。
- 提交生成任务和下载模型前先检查剩余空间，不足时直接返回“磁盘空间不足”提示，而不是让任务在中途崩溃。生成要求至少 2 GB 可用空间，下载要求模型体积再加 2 GB。
- 本地服务启动失败时，对话框会附带 `backend.log` 末尾几行；如果日志显示临时目录或磁盘写入失败，还会给出当前剩余空间和清理提示。

排查时可以这样确认状态：

```bash
df -h /System/Volumes/Data
sysctl vm.swapusage
```

模型缓存通常占用数十 GB，位于 `~/.cache/huggingface/hub` 与 `~/.cache/modelscope`。清理前请先在应用内确认哪些模型已不再使用，删除后重新下载会重新占用网络与磁盘。

## 本机开发与打包

构建环境需要 Apple Silicon Mac、macOS 14+、Xcode Command Line Tools、Rust、Python 3.11+、uv、Node.js 22 和 npm。继续使用 npm，沿用现有 `package-lock.json`；Bun 不作为额外依赖。

```bash
uv sync --locked --group desktop
npm ci
npm run desktop:dev
```

构建安装包（推荐一键脚本）：

```bash
./ops.sh build
```

`build` 会依次执行：清理旧产物与打包缓存 → `uv lock --check` → Python 与前端回归 → 同步桌面依赖 → `npm run desktop:build` → 安装包内置后端自检 → 收集到 `dist/desktop/`（含 `SHA256SUMS.txt`）。

常用参数：

| 参数 | 作用 |
| --- | --- |
| `--deep` | 先删除 `build/desktop-env` 与 `src-tauri/target`，从零重建（最慢，但能排除缓存影响） |
| `--no-clean` | 跳过打包前清理，直接复用缓存 |
| `--skip-tests` | 跳过 lock 校验与回归测试 |
| `--skip-smoke` | 跳过安装包内置后端自检 |

只想腾出空间、不做打包时用 `./ops.sh clean`，它默认清理以下内容，可用 `--dry-run` 先看清单：

| 路径 | 内容 |
| --- | --- |
| `build/desktop` | PyInstaller 目录式后端与打包用前端资源 |
| `build/pyinstaller`、`build/pyinstaller-cache` | PyInstaller 工作目录与配置缓存 |
| `build/matplotlib-cache` | 打包时的绘图库缓存 |
| `src-tauri/target/*/release/bundle` | 上一次的 `.app` 与 `.dmg` |
| `dist/desktop` | 本地收集的安装包与校验值 |

`clean --deep` 还会删除 `build/desktop-env`（uv 构建环境）与 `src-tauri/target`（Rust 依赖缓存），下次打包需要重新下载与编译。日常迭代保留这两项可以把打包时间从数分钟降到几十秒。

直接使用 npm 的等价流程：

```bash
npm run desktop:build
```

构建前会自动编译前端并生成 PyInstaller 目录式后端，避免每次打开应用都解压 Python 环境。产物位于 `src-tauri/target/release/bundle/macos/` 和 `src-tauri/target/release/bundle/dmg/`。使用 `--target aarch64-apple-darwin` 时，产物位于对应 target 子目录。

Tauri 外壳使用系统 WebView；安装包体积主要来自 Python 和模型推理依赖，不能把完整应用的体积等同于纯 Tauri 外壳。权重单独下载，更新应用不重复打包权重。

打包脚本在 `build/desktop-env/` 创建独立的锁定依赖环境，明确选择 macOS 14 的 wheel，并检查原生二进制的最低系统版本；避免构建机系统较新时误把仅支持新系统的 MLX 变体带入安装包。开发虚拟环境不受影响。

验证独立后端：

```bash
uv run --locked --group desktop python scripts/smoke_desktop_backend.py build/desktop/backend/mflux-backend
build/desktop/backend/mflux-backend --self-test
```

第一条验证页面、资源、API、访问会话和父进程退出；第二条实际导入全部模型并执行 Metal 运算，需要可访问 GPU 的真实 Mac 会话。GitHub 托管的 Apple Silicon runner 不提供 Metal GPU，云端冒烟检查不能替代真实 Mac 的生图验证。

## GitHub Actions 与 Release

`.github/workflows/desktop.yml` 在 Apple Silicon `macos-15` runner 构建。支持：

- 手动运行工作流，默认只上传构建产物；选中 `publish` 后发布预发布 Release。
- 推送 `desktop-v*` 标签，构建成功后自动发布该标签的预发布 Release。
- 下载文件包含 `.dmg`、`.app.zip` 与 `SHA256SUMS.txt`。

```bash
gh workflow run desktop.yml
gh run list --workflow desktop.yml
```

工作流必须先存在于默认分支才能手动触发。标签触发使用标签指向提交中的工作流。

发布前更新 `src-tauri/tauri.conf.json` 与 `src-tauri/Cargo.toml` 的版本，并使用对应的 `desktop-v<版本>` 标签。Python 包版本与桌面应用版本可以分别维护。Release 始终标记为预发布，由维护者验证下载包后再决定是否转为正式版。

## 签名与公证

在 GitHub 仓库的 Actions secrets 配置：

| Secret | 内容 |
| --- | --- |
| `APPLE_CERTIFICATE` | Developer ID Application `.p12` 证书的 Base64 内容 |
| `APPLE_CERTIFICATE_PASSWORD` | `.p12` 密码 |
| `APPLE_SIGNING_IDENTITY` | Developer ID Application 完整签名名称 |
| `APPLE_ID` | Apple 开发者账户邮箱 |
| `APPLE_PASSWORD` | Apple 应用专用密码 |
| `APPLE_TEAM_ID` | Apple Developer Team ID |

工作流将证书导入临时 keychain，PyInstaller 与 Tauri 使用相同签名身份；Tauri 使用 Apple 凭据进行公证。本机也可通过相同环境变量配置签名，但证书需提前导入本机 keychain。没有凭据仍可构建测试包，Release 会标注未签名、公证的状态。

发布采用直接下载 `.dmg` 的方式，不使用 Mac App Store 沙箱。参考 [Tauri 资源打包](https://v2.tauri.app/develop/resources/)、[macOS 签名与公证](https://v2.tauri.app/distribute/sign/macos/)、[PyInstaller macOS 打包说明](https://pyinstaller.org/en/stable/feature-notes.html)。
