from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = Field(..., alias="DATABASE_URL")
    frontend_confirm_base_url: str = Field(..., alias="FRONTEND_CONFIRM_BASE_URL")
    token_salt_secret: str = Field(..., alias="TOKEN_SALT_SECRET")
    storage_dir: str = Field("storage", alias="STORAGE_DIR")
    google_maps_api_key: str | None = Field(None, alias="GOOGLE_MAPS_API_KEY")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
