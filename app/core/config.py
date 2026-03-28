from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = Field(..., alias="DATABASE_URL")
    frontend_confirm_base_url: str = Field(..., alias="FRONTEND_CONFIRM_BASE_URL")
    token_salt_secret: str = Field(..., alias="TOKEN_SALT_SECRET")
    admin_token_secret: str | None = Field(None, alias="ADMIN_TOKEN_SECRET")
    admin_token_ttl_minutes: int = Field(480, alias="ADMIN_TOKEN_TTL_MINUTES")
    admin_reporting_timezone: str = Field("Europe/Istanbul", alias="ADMIN_REPORTING_TIMEZONE")
    admin_bootstrap_username: str | None = Field(None, alias="ADMIN_BOOTSTRAP_USERNAME")
    admin_bootstrap_email: str | None = Field(None, alias="ADMIN_BOOTSTRAP_EMAIL")
    admin_bootstrap_password: str | None = Field(None, alias="ADMIN_BOOTSTRAP_PASSWORD")
    whatsapp_enabled: bool = Field(False, alias="WHATSAPP_ENABLED")
    whatsapp_graph_api_version: str = Field("v23.0", alias="WHATSAPP_GRAPH_API_VERSION")
    whatsapp_access_token: str | None = Field(None, alias="WHATSAPP_ACCESS_TOKEN")
    whatsapp_phone_number_id: str | None = Field(None, alias="WHATSAPP_PHONE_NUMBER_ID")
    whatsapp_confirmation_template_name: str | None = Field(
        None,
        alias="WHATSAPP_CONFIRMATION_TEMPLATE_NAME",
    )
    whatsapp_confirmation_template_language: str = Field(
        "tr",
        alias="WHATSAPP_CONFIRMATION_TEMPLATE_LANGUAGE",
    )
    whatsapp_default_country_code: str = Field("90", alias="WHATSAPP_DEFAULT_COUNTRY_CODE")
    storage_dir: str = Field("storage", alias="STORAGE_DIR")
    google_maps_api_key: str | None = Field(None, alias="GOOGLE_MAPS_API_KEY")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
