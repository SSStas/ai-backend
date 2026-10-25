import httpx
import torch
from fastapi import FastAPI

from app.config import settings
from app.routers.audio import router as audio_router


app = FastAPI(
    title="AI Backend",
    version="0.1.0",
)

app.include_router(audio_router)

@app.get("/health")
async def health():
    cuda_available = torch.cuda.is_available()

    ollama_available = False

    try:
        async with httpx.AsyncClient(timeout=2) as client:
            response = await client.get(
                f"{settings.ollama_url}/api/tags"
            )
            ollama_available = response.is_success
    except httpx.HTTPError:
        pass

    return {
        "status": "ok",
        "cuda": {
            "available": cuda_available,
            "device": (
                torch.cuda.get_device_name(0)
                if cuda_available
                else None
            ),
        },
        "ollama": {
            "available": ollama_available,
        },
    }
