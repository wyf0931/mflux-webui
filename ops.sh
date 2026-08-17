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

start() {
    if is_running; then echo "mflux WebUI 已运行（PID $(cat "$PID_FILE")）"; return; fi
    mkdir -p "$ROOT_DIR/logs"
    rm -f "$PID_FILE"
    PORT_PID=$(port_owner || true)
    if [ -n "$PORT_PID" ]; then
        echo "启动失败：端口 8090 已被 PID $PORT_PID 占用"
        exit 1
    fi
    (
        cd "$ROOT_DIR"
        nohup uv run python app.py >>"$LOG_FILE" 2>&1 &
        echo $! >"$PID_FILE"
    )
    sleep 1
    if is_running; then echo "mflux WebUI 已启动：http://127.0.0.1:8090（PID $(cat "$PID_FILE")）"; else echo "启动失败，请查看 $LOG_FILE"; exit 1; fi
}

stop() {
    if is_running; then kill "$(cat "$PID_FILE")"; rm -f "$PID_FILE"; echo "mflux WebUI 已停止"; else rm -f "$PID_FILE"; echo "mflux WebUI 未运行"; fi
}

status() { if is_running; then echo "mflux WebUI 正在运行（PID $(cat "$PID_FILE")）"; else echo "mflux WebUI 未运行"; return 1; fi; }

case "${1:-}" in start) start ;; stop) stop ;; status) status ;; restart) stop; start ;; *) echo "用法：$0 {start|stop|status|restart}"; exit 2 ;; esac
