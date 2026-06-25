import logging
from datetime import datetime

from src.client.fireblocks import FireblocksClient, FireblocksError, build_fireblocks_client
from src.core.app_config import AppConfig, get_app_config
from src.domain.entity.ingest import LiquidityBalanceRawData
from src.repository.balance_ingest import BalanceIngestRepository

log = logging.getLogger(__name__)


class FireblocksBalanceIngestService:
    """Fetches balances for configured Fireblocks vault IDs and writes them
    to the unified balance_ingest table.

    Vault names are resolved live from the Fireblocks API — no hardcoded mapping.
    Vault IDs are loaded from configurations/config.yaml (ServiceConfig.FireblocksVaultIds).
    """

    def __init__(
        self,
        client: FireblocksClient,
        repo: BalanceIngestRepository,
        config: AppConfig | None = None,
    ) -> None:
        self._client = client
        self._repo = repo
        self._config = config or get_app_config()

    def ingest(self, snapshot_ts: datetime) -> int:
        rows = []
        for vault_id in self._config.service.fireblocks_vault_ids:
            vault_id = str(vault_id)
            try:
                balances = self._client.get_vault_infos(vault_id)
                print(f"Fetched {len(balances)} balances for vault {vault_id}")
            except FireblocksError as exc:
                log.error("Vault %s failed: %s", vault_id, exc)
                continue

            for b in balances:
                if b.total == 0:
                    continue  # skip empty asset slots
                rows.append(LiquidityBalanceRawData(
                    timestamp=snapshot_ts,
                    platform="fireblocks",
                    source_name=b.vault_name.upper(),
                    currency=b.asset_id,
                    network="FIREBLOCKS",
                    amount=b.total,
                ))
                log.info("  vault=%s (%s) %s = %s", vault_id, b.vault_name, b.asset_id, b.total)

        if rows:
            self._repo.insert_total_balance(rows)
            log.info("Inserted %d Fireblocks balance rows", len(rows))
        else:
            log.warning("No Fireblocks balance rows fetched")
        return len(rows)

    def run(self) -> int:
        self._repo.ensure_table()
        snapshot_ts = datetime.now()
        log.info("Snapshot timestamp: %s", snapshot_ts)
        return self.ingest(snapshot_ts)


def build_fireblocks_ingest_service(repo: BalanceIngestRepository) -> FireblocksBalanceIngestService:
    return FireblocksBalanceIngestService(build_fireblocks_client(), repo)
