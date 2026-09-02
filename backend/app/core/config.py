"""
Application configuration.
Settings are loaded from environment variables / .env file.
"""

from pathlib import Path
from pydantic_settings import BaseSettings

# .env 文件位置：backend/.env（相对于本文件的上级目录）
ENV_FILE_PATH = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    """Application settings."""

    # Application
    APP_NAME: str = "AI Business Decision Platform"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # Kucun 输出目录（旺店通每日出库 JSON 数据）
    KUCUN_OUTPUT_PATH: str = "/opt/kucun/output"
    SALES_AGENT_DATA_PATH: str = ""

    # 旺店通开放平台 API
    WANGDIAN_SID: str = ""
    WANGDIAN_APPKEY: str = ""
    WANGDIAN_APPSECRET: str = ""
    WANGDIAN_SANDBOX: bool = False

    # Mutation endpoints (imports, sync, cost maintenance)
    ADMIN_API_KEY: str = ""

    model_config = {"env_file": str(ENV_FILE_PATH), "env_file_encoding": "utf-8"}

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()
