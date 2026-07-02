from pydantic_settings import BaseSettings

from src.db.base import build_engine
from src.utils.path import return_full_path


class ClickhouseSettings(BaseSettings):
    """ClickHouse connection URL, read from .env (CLICKHOUSE_URL).

    Pool tuning is shared across databases — see src.client.base.DBSettings.
    """

    clickhouse_url: str

    class Config:
        extra = "allow"
        env_file = return_full_path(".env")
        env_file_encoding = "utf-8"


settings = ClickhouseSettings()
engine = build_engine(settings.clickhouse_url)
