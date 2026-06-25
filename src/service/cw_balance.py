import logging
import time
from datetime import datetime

from src.core.app_config import AppConfig, get_app_config
from src.domain.entity.ingest import LiquidityBalanceRawData
from src.domain.entity.tronscan import Tron
from src.repository.balance_ingest import BalanceIngestRepository
from src.service.tronscan import TronLiquidityService

log = logging.getLogger(__name__)

# TRC-20 tokens to query on each wallet (STBT is Ethereum-only, not applicable here).
_CW_TOKENS = [Tron.USDT, Tron.USDC]


class CWBalanceIngestService:
    """Fetches USDT/USDC balances from on-chain CW wallets (Tron) via Tronscan
    and writes them to the unified balance_ingest table."""

    def __init__(
        self,
        tron_service: TronLiquidityService,
        repo: BalanceIngestRepository,
        config: AppConfig | None = None,
    ) -> None:
        self._tron = tron_service
        self._repo = repo
        self._config = config or get_app_config()

    def ingest(self, snapshot_ts: datetime) -> int:
        wallets = self._config.service.cw_wallets
        rows = []
        for i, wallet in enumerate(wallets):
            if i > 0:
                time.sleep(1)  # stay within Tronscan rate limit between wallets
            log.info("Fetching %s (%s)…", wallet.name, wallet.address)
            for token in _CW_TOKENS:
                try:
                    tb = self._tron.get_balance(wallet.address, token)
                    if tb is None:
                        log.warning("  %s %s returned None", wallet.name, token.name)
                        continue
                    rows.append(LiquidityBalanceRawData(
                        timestamp=snapshot_ts,
                        platform="cw",
                        source_name=wallet.name.upper(),
                        currency=tb.symbol or token.name,
                        network="TRON",
                        amount=tb.amount,
                    ))
                    log.info("  %s %s = %s", wallet.name, token.name, tb.amount)
                except Exception as exc:
                    log.error("  %s %s failed: %s", wallet.name, token.name, exc)

        if rows:
            self._repo.insert_total_balance(rows)
            log.info("Inserted %d CW balance rows", len(rows))
        else:
            log.warning("No CW balance rows fetched")
        return len(rows)

    def run(self) -> int:
        self._repo.ensure_table()
        snapshot_ts = datetime.now()
        log.info("Snapshot timestamp: %s", snapshot_ts)
        return self.ingest(snapshot_ts)
