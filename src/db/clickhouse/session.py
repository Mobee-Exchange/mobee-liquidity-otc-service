from sqlalchemy.orm import sessionmaker

from src.db.clickhouse.engine import engine

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_clickhouse_connection():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
