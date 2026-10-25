#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

if [[ ! -f "$PROJECT_DIR/.env" ]]; then
    echo "ERROR: .env not found. Run bootstrap.sh first."
    exit 1
fi

# Загружаем конфигурацию сервисов
set -a
source "$PROJECT_DIR/.env"
set +a


echo "Bootstrapping AI Backend..."

# Устанавливаем uv, если его ещё нет
if ! command -v uv >/dev/null 2>&1; then
    echo "Installing uv..."
    python3 -m pip install --quiet uv
fi

# Создаём окружение с доступом к системному PyTorch GPU-машины
if [[ ! -d .venv ]]; then
    uv venv --system-site-packages .venv
fi

uv sync --frozen --no-default-groups


# Устанавливаем Ollama, если его ещё нет
if ! command -v ollama >/dev/null 2>&1; then
    curl -fsSL https://ollama.com/install.sh | sh
fi


mkdir -p "$BACKEND_SERVICES_DIR"

COMFYUI_DIR="$BACKEND_SERVICES_DIR/ComfyUI"

# Устанавливаем ComfyUI, если его ещё нет
if [[ ! -d "$COMFYUI_DIR" ]]; then
    git clone \
        https://github.com/comfyanonymous/ComfyUI.git \
        "$COMFYUI_DIR"
fi

# Создаём отдельное окружение ComfyUI
if [[ ! -d "$COMFYUI_DIR/.venv" ]]; then
    uv venv \
        --system-site-packages \
        "$COMFYUI_DIR/.venv"
fi

# Устанавливаем зависимости ComfyUI
uv pip install \
    --python "$COMFYUI_DIR/.venv/bin/python" \
    -r "$COMFYUI_DIR/requirements.txt"


mkdir -p runtime/logs
mkdir -p runtime/pids

echo "Bootstrap complete."
