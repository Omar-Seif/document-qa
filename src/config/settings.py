from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables and .env."""

    # =========================================================================
    # LLM Configuration
    # =========================================================================
    GROQ_API_KEY: str
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    MODEL: str = "openai/gpt-oss-20b"
    EMBEDDING_MODEL: str = "nomic-embed-text-v1_5"

    # =========================================================================
    # API Configuration
    # =========================================================================
    API_PREFIX: str = "/api"
    ALLOWED_ORIGINS: List[str] = ["https://localhost:3000", "https://localhost:5173"]

    # =========================================================================
    # Application Configuration
    # =========================================================================
    DEBUG: bool = True

    # =========================================================================
    # Server Configuration
    # =========================================================================
    PORT: int = 8000

    # =========================================================================
    # Logging
    # =========================================================================
    LOG_LEVEL: str = "DEBUG"
    LOG_FILE_PATH: str = "logs/app.log"

    # =========================================================================
    # Groq API / Retry Configuration
    # =========================================================================
    REQUEST_TIMEOUT: int = 30
    MAX_RETRIES: int = 3
    RETRY_DELAY: int = 1

    @field_validator("LOG_LEVEL", mode="after")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper_v = v.upper()
        if upper_v not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of {valid_levels}, got: {v}")
        return upper_v

    @field_validator("ALLOWED_ORIGINS", mode="after")
    @classmethod
    def validate_allowed_origins(cls, origins: List[str]) -> List[str]:
        normalized: List[str] = []
        seen: set[str] = set()
        for origin in origins:
            origin = origin.strip().lower()
            if not origin:
                raise ValueError("ALLOWED_ORIGINS cannot contain empty values.")
            if origin not in seen:
                normalized.append(origin)
                seen.add(origin)
        return normalized

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
