#!/usr/bin/env sh
set -eu

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

case "${1:-}" in
    start) start ;;
    stop) stop ;;
    status)
        if [ "${2:-}" = "--watch" ]; then status_watch; else status_snapshot; fi
        ;;
    logs) logs "${2:-100}" ;;
    restart) stop; start ;;
    *) echo "用法：$0 {start|stop|status [--watch]|logs [行数]|restart}"; exit 2 ;;
esac
