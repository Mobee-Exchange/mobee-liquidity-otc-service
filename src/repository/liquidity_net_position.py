from datetime import datetime

from sqlalchemy import orm, text


class LiquidityNetPositionRepository:
    """Reads the live liquidity_net_position view and writes its USD-valued
    snapshot. Session-injected: the caller owns the transaction (so the read,
    price lookup, and write share one unit of work).

    Schema (CREATE TABLE / CREATE VIEW) lives in .sql, not here.
    """

    def __init__(self, session: orm.Session):
        self.session = session

    def fetch_net_position(self) -> list[dict]:
        """Current net liquidity per currency, in native units."""
        result = self.session.execute(
            text(
                "SELECT currency, total_balance, client_balance, liquidity_balance "
                "FROM mobee_liquidity_otc.liquidity_net_position"
            )
        ).mappings().all()
        return [dict(row) for row in result]

    def insert_snapshot(self, snapshot_ts: datetime, rows: list[dict]) -> int:
        """Write one snapshot run. Each row carries native amounts plus the USD
        price applied and the resulting USD value (both may be None)."""
        if not rows:
            return 0
        self.session.execute(
            text(
                "INSERT INTO mobee_liquidity_otc.liquidity_net_position_snapshot "
                "(snapshot_ts, currency, total_balance, client_balance, "
                " liquidity_balance, usd_price, liquidity_balance_usd) "
                "VALUES (:snapshot_ts, :currency, :total_balance, :client_balance, "
                " :liquidity_balance, :usd_price, :liquidity_balance_usd)"
            ),
            [{"snapshot_ts": snapshot_ts, **row} for row in rows],
        )
        return len(rows)
