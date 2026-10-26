import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# 统一从项目根目录 .env 读取，前后端共用一份配置。
PROJECT_ROOT = Path(__file__).resolve().parents[3]
ENV_FILE = Path(os.environ.get("BAS_ENV_FILE", PROJECT_ROOT / ".env"))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "Business Attribution System"
    api_host: str = "127.0.0.1"
    api_port: int = 8000

    database_url: str = "sqlite+aiosqlite:///./data/app.db"
    business_database_url: str = "sqlite+aiosqlite:///./data/business.db"

    jwt_secret: str = "change-me-demo-secret-at-least-32-bytes"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    auth_mode: str = "demo"
    auth_center_base_url: str = ""
    auth_client_id: str = ""
    auth_client_secret: str = ""
    auth_redirect_uri: str = "http://127.0.0.1:8000/auth/callback"
    frontend_base_url: str = "http://127.0.0.1:5173"

    cors_origins: list[str] = ["http://127.0.0.1:5173", "http://localhost:5173"]

    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-chat"
    deepseek_base_url: str = "https://api.deepseek.com"
    llm_timeout_seconds: int = 60
    agent_max_tool_calls: int = 8
    agent_max_corrections: int = 2

    sql_query_timeout_seconds: int = 10
    sql_max_rows: int = 200
    sql_allowed_tables: list[str] = []

    storage_root: str = "./storage"
    upload_max_mb: int = 50
    ws_token_ttl_seconds: int = 60

    @property
    def llm_configured(self) -> bool:
        return bool(self.deepseek_api_key.strip())

    @property
    def storage_path(self) -> Path:
        return Path(self.storage_root).resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()
