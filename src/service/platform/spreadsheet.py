import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation

from src.client.spreadsheet import SpreadsheetClient
from src.core.config import settings
from src.domain.entity.ingest import LiquidityBalanceRawData
from src.repository.balance_ingest import BalanceIngestRepository

log = logging.getLogger(__name__)


class SpreadsheetIngestService:
    """Reads ClientBalance, BalanceIDR and TradingBalance tabs from Google Sheets
    and writes to the unified balance_ingest table via BalanceIngestRepository."""

    def __init__(self, sheets: SpreadsheetClient, repo: BalanceIngestRepository) -> None:
        self._sheets = sheets
        self._repo = repo
        self._settings = settings

    def _to_str(self, value) -> str:
        s = str(value).strip()
        return "" if s.lower() in ("nan", "none", "") else s

    def _to_decimal(self, value, label: str) -> Decimal | None:
        cleaned = str(value).replace(",", "").strip()
        if not cleaned or cleaned.lower() in ("nan", "none"):
            log.warning("Empty value for '%s'", label)
            return None
        try:
            return Decimal(cleaned)
        except InvalidOperation:
            log.warning("Cannot parse %r as Decimal for '%s'", value, label)
            return None

    def ingest_client_balances(self, snapshot_ts: datetime) -> int:
        log.info("Reading tab '%s'…", self._settings.balance_ingest_tab_client)
        df = self._sheets.read(self._settings.balance_ingest_spreadsheet_url, self._settings.balance_ingest_tab_client)
        df.columns = [c.strip() for c in df.columns]

        rows = []
        for i, row in df.iterrows():
            client_name = self._to_str(row["client_name"])
            if not client_name:
                log.warning("Row %d: skipping — empty client_name", i)
                continue
            amount = self._to_decimal(row["balance"], "balance")
            if amount is None:
                log.warning("Row %d: skipping — unreadable balance for '%s'", i, client_name)
                continue
            rows.append(LiquidityBalanceRawData(
                timestamp=snapshot_ts,
                platform="Client Balance",
                source_name=client_name,
                currency=self._to_str(row["currency"]),
                amount=amount,
            ))

        if rows:
            self._repo.insert_total_balance(rows)
            log.info("Inserted %d Client Balance rows", len(rows))
        else:
            log.warning("No valid rows in '%s' tab", self._settings.balance_ingest_tab_client)
        return len(rows)

    def ingest_idr_bank_balances(self, snapshot_ts: datetime) -> int:
        log.info("Reading tab '%s'…", self._settings.balance_ingest_tab_idr_bank)
        df = self._sheets.read(self._settings.balance_ingest_spreadsheet_url, self._settings.balance_ingest_tab_idr_bank)
        df.columns = [c.strip() for c in df.columns]

        rows = []
        for i, row in df.iterrows():
            bank = self._to_str(row["bank"])
            if not bank:
                log.warning("Row %d: skipping — empty bank", i)
                continue
            amount = self._to_decimal(row["balance"], "balance")
            if amount is None:
                log.warning("Row %d: skipping — unreadable balance for bank '%s'", i, bank)
                continue
            rows.append(LiquidityBalanceRawData(
                timestamp=snapshot_ts,
                platform=bank,
                source_name=self._to_str(row["account"]),
                currency="IDR",
                amount=amount,
            ))

        if rows:
            self._repo.insert_total_balance(rows)
            log.info("Inserted %d idr_bank rows", len(rows))
        else:
            log.warning("No valid rows in '%s' tab", self._settings.balance_ingest_tab_idr_bank)
        return len(rows)

    def ingest_trading_balances(self, snapshot_ts: datetime) -> int:
        log.info("Reading tab '%s'…", self._settings.balance_ingest_tab_trading)
        df = self._sheets.read(self._settings.balance_ingest_spreadsheet_url, self._settings.balance_ingest_tab_trading)
        df.columns = [c.strip() for c in df.columns]

        rows = []
        for i, row in df.iterrows():
            currency = self._to_str(row["currency"])
            if not currency:
                log.warning("Row %d: skipping — empty currency", i)
                continue
            amount = self._to_decimal(row["balance"], "balance")
            if amount is None:
                log.warning("Row %d: skipping — unreadable balance for '%s'", i, currency)
                continue
            rows.append(LiquidityBalanceRawData(
                timestamp=snapshot_ts,
                platform="Trading Balance",
                source_name="Total",
                currency=currency,
                amount=amount,
            ))

        if rows:
            self._repo.insert_total_balance(rows)
            log.info("Inserted %d Trading Balance rows", len(rows))
        else:
            log.warning("No valid rows in '%s' tab", self._settings.balance_ingest_tab_trading)
        return len(rows)

    def run(self, *, full: bool = False, snapshot_ts: datetime | None = None) -> dict[str, int]:
        snapshot_ts = snapshot_ts or datetime.now()
        log.info("Snapshot timestamp: %s", snapshot_ts)

        return {
            "client_balance": self.ingest_client_balances(snapshot_ts),
            "idr_bank": self.ingest_idr_bank_balances(snapshot_ts),
            "trading_balance": self.ingest_trading_balances(snapshot_ts),
        }
