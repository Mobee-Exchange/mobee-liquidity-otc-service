from src.core.config import settings as s
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from sqlalchemy import Engine, create_engine


def build_engine() -> Engine:
    return create_engine(
        s.postgres_url,
        poolclass=QueuePool,
        pool_size=s.pool_size,
        max_overflow=s.max_overflow,
        pool_timeout=s.pool_timeout,
        pool_recycle=s.pool_recycle,
        pool_pre_ping=True,
    )


SessionLocal = sessionmaker(bind=build_engine(), autoflush=False, autocommit=False)


def get_postgress_conn():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
