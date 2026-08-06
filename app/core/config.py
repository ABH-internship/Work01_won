from functools import lru_cache
from datetime import date
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "Work01 API"
    app_env: str = "development"
    api_prefix: str = "/api"
    base_date_override: date | None = Field(default=None, validation_alias="BASE_DATE")

    postgres_db: str = "abh"
    postgres_user: str = "abh"
    postgres_password: str = "1234"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    database_url: str | None = None

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.database_url:
            return self.database_url

        return (
            "postgresql+psycopg://"
            f"{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def base_date(self) -> date:
        if self.app_env.lower() == "development" and self.base_date_override:
            return self.base_date_override

        return date.today()


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
