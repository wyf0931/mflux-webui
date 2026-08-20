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
    if is_running; then echo "mflux WebUI 已启动：http://127.0.0.1:8090（PID $(cat "$PID_FILE")）"; else echo "启动失败，请查看 $LOG_FILE"; exit 1; fi
}

stop() {
    if is_running; then kill "$(cat "$PID_FILE")"; rm -f "$PID_FILE"; echo "mflux WebUI 已停止"; else rm -f "$PID_FILE"; echo "mflux WebUI 未运行"; fi
}

status() { if is_running; then echo "mflux WebUI 正在运行（PID $(cat "$PID_FILE")）"; else echo "mflux WebUI 未运行"; return 1; fi; }

logs() {
    lines=${1:-100}
    mkdir -p "$ROOT_DIR/logs"
    touch "$LOG_FILE"
    echo "正在跟踪 $LOG_FILE（最近 $lines 行，按 Ctrl-C 退出）"
    tail -n "$lines" -f "$LOG_FILE"
}

gpu_usage() {
    if command -v ioreg >/dev/null 2>&1; then
        value=$(ioreg -r -d 1 -c IOAccelerator -k PerformanceStatistics 2>/dev/null \
            | grep -m1 'Device Utilization' \
            | sed -E 's/.*"Device Utilization %"=([0-9]+).*/\1%/' || true)
        [ -n "$value" ] && { echo "$value"; return; }
    fi
    if command -v nvidia-smi >/dev/null 2>&1; then
        nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits 2>/dev/null \
            | head -n 1 | awk '{print $1 "%"}'
        return
    fi
    echo "n/a"
}

memory_usage() {
    if command -v vm_stat >/dev/null 2>&1 && command -v sysctl >/dev/null 2>&1; then
        page_size=$(vm_stat | sed -n 's/.*page size of \([0-9][0-9]*\) bytes.*/\1/p' | head -n 1)
        total_bytes=$(sysctl -n hw.memsize 2>/dev/null || true)
        if [ -n "$page_size" ] && [ -n "$total_bytes" ]; then
            free_pages=$(vm_stat | awk '/Pages free|Pages inactive|Pages speculative|Pages purgeable/ {gsub("\\.", "", $2); total += $2} END {print total + 0}')
            used_bytes=$((total_bytes - free_pages * page_size))
            awk -v used="$used_bytes" -v total="$total_bytes" 'BEGIN { printf "%.1f%%", used / total * 100 }'
            return
        fi
    fi
    echo "n/a"
}

status_snapshot() {
    if ! is_running; then
        echo "mflux WebUI 未运行"
        return 1
    fi
    APP_PID=$(cat "$PID_FILE")
    app_cpu=$(ps -p "$APP_PID" -o %cpu= 2>/dev/null | awk '{print $1}')
    app_mem=$(ps -p "$APP_PID" -o %mem= 2>/dev/null | awk '{print $1}')
    app_elapsed=$(ps -p "$APP_PID" -o etime= 2>/dev/null | sed 's/^ *//')
    printf 'mflux WebUI 运行中  PID=%s  uptime=%s\n' "$APP_PID" "${app_elapsed:-n/a}"
    printf '进程资源        CPU=%s%%  MEM=%s%%\n' "${app_cpu:-n/a}" "${app_mem:-n/a}"
    printf '系统资源        MEM=%s  GPU=%s\n' "$(memory_usage)" "$(gpu_usage)"
    printf '提示：生成期间可使用 "%s status --watch" 每 5 秒刷新一次。\n' "$0"
}

status_watch() {
    while :; do
        clear 2>/dev/null || true
        printf 'mflux WebUI resource monitor  %s\n\n' "$(date '+%Y-%m-%d %H:%M:%S')"
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
