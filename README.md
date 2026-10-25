# AI Backend

Удалённый GPU backend для локальных AI-приложений.

Текущий deployment target: Google Colab.

## Architecture

Исходный код проекта хранится локально.

На удалённой GPU-машине выполняются:

- FastAPI
- Ollama
- далее: Whisper / ComfyUI / Diffusers

### Scripts

- `deploy/*` — доставка проекта и platform-specific подготовка машины.
- `scripts/bootstrap.sh` — общая подготовка проекта и зависимостей.
- `scripts/start.sh` — запуск сервисов.
- `scripts/stop.sh` — остановка сервисов.

## Google Colab

Создать GPU runtime:

```bash
colab --auth=oauth2 new -s ai-backend --gpu L4
```

Проверить runtime:

```bash
colab status -s ai-backend
```

Развернуть backend:

```bash
./deploy/colab/deploy.sh
```

После deploy открыть постоянное SSH-соединение:

```bash
ssh colab-gpu
```

Локальные endpoints:

- FastAPI: `http://127.0.0.1:18000`
- FastAPI docs: `http://127.0.0.1:18000/docs`
- Ollama: `http://127.0.0.1:11435`
- ComfyUI: `http://127.0.0.1:18188` — после установки

Проверить FastAPI:

```bash
curl http://127.0.0.1:18000/health
```

Проверить Ollama:

```bash
curl http://127.0.0.1:11435/api/tags
```

Остановить Colab runtime:

```bash
colab stop -s ai-backend
```

Google Colab пересоздаёт VM, поэтому `prepare`, `bootstrap` и `start` выполняются для каждого нового runtime через `deploy/colab/deploy.sh`.

## Persistent GPU Server

На постоянной GPU-машине `prepare` и `bootstrap` обычно выполняются только при первоначальной настройке или изменении окружения.

После этого для управления сервисами используются:

```bash
scripts/start.sh
scripts/stop.sh
```
