from sqlalchemy.orm import sessionmaker

from src.db.postgres.engine import engine

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_postgres_connection():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
