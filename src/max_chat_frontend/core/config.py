from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "MAX Chat Frontend"
    environment: str = "development"
    backend_base_url: str = "http://localhost:8000"
    backend_api_prefix: str = "/api/v1"
    internal_api_key: str = "change-me"
    frontend_secret_key: str = "change-me"
    admin_username: str = "admin"
    admin_password: str = "change-me"


@lru_cache
def get_settings() -> Settings:
    return Settings()

