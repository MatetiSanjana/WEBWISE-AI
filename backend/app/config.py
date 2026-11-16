"""Application settings. Credentials are read ONLY from environment variables / the root .env file."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Webwise AI/  (config.py -> app -> backend -> project root)
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _is_placeholder(value: str) -> bool:
    v = (value or "").strip().lower()
    return (not v) or v.startswith("your-") or v.endswith("-here") or v in {"changeme", "xxx"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    tavily_api_key: str = ""
    gemini_api_key: str = ""
    # QA finding: gemini-4-hydrogen's free tier allows only 20 requests/day (about 7 researches). gemini-3.5-flash-lite
    # completed Quick/Deep runs in 13s/27s with intact citations, so it is the default; override with GEMINI_MODEL.
    gemini_model: str = "gemini-3.5-flash-lite"
    enable_docs: bool = True  # set ENABLE_DOCS=false in production to hide /docs and /openapi.json

    frontend_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    database_path: str = "backend/data/webwise.db"
    log_level: str = "INFO"
    http_timeout_seconds: float = 45
    llm_timeout_seconds: float = 120
    rate_limit_per_minute: int = 10

    @property
    def tavily_configured(self) -> bool:
        return not _is_placeholder(self.tavily_api_key)

    @property
    def gemini_configured(self) -> bool:
        return not _is_placeholder(self.gemini_api_key)

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.frontend_origins.split(",") if o.strip()]

    @property
    def db_file(self) -> Path:
        p = Path(self.database_path)
        return p if p.is_absolute() else PROJECT_ROOT / p


@lru_cache
def get_settings() -> Settings:
    return Settings()
