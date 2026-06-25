from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

from src.core.app_config import get_app_config
from src.core.config import get_settings

_s = get_settings()
_pool = get_app_config().database.clickhouse

engine = create_engine(
    _s.get_clickhouse_url(),
    poolclass=QueuePool,
    pool_size=_pool.pool_size,
    max_overflow=_pool.max_overflow,
    pool_timeout=_pool.pool_timeout,
    pool_recycle=_pool.pool_recycle,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_clickhouse_connection():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
