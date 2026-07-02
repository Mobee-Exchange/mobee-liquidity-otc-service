from src.core.config import settings as s
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy import Engine, create_engine
from contextlib import contextmanager
from typing import Iterator

def build_engine() -> Engine:
    return create_engine(
        s.clickhouse_url, 
        poolclass=QueuePool,
        pool_size=s.pool_size,
        max_overflow=s.max_overflow,
        pool_timeout=s.pool_timeout,
        pool_recycle=s.pool_recycle,
        pool_pre_ping=True,
    )

SessionLocal = sessionmaker(bind=build_engine(), autoflush= False, autocommit=False)

def get_clickhouse_connection():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    """Transactional scope: commit on success, roll back on error, always close.

    Use when several repository calls must share one session/transaction
    (e.g. read a view + fetch prices + write a snapshot in one unit).
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
