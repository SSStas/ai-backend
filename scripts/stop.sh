#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

PID_DIR="$PROJECT_DIR/runtime/pids"


stop_service() {
    local name="$1"
    local pid_file="$PID_DIR/$name.pid"

    if [[ ! -f "$pid_file" ]]; then
        echo "$name is not running."
        return
    fi

    local pid
    pid="$(cat "$pid_file")"

    # Останавливаем только процесс, который запускал этот проект.
    if kill -0 "$pid" 2>/dev/null; then
        echo "Stopping $name (PID $pid)..."
        kill "$pid"
    fi

    rm -f "$pid_file"
}


stop_service api
stop_service ollama

echo "Services stopped."
