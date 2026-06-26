from pydantic_settings import BaseSettings
from sqlalchemy import Engine, create_engine
from sqlalchemy.pool import QueuePool

from src.utils.path import return_full_path


class DBSettings(BaseSettings):
    """Shared connection-pool / retry policy for every database.

    Pool tuning defaults here (the shared policy) and applies to all engines;
    override per-deploy via DB_* env vars (DB_POOL_SIZE, ...). Per-database URLs
    live in each database's own settings (ClickhouseSettings, PostgresSettings).
    """

    pool_size: int = 2
    max_overflow: int = 5
    pool_timeout: int = 30
    pool_recycle: int = 900

    class Config:
        env_prefix = "DB_"
        extra = "allow"
        env_file = return_full_path(".env")
        env_file_encoding = "utf-8"


db_settings = DBSettings()


def build_engine(url: str) -> Engine:
    """Create a SQLAlchemy engine using the shared pool/retry policy.

    ``pool_pre_ping`` health-checks a connection before use, transparently
    replacing ones the server has dropped — the shared "retry policy".
    """
    return create_engine(
        url,
        poolclass=QueuePool,
        pool_size=db_settings.pool_size,
        max_overflow=db_settings.max_overflow,
        pool_timeout=db_settings.pool_timeout,
        pool_recycle=db_settings.pool_recycle,
        pool_pre_ping=True,
    )
