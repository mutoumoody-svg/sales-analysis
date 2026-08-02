"""
Application configuration.
Settings are loaded from environment variables / .env file.
"""

from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field

# .env 文件位置：backend/.env（相对于本文件的上级目录）
ENV_FILE_PATH = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    """Application settings."""

    # Application
    APP_NAME: str = "AI Business Decision Platform"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/sales_analysis"

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    model_config = {"env_file": str(ENV_FILE_PATH), "env_file_encoding": "utf-8"}

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]


settings = Settings()
