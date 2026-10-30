from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Automation Workflow Manager"
    app_env: str = "development"
    api_prefix: str = "/api"

    database_url: str = "postgresql+psycopg://workflow:workflow_dev_pw@localhost:5432/workflow"

    upload_dir: Path = Path("/data/uploads")
    processed_dir: Path = Path("/data/processed")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
