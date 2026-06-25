import logging
import time
from datetime import datetime

from src.core.app_config import AppConfig, get_app_config
from src.domain.entity.evmscan import (
    Arbitrum,
    Bsc,
    EVMChain,
    Ethereum,
    Optimism,
)
from src.domain.entity.ingest import LiquidityBalanceRawData
from src.repository.balance_ingest import BalanceIngestRepository
from src.service.evmscan import EVMLiquidityService, build_evm_liquidity_service

log = logging.getLogger(__name__)

# Tokens to query per chain. STBT is Ethereum-only.
_CW_EVM_TOKENS = {
    EVMChain.ethereum: [Ethereum.USDT, Ethereum.USDC, Ethereum.STBT],
    EVMChain.bsc:      [Bsc.USDT,      Bsc.USDC],
    EVMChain.arbitrum: [Arbitrum.USDT, Arbitrum.USDC],
    EVMChain.optimism: [Optimism.USDT, Optimism.USDC],
}


class CWEVMBalanceIngestService:
    """Fetches USDT/USDC/STBT balances from EVM CW wallets across all supported
    chains via Etherscan-family explorers and writes them to balance_ingest."""

    def __init__(
        self,
        evm_services: list[EVMLiquidityService],
        repo: BalanceIngestRepository,
        config: AppConfig | None = None,
    ) -> None:
        self._evm_services = evm_services
        self._repo = repo
        self._config = config or get_app_config()

    def ingest(self, snapshot_ts: datetime) -> int:
        wallets = self._config.service.evm_cw_wallets
        rows = []

        for evm_service in self._evm_services:
            chain = evm_service.chain
            tokens = _CW_EVM_TOKENS.get(chain, [])
            log.info("Chain: %s (%d wallets, %d tokens)", chain.network, len(wallets), len(tokens))

            for i, wallet in enumerate(wallets):
                if i > 0:
                    time.sleep(0.5)  # stay within Etherscan rate limit between wallets
                log.info("  Fetching %s (%s)…", wallet.name, wallet.address)

                for token in tokens:
                    try:
                        tb = evm_service.get_balance(wallet.address, token)
                        rows.append(LiquidityBalanceRawData(
                            timestamp=snapshot_ts,
                            platform="cw",
                            source_name=wallet.name.upper(),
                            currency=tb.symbol or token.name,
                            network=chain.network.upper(),
                            amount=tb.amount,
                        ))
                        log.info("    %s %s = %s", wallet.name, token.name, tb.amount)
                    except Exception as exc:
                        log.error("    %s %s %s failed: %s", wallet.name, chain.network, token.name, exc)

        if rows:
            self._repo.insert_total_balance(rows)
            log.info("Inserted %d EVM CW balance rows", len(rows))
        else:
            log.warning("No EVM CW balance rows fetched")
        return len(rows)

    def run(self) -> int:
        self._repo.ensure_table()
        snapshot_ts = datetime.now()
        log.info("Snapshot timestamp: %s", snapshot_ts)
        return self.ingest(snapshot_ts)


def build_cw_evm_ingest_service(repo: BalanceIngestRepository) -> CWEVMBalanceIngestService:
    evm_services = [build_evm_liquidity_service(chain) for chain in EVMChain]
    return CWEVMBalanceIngestService(evm_services, repo)
