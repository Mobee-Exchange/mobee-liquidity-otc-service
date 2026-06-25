import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation

from src.client.spreadsheet import SpreadsheetClient
from src.core.config import get_settings
from src.domain.entity.ingest import LiquidityBalanceRawData
from src.repository.balance_ingest import BalanceIngestRepository

log = logging.getLogger(__name__)


class SpreadsheetBalanceIngestService:
    """Reads ClientBalance and BalanceIDR tabs from Google Sheets and writes
    to the unified balance_ingest table via BalanceIngestRepository."""

    def __init__(self, sheets: SpreadsheetClient, repo: BalanceIngestRepository) -> None:
        self._sheets = sheets
        self._repo = repo

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
        s = get_settings()
        log.info("Reading tab '%s'…", s.balance_ingest_tab_client)
        df = self._sheets.read(s.balance_ingest_spreadsheet_url, s.balance_ingest_tab_client)
        df.columns = [c.strip() for c in df.columns]

        rows = []
        for i, row in df.iterrows():
            client_name = self._to_str(row["client_name"]).upper()
            if not client_name:
                log.warning("Row %d: skipping — empty client_name", i)
                continue
            amount = self._to_decimal(row["balance"], "balance")
            if amount is None:
                log.warning("Row %d: skipping — unreadable balance for '%s'", i, client_name)
                continue
            rows.append(LiquidityBalanceRawData(
                timestamp=snapshot_ts,
                platform="client_balance",
                source_name=client_name,
                currency=self._to_str(row["currency"]),
                network="",
                amount=amount,
            ))

        if rows:
            self._repo.insert_total_balance(rows)
            log.info("Inserted %d client_balance rows", len(rows))
        else:
            log.warning("No valid rows in '%s' tab", s.balance_ingest_tab_client)
        return len(rows)

    def ingest_idr_bank_balances(self, snapshot_ts: datetime) -> int:
        s = get_settings()
        log.info("Reading tab '%s'…", s.balance_ingest_tab_idr_bank)
        df = self._sheets.read(s.balance_ingest_spreadsheet_url, s.balance_ingest_tab_idr_bank)
        df.columns = [c.strip() for c in df.columns]

        rows = []
        for i, row in df.iterrows():
            bank = self._to_str(row["bank"]).upper()
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
                network="",
                amount=amount,
            ))

        if rows:
            self._repo.insert_total_balance(rows)
            log.info("Inserted %d idr_bank rows", len(rows))
        else:
            log.warning("No valid rows in '%s' tab", s.balance_ingest_tab_idr_bank)
        return len(rows)

    def run(self, *, full: bool = False) -> dict[str, int]:
        self._repo.ensure_table()
        if full:
            log.info("--full: truncating balance_ingest")
            self._repo.truncate()

        snapshot_ts = datetime.now()
        log.info("Snapshot timestamp: %s", snapshot_ts)

        return {
            "client_balance": self.ingest_client_balances(snapshot_ts),
            "idr_bank": self.ingest_idr_bank_balances(snapshot_ts),
        }
