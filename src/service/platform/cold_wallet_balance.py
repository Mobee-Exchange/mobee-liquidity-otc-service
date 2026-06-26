import logging
import time
from datetime import datetime

from src.core.app_config import AppConfig, get_app_config
from src.domain.entity.evmscan import EVMChain
from src.domain.entity.ingest import LiquidityBalanceRawData
from src.domain.entity.tronscan import TRON_NETWORK
from src.repository.balance_ingest import BalanceIngestRepository
from src.service.platform.evmscan import build_evm_liquidity_service
from src.service.platform.tronscan import build_tron_liquidity_service

log = logging.getLogger(__name__)


def _build_service_for(network: str):
    """Map a config network key (e.g. "Ethereum", "Tron") to a liquidity service.

    Both EVM and Tron services expose ``get_balance(address, symbol)``, which
    resolves the symbol to its known contract via the per-network token enum.
    """
    key = network.strip().lower()
    if key == TRON_NETWORK:  # "tron"
        return build_tron_liquidity_service()
    for chain in EVMChain:
        if chain.network == key:
            return build_evm_liquidity_service(chain)
    raise ValueError(f"Unsupported cold-wallet network: {network!r}")


class ColdWalletBalanceIngestService:
    """Fetches cold-wallet balances per network/address for the tokens listed in
    config, and writes them to the unified balance_ingest table.

    Config shape (configurations/config.yaml -> ServiceConfig.ColdWallets):

        ColdWallets:
          Ethereum:
            - {Name: "...", Address: "0x...", Token: ["USDT", "USDC"]}
          Tron:
            - {Name: "...", Address: "T...",  Token: ["USDT", "USDC"]}

    Tokens are resolved to their known contract via the per-network enum (not by
    symbol string), so messy on-chain display symbols and scam look-alikes are
    handled correctly. The clean config symbol is stored as ``currency``.
    """

    def __init__(self, repo: BalanceIngestRepository, config: AppConfig | None = None) -> None:
        self._repo = repo
        self._config = config or get_app_config()

    def ingest(self, snapshot_ts: datetime) -> int:
        rows: list[LiquidityBalanceRawData] = []
        for network, wallets in self._config.cold_wallets.items():
            try:
                service = _build_service_for(network)
            except Exception as exc:
                log.error("Network %s: cannot init service: %s", network, exc)
                continue

            net_label = network.strip().upper()
            log.info("Network %s: %d wallet(s)", net_label, len(wallets))

            for i, wallet in enumerate(wallets):
                if i > 0:
                    time.sleep(0.5)  # stay within explorer rate limits between wallets
                for symbol in wallet.tokens:
                    try:
                        tb = service.get_balance(wallet.address, symbol)
                    except Exception as exc:
                        log.error("  [%s] %s %s failed: %s", net_label, wallet.name, symbol, exc)
                        continue
                    if tb is None:
                        log.warning("  [%s] %s %s returned None", net_label, wallet.name, symbol)
                        continue
                    rows.append(LiquidityBalanceRawData(
                        timestamp=snapshot_ts,
                        platform="Cold Wallet",
                        source_name=wallet.name,
                        currency=symbol.upper(),
                        network=net_label,
                        amount=tb.amount,
                    ))
                    log.info("  [%s] %s %s = %s", net_label, wallet.name, symbol, tb.amount)

        if rows:
            self._repo.insert_total_balance(rows)
            log.info("Inserted %d cold-wallet balance rows", len(rows))
        else:
            log.warning("No cold-wallet balance rows fetched")
        return len(rows)

    def run(self) -> int:
        self._repo.ensure_table()
        snapshot_ts = datetime.now()
        log.info("Snapshot timestamp: %s", snapshot_ts)
        return self.ingest(snapshot_ts)


def build_cold_wallet_ingest_service(repo: BalanceIngestRepository) -> ColdWalletBalanceIngestService:
    return ColdWalletBalanceIngestService(repo)
