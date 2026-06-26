import logging
from datetime import datetime

from src.client.fireblocks import FireblocksClient, FireblocksError, build_fireblocks_client
from src.core.app_config import AppConfig, get_app_config
from src.domain.entity.ingest import LiquidityBalanceRawData
from src.repository.balance_ingest import BalanceIngestRepository
from src.repository.liquidity import LiquidityRepository

log = logging.getLogger(__name__)


class FireblocksBalanceIngestService:
    """Fetches balances for configured Fireblocks vault IDs and writes them
    to the unified balance_ingest table.

    Vaults (name + id) are loaded from configurations/config.yaml
    (ServiceConfig.FireblocksVaults); the configured name is used as source_name.

    Currencies are resolved from Postgres (LiquidityRepository) — the Fireblocks
    asset_id (e.g. "USDT_BSC") maps to a clean currency_code (e.g. "USDT").
    """

    def __init__(
        self,
        client: FireblocksClient,
        repo: BalanceIngestRepository,
        config: AppConfig | None = None,
        liquidity_repo: LiquidityRepository | None = None,
    ) -> None:
        self._client = client
        self._repo = repo
        self._config = config or get_app_config()
        self._liquidity_repo = liquidity_repo

    def _load_currency_map(self) -> dict[str, str]:
        """Build {asset_id: currency_code} from Postgres.

        Uses the injected LiquidityRepository if given; otherwise opens a
        Postgres session lazily (imported here so merely importing this module
        doesn't require POSTGRES_URL).
        """
        if self._liquidity_repo is not None:
            rows = self._liquidity_repo.fetch_fireblocks_assets_with_currency()
        else:
            from src.db.postgres import SessionLocal

            session = SessionLocal()
            try:
                rows = LiquidityRepository(session).fetch_fireblocks_assets_with_currency()
            finally:
                session.close()
        return {row["asset_id"]: row["currency_code"] for row in rows}

    def ingest(self, snapshot_ts: datetime) -> int:
        currency_map = self._load_currency_map()
        rows = []
        for vault in self._config.fireblocks_vaults:
            vault_id = str(vault.id)
            try:
                balances = self._client.get_vault_infos(vault_id)
                print(f"Fetched {len(balances)} balances for vault {vault.name} ({vault_id})")
            except FireblocksError as exc:
                log.error("Vault %s (%s) failed: %s", vault.name, vault_id, exc)
                continue

            for b in balances:
                if b.total == 0:
                    continue  # skip empty asset slots
                currency = currency_map.get(b.asset_id)
                if currency is None:
                    log.warning("No currency_code for Fireblocks asset_id %r; storing as-is", b.asset_id)
                    currency = b.asset_id
                rows.append(LiquidityBalanceRawData(
                    timestamp=snapshot_ts,
                    platform="Fireblocks",
                    source_name=vault.name,
                    currency=currency,
                    amount=b.total,
                ))
                log.info("  vault=%s (%s) %s -> %s = %s",
                         vault_id, vault.name, b.asset_id, currency, b.total)

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
