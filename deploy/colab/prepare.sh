#!/usr/bin/env bash
set -euo pipefail

echo "Preparing Google Colab runtime..."

if [[ ! -f ".env" ]]; then
    cp ".env.example" ".env"

    sed -i \
        's|^BACKEND_SERVICES_DIR=.*|BACKEND_SERVICES_DIR=/content/services|' \
        ".env"
fi

if [[ -f ".env.local" ]]; then
    set -a
    source ".env.local"
    set +a

    if [[ -n "${HF_TOKEN:-}" ]]; then
        sed -i \
            "s|^HF_TOKEN=.*|HF_TOKEN=$HF_TOKEN|" \
            ".env"
    fi

    rm -f ".env.local"
fi

if [[ ! -x "$(command -v ffmpeg)" ]]; then
    apt-get update -qq
    apt-get install -y -qq ffmpeg
fi

if [[ ! -d /usr/lib64-nvidia ]]; then
    echo "ERROR: /usr/lib64-nvidia not found."
    echo "The Colab session probably has no GPU."
    exit 1
fi

echo "/usr/lib64-nvidia" > /etc/ld.so.conf.d/nvidia.conf
ldconfig

# Colab-specific: нужен для распаковки Ollama installer.
if ! command -v zstd >/dev/null 2>&1; then
    apt-get update -qq
    apt-get install -y -qq zstd
fi

nvidia-smi

echo "Colab runtime prepared."
