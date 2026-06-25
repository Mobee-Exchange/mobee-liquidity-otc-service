from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

from src.core.config import get_settings

_s = get_settings()

engine = create_engine(
    _s.get_clickhouse_url(),
    poolclass=QueuePool,
    pool_size=_s.clickhouse_pool_size,
    max_overflow=_s.clickhouse_max_overflow,
    pool_timeout=_s.clickhouse_pool_timeout,
    pool_recycle=_s.clickhouse_pool_recycle,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_clickhouse_connection():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
