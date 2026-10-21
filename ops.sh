#!/usr/bin/env sh
set -eu

# CDPATH= 用于避免继承调用者的 CDPATH 输出。
# shellcheck disable=SC1007
ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PID_FILE="$ROOT_DIR/logs/app.pid"
LOG_FILE="$ROOT_DIR/logs/app.log"

is_running() {
    [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null
}

port_owner() {
    lsof -tiTCP:8090 -sTCP:LISTEN 2>/dev/null | head -n 1
}

port_is_in_use() {
    PORT_PID=$(port_owner || true)
    [ -n "$PORT_PID" ] && return 0
    command -v curl >/dev/null 2>&1 && curl -fsS --max-time 1 http://127.0.0.1:8090/ >/dev/null 2>&1
}

start() {
    if is_running; then echo "mflux WebUI 已运行（PID $(cat "$PID_FILE")）"; return; fi
    mkdir -p "$ROOT_DIR/logs"
    rm -f "$PID_FILE"
    if port_is_in_use; then
        PORT_PID=$(port_owner || true)
        echo "启动失败：端口 8090 已被现有服务占用${PORT_PID:+（PID $PORT_PID）}"
        exit 1
    fi
    if [ -f "$ROOT_DIR/package.json" ]; then
        echo "构建前端资源…"
        (cd "$ROOT_DIR" && npm run build >/dev/null)
    fi
    (
        cd "$ROOT_DIR"
        nohup uv run python app.py >>"$LOG_FILE" 2>&1 &
        echo $! >"$PID_FILE"
    )
    sleep 1
    if is_running || port_is_in_use; then echo "mflux WebUI 已启动：http://127.0.0.1:8090（PID $(cat "$PID_FILE")）"; else echo "启动失败，请查看 $LOG_FILE"; exit 1; fi
}

stop() {
    if is_running; then kill "$(cat "$PID_FILE")"; rm -f "$PID_FILE"; echo "mflux WebUI 已停止"; else rm -f "$PID_FILE"; echo "mflux WebUI 未运行"; fi
}

status() { if is_running; then echo "mflux WebUI 正在运行（PID $(cat "$PID_FILE")）"; else echo "mflux WebUI 未运行"; return 1; fi; }

logs() {
    lines=${1:-100}
    mkdir -p "$ROOT_DIR/logs"
    touch "$LOG_FILE"
    echo "正在跟踪 ${LOG_FILE}（最近 $lines 行，按 Ctrl-C 退出）"
    tail -n "$lines" -f "$LOG_FILE"
}

status_snapshot() {
    if ! is_running; then
        echo "mflux WebUI 未运行"
        return 1
    fi
    APP_PID=$(cat "$PID_FILE")
    app_elapsed=$(ps -p "$APP_PID" -o etime= 2>/dev/null | sed 's/^ *//')
    printf 'mflux WebUI 运行中  PID=%s  uptime=%s\n' "$APP_PID" "${app_elapsed:-n/a}"
    printf '提示：使用 "%s status --watch" 每 5 秒刷新进程状态。\n' "$0"
}

status_watch() {
    while :; do
        clear 2>/dev/null || true
        printf 'mflux WebUI process monitor  %s\n\n' "$(date '+%Y-%m-%d %H:%M:%S')"
        status_snapshot || return 1
        sleep 5
    done
}

# ---------- 桌面版打包 ----------

DESKTOP_BUILD_CACHES='build/desktop build/pyinstaller build/pyinstaller-cache build/matplotlib-cache'
DESKTOP_BUNDLE_DIRS='src-tauri/target/release/bundle src-tauri/target/aarch64-apple-darwin/release/bundle'
DESKTOP_DEEP_CACHES='build/desktop-env src-tauri/target'
DESKTOP_ARTIFACTS='dist/desktop'

human_kb() {
    awk -v k="$1" 'BEGIN { if (k >= 1048576) printf "%.1f GB", k/1048576; else printf "%.0f MB", k/1024 }'
}

# 列出应该清理的路径（绝对路径，一行一个）
desktop_clean_paths() {
    deep="$1"
    for relative in $DESKTOP_BUILD_CACHES $DESKTOP_BUNDLE_DIRS $DESKTOP_ARTIFACTS; do
        printf '%s\n' "$ROOT_DIR/$relative"
    done
    if [ "$deep" = yes ]; then
        for relative in $DESKTOP_DEEP_CACHES; do
            printf '%s\n' "$ROOT_DIR/$relative"
        done
    fi
}

clean_desktop() {
    deep=no
    dry_run=no
    for arg in "$@"; do
        case "$arg" in
            --deep) deep=yes ;;
            --dry-run|--dry) dry_run=yes ;;
            *) echo "未知的 clean 参数：$arg"; exit 2 ;;
        esac
    done
    if [ "$dry_run" = yes ]; then
        echo "将要清理（未实际删除）："
    else
        echo "清理打包缓存与旧产物…"
    fi
    list_file=$(mktemp "${TMPDIR:-/tmp}/mflux-clean.XXXXXX")
    desktop_clean_paths "$deep" >"$list_file"
    removed=0
    total_kb=0
    while IFS= read -r path; do
        [ -e "$path" ] || continue
        size=$(du -sk "$path" 2>/dev/null | awk '{print $1}')
        [ -n "$size" ] || size=0
        removed=$((removed + 1))
        total_kb=$((total_kb + size))
        printf '  - %s (%s)\n' "${path#"$ROOT_DIR"/}" "$(human_kb "$size")"
        [ "$dry_run" = yes ] || rm -rf "$path"
    done <"$list_file"
    rm -f "$list_file"
    if [ "$removed" -eq 0 ]; then
        echo "  没有需要清理的内容。"
    elif [ "$dry_run" = yes ]; then
        printf '共 %s 项，可释放约 %s。\n' "$removed" "$(human_kb "$total_kb")"
    else
        printf '已清理 %s 项，释放约 %s。\n' "$removed" "$(human_kb "$total_kb")"
    fi
    if [ "$deep" = yes ]; then
        echo "提示：--deep 会在下次打包时重建 uv 环境与 Rust 依赖缓存，耗时显著增加。"
    fi
}

desktop_preflight() {
    if [ "$(uname -s)" != Darwin ] || [ "$(uname -m)" != arm64 ]; then
        echo "打包失败：桌面版只能在 Apple Silicon Mac（arm64）上构建。"; exit 1
    fi
    for tool in node npm uv cargo ditto shasum; do
        if ! command -v "$tool" >/dev/null 2>&1; then
            echo "打包失败：缺少 $tool。"
            [ "$tool" = cargo ] && echo "请先安装 Rust：https://rustup.rs"
            exit 1
        fi
    done
    if ! xcode-select -p >/dev/null 2>&1; then
        echo "打包失败：缺少 Xcode Command Line Tools，请执行 xcode-select --install。"
        exit 1
    fi
}

desktop_bundle_dir() {
    for relative in $DESKTOP_BUNDLE_DIRS; do
        if [ -d "$ROOT_DIR/$relative/macos" ]; then
            printf '%s\n' "$ROOT_DIR/$relative"
            return 0
        fi
    done
    return 1
}

build_desktop() {
    deep=no
    do_clean=yes
    run_tests=yes
    run_smoke=yes
    for arg in "$@"; do
        case "$arg" in
            --deep) deep=yes ;;
            --no-clean) do_clean=no ;;
            --skip-tests) run_tests=no ;;
            --skip-smoke) run_smoke=no ;;
            *) echo "未知的 build 参数：$arg"; exit 2 ;;
        esac
    done

    desktop_preflight
    if [ "$do_clean" = yes ]; then
        if [ "$deep" = yes ]; then clean_desktop --deep; else clean_desktop; fi
    fi

    if [ -d "$ROOT_DIR/node_modules" ]; then
        :
    else
        echo "安装前端依赖…"
        (cd "$ROOT_DIR" && npm ci)
    fi

    if [ "$run_tests" = yes ]; then
        echo "运行锁文件与回归测试…"
        (cd "$ROOT_DIR" && uv lock --check)
        (cd "$ROOT_DIR" && uv run --locked --group desktop python -m unittest discover -s tests)
        (cd "$ROOT_DIR" && node --test tests/js/*.test.cjs)
    fi

    echo "同步桌面依赖…"
    (cd "$ROOT_DIR" && uv sync --locked --group desktop --python 3.11)

    echo "构建 Tauri 应用与 DMG（首次或清理后较慢）…"
    (cd "$ROOT_DIR" && npm run desktop:build)

    BUNDLE_DIR=$(desktop_bundle_dir) || {
        echo "打包失败：未找到 bundle 目录。"; exit 1
    }
    APP_PATH="$BUNDLE_DIR/macos/mflux WebUI.app"
    if [ ! -d "$APP_PATH" ]; then echo "打包失败：未生成 $APP_PATH"; exit 1; fi

    if [ "$run_smoke" = yes ]; then
        echo "验证安装包内置后端…"
        (cd "$ROOT_DIR" && uv run --locked --group desktop python scripts/smoke_desktop_backend.py \
            "$APP_PATH/Contents/Resources/backend/mflux-backend")
    fi

    VERSION=$(cd "$ROOT_DIR" && node -p 'require("./src-tauri/tauri.conf.json").version')
    OUT_DIR="$ROOT_DIR/dist/desktop"
    rm -rf "$OUT_DIR"
    mkdir -p "$OUT_DIR"
    DMG_NAME="mflux-WebUI_${VERSION}_macos-arm64.dmg"
    ZIP_NAME="mflux-WebUI_${VERSION}_macos-arm64.app.zip"
    set -- "$BUNDLE_DIR"/dmg/*.dmg
    if [ -f "$1" ]; then cp "$1" "$OUT_DIR/$DMG_NAME"; else echo "警告：未找到 DMG，跳过复制。"; fi
    ditto -c -k --sequesterRsrc --keepParent "$APP_PATH" "$OUT_DIR/$ZIP_NAME"
    (cd "$OUT_DIR" && shasum -a 256 ./* > SHA256SUMS.txt)

    printf '\n打包完成（版本 %s）\n' "$VERSION"
    for artifact in "$OUT_DIR"/*; do
        printf '  %s (%s)\n' "${artifact#"$ROOT_DIR"/}" "$(human_kb "$(du -sk "$artifact" | awk '{print $1}')")"
    done
    printf '\n校验值：%s/SHA256SUMS.txt\n' "${OUT_DIR#"$ROOT_DIR"/}"
    printf '安装测试：open "%s"\n' "$OUT_DIR/${DMG_NAME:-$ZIP_NAME}"
}

case "${1:-}" in
    start) start ;;
    stop) stop ;;
    status)
        if [ "${2:-}" = "--watch" ]; then status_watch; else status_snapshot; fi
        ;;
    logs) logs "${2:-100}" ;;
    restart) stop; start ;;
    build) shift; build_desktop "$@" ;;
    clean) shift; clean_desktop "$@" ;;
    *)
        cat <<'USAGE'
用法：ops.sh <命令>

  服务：
    start                 前台构建前端并后台启动（默认 8090）
    stop                  停止服务
    status [--watch]      查看运行状态，--watch 每 5 秒刷新
    logs [行数]           查看并跟踪日志
    restart               重启服务

  桌面版：
    build [参数]          一键打包 macOS 桌面版（.app + .dmg）
      --deep              先删除 uv 环境与 src-tauri/target（全量重建）
      --no-clean          跳过打包前清理，直接复用缓存
      --skip-tests        跳过 lock 校验与回归测试
      --skip-smoke        跳过安装包内置后端自检
    clean [参数]          只清理打包缓存与旧产物
      --deep              连同 uv 环境与 src-tauri/target 一起删除
      --dry-run           只列出将删除的内容

示例：
  ./ops.sh build                 清理 → 回归 → 打包 → 自检 → 汇总到 dist/desktop
  ./ops.sh build --deep          从零重建（最慢）
  ./ops.sh clean --dry-run       先看看能腾出多少空间
USAGE
        exit 2
        ;;
esac
