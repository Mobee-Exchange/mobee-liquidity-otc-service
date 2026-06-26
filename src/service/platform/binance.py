import logging
from collections import defaultdict
from datetime import datetime
from decimal import Decimal

from src.client.binance import BinanceClients
from src.core.config import settings
from src.domain.entity.ingest import LiquidityBalanceRawData
from src.repository.balance_ingest import BalanceIngestRepository

log = logging.getLogger(__name__)

# Statuses for currently-held dual-investment positions (excludes SETTLED /
# refunded / failed, which are no longer part of the balance).
_DCI_STATUSES = ["PENDING", "PURCHASE_SUCCESS", "SETTLING"]
_PAGE_SIZE = 100  # matches the client's hardcoded pageSize


class BinanceIngestService:
    """Fetches Binance Dual Investment positions across all held statuses, sums
    subscriptionAmount per invest coin, and writes one balance_ingest row per
    currency. ``source_name`` records which account ("main"/"sub")."""

    def __init__(
        self,
        client: BinanceClients,
        repo: BalanceIngestRepository,
        source_name: str ,
    ) -> None:
        self._client = client
        self._repo = repo
        self._source_name = source_name

    def _fetch_positions(self, status: str) -> list[dict]:
        """All positions for one status, following pagination."""
        positions: list[dict] = []
        page = 1
        while True:
            resp = self._client.get_dual_investment_positions(status=status, pageIndex=page)
            if resp.status_code != 200:
                log.error("DCI status=%s page=%d failed: %s %s",
                          status, page, resp.status_code, resp.text)
                break
            batch = resp.json().get("list", [])
            positions.extend(batch)
            if len(batch) < _PAGE_SIZE:
                break
            page += 1
        return positions

    def ingest(self, snapshot_ts: datetime) -> int:
        totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        for status in _DCI_STATUSES:
            for item in self._fetch_positions(status):
                coin = item["investCoin"]
                totals[coin] += Decimal(str(item["subscriptionAmount"]))

        rows = [
            LiquidityBalanceRawData(
                timestamp=snapshot_ts,
                platform="Binance",
                source_name=self._source_name.upper(),
                currency=coin,
                amount=amount,
            )
            for coin, amount in totals.items()
        ]

        if rows:
            self._repo.insert_total_balance(rows)
            log.info("Inserted %d Binance rows", len(rows))
            for r in rows:
                log.info("  %s = %s", r.currency, r.amount)
        else:
            log.warning("No Binance dual-investment positions found")
        return len(rows)

    def run(self) -> int:
        self._repo.ensure_table()
        snapshot_ts = datetime.now()
        log.info("Snapshot timestamp: %s", snapshot_ts)
        return self.ingest(snapshot_ts)


_BINANCE_CREDS = {
    "main": ("binance_main_api_key", "binance_main_secret"),
    "sub": ("binance_sub_api_key", "binance_sub_secret"),
}


def build_binance_ingest_service(
    repo: BalanceIngestRepository, *, account: str
) -> BinanceIngestService:
    """Build the DCI ingest service for the "main" or "sub" Binance account.

    Each account uses its own API key/secret; source_name is the account
    ("main" / "sub").
    """
    try:
        key_attr, secret_attr = _BINANCE_CREDS[account]
    except KeyError:
        raise ValueError(f"Unknown Binance account {account!r}; expected 'main' or 'sub'")
    client = BinanceClients(getattr(settings, key_attr), getattr(settings, secret_attr))
    return BinanceIngestService(client, repo, source_name=account)
