from enum import Enum
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool
from src.core.config import get_settings

s = get_settings()


class DatabaseUrl(Enum):
    CLICKHOUSE = s.db_clickhouse_url
    DATADB = s.db_datadb_url


engines = {
    name: create_engine(
        url=enum_val.value,
        poolclass=QueuePool,
        pool_size=3,
        max_overflow=5,
        pool_timeout=30,
        pool_recycle=1800,
    )
    for name, enum_val in DatabaseUrl.__members__.items()
}

SessionLocal = {
    name: scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
    for name, engine in engines.items()
}


def get_db_session(db_type: str):
    """Context generator yielding a DB session for the given db_type."""
    session_factory = SessionLocal.get(db_type)
    if session_factory is None:
        raise ValueError(f"Database type '{db_type}' is not recognized.")

    session = session_factory()
    try:
        yield session
    finally:
        session.close()
