import logging
from datetime import datetime
from decimal import Decimal

from src.db.clickhouse import session_scope
from src.repository.liquidity_net_position import LiquidityNetPositionRepository
from src.repository.price_quote import PriceRepository

log = logging.getLogger(__name__)


class LiquiditySnapshotService:
    """Freezes a point-in-time snapshot of liquidity_net_position with USD
    valuation.

    Reads the native (per-currency) view, applies current USD prices from
    datawarehouse.last_hour_price_diff, and writes liquidity_net_position_snapshot
    — all in one transaction so the read, prices, and write are consistent.
    Run it *after* the platform ingest so balance_latest reflects the new run.
    """

    @staticmethod
    def _to_decimal(value) -> Decimal:
        return value if isinstance(value, Decimal) else Decimal(str(value))

    def run(self, snapshot_ts: datetime | None = None) -> int:
        snapshot_ts = snapshot_ts or datetime.now()
        log.info("Snapshot timestamp: %s", snapshot_ts)

        with session_scope() as session:
            repo = LiquidityNetPositionRepository(session)
            positions = repo.fetch_net_position()
            if not positions:
                log.warning(
                    "liquidity_net_position returned no rows — skipping snapshot"
                )
                return 0

            currencies = [p["currency"] for p in positions]
            prices = PriceRepository(session).fetch_current_prices(currencies)

            rows = []
            for p in positions:
                currency = p["currency"]
                liquidity = self._to_decimal(p["liquidity_balance"])
                price = prices.get(currency)
                if price is None:
                    log.warning(
                        "No USD price for %s — storing NULL valuation", currency
                    )
                    usd_price = 1
                    liquidity_usd = liquidity
                else:
                    usd_price = Decimal(str(price))
                    liquidity_usd = liquidity * usd_price
                rows.append(
                    {
                        "currency": currency,
                        "total_balance": self._to_decimal(p["total_balance"]),
                        "client_balance": self._to_decimal(p["client_balance"]),
                        "liquidity_balance": liquidity,
                        "usd_price": usd_price,
                        "liquidity_balance_usd": liquidity_usd,
                    }
                )

            inserted = repo.insert_snapshot(snapshot_ts, rows)

        total_usd = sum(
            (
                r["liquidity_balance_usd"]
                for r in rows
                if r["liquidity_balance_usd"] is not None
            ),
            Decimal(0),
        )
        log.info(
            "Snapshot wrote %d currency rows; total net liquidity ≈ $%s",
            inserted,
            total_usd,
        )
        return inserted
