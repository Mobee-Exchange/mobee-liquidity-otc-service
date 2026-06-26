from pydantic_settings import BaseSettings

from src.db.base import build_engine
from src.utils.path import return_full_path


class PostgresSettings(BaseSettings):
    """Postgres connection URL, read from .env (POSTGRES_URL).

    Pool tuning is shared across databases — see src.client.base.DBSettings.
    """

    postgres_url: str

    class Config:
        extra = "allow"
        env_file = return_full_path(".env")
        env_file_encoding = "utf-8"


settings = PostgresSettings()
engine = build_engine(settings.postgres_url)
