from sqlalchemy.orm import Session
from sqlalchemy import text

from src.domain.entity.ingest import LiquidityBalanceRawData

_CREATE_BALANCE_INGEST_SQL = """
CREATE TABLE IF NOT EXISTS mobee_liquidity_otc.balance_ingest
(
    timestamp   DateTime64(3, 'Asia/Jakarta'),
    platform    LowCardinality(String),
    source_name LowCardinality(String),
    currency    LowCardinality(String),
    network     LowCardinality(String),
    amount      Decimal(38, 18)
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (timestamp, platform, source_name, currency)
"""


class BalanceIngestRepository:
    """Persistence port for the unified balance_ingest table."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def ensure_table(self) -> None:
        self._session.execute(text(_CREATE_BALANCE_INGEST_SQL))
        self._session.commit()

    def truncate(self) -> None:
        self._session.execute(text("TRUNCATE TABLE mobee_liquidity_otc.balance_ingest"))
        self._session.commit()

    def insert_total_balance(self, rows: list[LiquidityBalanceRawData]) -> None:
        self._session.execute(
            text(
                "INSERT INTO mobee_liquidity_otc.balance_ingest "
                "(timestamp, platform, source_name, currency, network, amount) "
                "VALUES (:timestamp, :platform, :source_name, :currency, :network, :amount)"
            ),
            [r.model_dump() for r in rows],
        )
        self._session.commit()
