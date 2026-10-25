from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


APP_DIR = Path(__file__).resolve().parent
PROJECT_DIR = APP_DIR.parent


class Settings(BaseSettings):
    backend_api_host: str
    backend_api_port: int

    backend_ollama_host: str
    backend_ollama_port: int

    backend_comfyui_host: str
    backend_comfyui_port: int

    backend_services_dir: str

    hf_token: str | None = None

    model_config = SettingsConfigDict(
        env_file=PROJECT_DIR / ".env",
        env_file_encoding="utf-8"
    )

    @property
    def ollama_url(self) -> str:
        return f"http://{self.backend_ollama_host}:{self.backend_ollama_port}"
    

settings = Settings()
