import logging
from collections import defaultdict
from datetime import datetime
from decimal import Decimal

from src.client.gate import GateioClients
from src.core.config import settings
from src.domain.entity.ingest import LiquidityBalanceRawData
from src.repository.balance_ingest import BalanceIngestRepository

log = logging.getLogger(__name__)

# Orders currently contributing to balance (exclude settled / closed).
_ACTIVE_STATUSES = {"PROCESSING", "SETTLEMENT_PROCESSING"}
_PAGE_LIMIT = 100  # matches the client's hardcoded limit


class GateIngestService:
    """Fetches Gate.io Dual Investment orders, keeps the active ones, sums
    invest_amount per invest currency, and writes one balance_ingest row per
    currency. ``source_name`` records which account ("main"/"sub")."""

    def __init__(
        self,
        client: GateioClients,
        repo: BalanceIngestRepository,
        source_name: str = "main",
    ) -> None:
        self._client = client
        self._repo = repo
        self._source_name = source_name

    def _fetch_orders(self) -> list[dict]:
        """All dual-investment orders, following pagination."""
        orders: list[dict] = []
        page = 1
        while True:
            resp = self._client.get_dual_investment_orders(page=page)
            if resp.status_code != 200:
                log.error("Gate dual orders page=%d failed: %s %s",
                          page, resp.status_code, resp.text)
                break
            batch = resp.json()
            if not isinstance(batch, list):
                log.error("Unexpected Gate response (expected a list): %r", batch)
                break
            orders.extend(batch)
            if len(batch) < _PAGE_LIMIT:
                break
            page += 1
        return orders

    def ingest(self, snapshot_ts: datetime) -> int:
        totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        for order in self._fetch_orders():
            if order.get("status") not in _ACTIVE_STATUSES:
                continue  # skip settled/closed orders — not part of the balance
            coin = order["invest_currency"]
            totals[coin] += Decimal(str(order["invest_amount"]))

        rows = [
            LiquidityBalanceRawData(
                timestamp=snapshot_ts,
                platform="Gate",
                source_name=self._source_name.upper(),
                currency=coin,
                amount=amount,
            )
            for coin, amount in totals.items()
        ]

        if rows:
            self._repo.insert_total_balance(rows)
            log.info("Inserted %d Gate rows", len(rows))
            for r in rows:
                log.info("  %s = %s", r.currency, r.amount)
        else:
            log.warning("No active Gate dual-investment orders found")
        return len(rows)

    def run(self) -> int:
        snapshot_ts = datetime.now()
        log.info("Snapshot timestamp: %s", snapshot_ts)
        return self.ingest(snapshot_ts)


_GATE_CREDS = {
    "main": ("gate_main_api_key", "gate_main_secret"),
    "sub": ("gate_sub_api_key", "gate_sub_secret"),
}


def build_gate_ingest_service(
    repo: BalanceIngestRepository, *, account: str
) -> GateIngestService:
    """Build the Gate DCI ingest service for the "main" or "sub" account.

    Each account uses its own API key/secret; source_name is the account
    ("main" / "sub").
    """
    try:
        key_attr, secret_attr = _GATE_CREDS[account]
    except KeyError:
        raise ValueError(f"Unknown Gate account {account!r}; expected 'main' or 'sub'")
    client = GateioClients(getattr(settings, key_attr), getattr(settings, secret_attr))
    return GateIngestService(client, repo, source_name=account)
