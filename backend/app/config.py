from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = (
        "postgresql+psycopg://hrm:hrm_secret@localhost:5432/hrm"
    )
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"
    gowa_send_url: str = "http://gowa:3000/send/message"
    gowa_basic_auth: str = "admin:admin"
    jwt_secret: str = "change-me-in-production-hrm-jwt-secret"
    jwt_expire_hours: int = 12
    docker_network: str = "hrm-net"
    platform_setup_key: str = "hrm-platform-setup"
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_publishable_key: str = ""
    stripe_simulation_mode: bool = True
    public_app_url: str = "http://localhost:5174"
    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-chat"
    deepseek_base_url: str = "https://api.deepseek.com"


@lru_cache
def get_settings() -> Settings:
    return Settings()
