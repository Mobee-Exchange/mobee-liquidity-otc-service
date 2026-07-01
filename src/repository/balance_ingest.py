from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.db.clickhouse import SessionLocal
from src.domain.entity.ingest import LiquidityBalanceRawData


class BalanceIngestRepository:
    """Data access (DML) for the unified balance_ingest table.

    Owns session lifecycle: each method runs in its own short-lived
    :meth:`session_scope` (commit on success, roll back on error, always
    close). Schema (CREATE TABLE) lives in .sql, not here.
    """

    def __init__(self, session_factory=SessionLocal) -> None:
        self._session_factory = session_factory

    @contextmanager
    def session_scope(self) -> Iterator[Session]:
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def truncate(self) -> None:
        with self.session_scope() as session:
            session.execute(text("TRUNCATE TABLE mobee_liquidity_otc.balance_ingest"))

    def latest(self) -> list[dict]:
        """Current balance per (platform, source_name, currency, network):
        the newest observation for each, read from the balance_latest view."""
        with self.session_scope() as session:
            result = session.execute(
                text(
                    "SELECT platform, source_name, currency, network, amount, as_of "
                    "FROM mobee_liquidity_otc.balance_latest"
                )
            ).mappings().all()
        return [dict(row) for row in result]

    def insert_total_balance(self, rows: list[LiquidityBalanceRawData]) -> int:
        """Insert balance rows; return the number written.

        Returns 0 for an empty batch (caller decides whether that's a warning).
        Raises on DB failure — session_scope rolls back, then re-raises.
        """
        if not rows:
            return 0
        with self.session_scope() as session:
            session.execute(
                text(
                    "INSERT INTO mobee_liquidity_otc.balance_ingest "
                    "(timestamp, platform, source_name, currency, network, amount) "
                    "VALUES (:timestamp, :platform, :source_name, :currency, :network, :amount)"
                ),
                [r.model_dump() for r in rows],
            )
        return len(rows)
