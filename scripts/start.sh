#!/usr/bin/env bash
set -euo pipefail


PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

RUNTIME_DIR="$PROJECT_DIR/runtime"
LOG_DIR="$RUNTIME_DIR/logs"
PID_DIR="$RUNTIME_DIR/pids"

mkdir -p "$LOG_DIR" "$PID_DIR"

if [[ ! -f "$PROJECT_DIR/.env" ]]; then
    echo "ERROR: .env not found. Run bootstrap.sh first."
    exit 1
fi

# Загружаем конфигурацию сервисов
set -a
source "$PROJECT_DIR/.env"
set +a


start_service() {
    local name="$1"
    shift

    local pid_file="$PID_DIR/$name.pid"
    local log_file="$LOG_DIR/$name.log"

    # Не запускаем второй экземпляр уже работающего сервиса.
    if [[ -f "$pid_file" ]]; then
        local pid
        pid="$(cat "$pid_file")"

        if kill -0 "$pid" 2>/dev/null; then
            echo "$name is already running (PID $pid)."
            return
        fi

        rm -f "$pid_file"
    fi

    echo "Starting $name..."

    nohup "$@" > "$log_file" 2>&1 &
    echo $! > "$pid_file"
}


start_service \
    ollama \
    env OLLAMA_HOST="$BACKEND_OLLAMA_HOST:$BACKEND_OLLAMA_PORT" \
    ollama serve


start_service \
    api \
    .venv/bin/uvicorn app.main:app \
    --host "$BACKEND_API_HOST" \
    --port "$BACKEND_API_PORT"


COMFYUI_DIR="$BACKEND_SERVICES_DIR/ComfyUI"

start_service \
    comfyui \
    "$COMFYUI_DIR/.venv/bin/python" \
    "$COMFYUI_DIR/main.py" \
    --listen "$BACKEND_COMFYUI_HOST" \
    --port "$BACKEND_COMFYUI_PORT"


echo "Services started."
