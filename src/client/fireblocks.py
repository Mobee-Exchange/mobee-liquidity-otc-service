from decimal import Decimal
from pathlib import Path
from typing import Any

from fireblocks_sdk import FireblocksSDK

from src.core.config import settings
from src.domain.entity.fireblocks import (
    FIREBLOCKS_NETWORK,
    FireblocksAssetBalance,
    FireblocksVault,
)
from src.domain.interface.balance import AssetRef


class FireblocksError(Exception):
    """Raised when a Fireblocks API call fails."""


def _decimal(value: Any) -> Decimal:
    if value in (None, ""):
        return Decimal("0")
    return Decimal(str(value))


class FireblocksClient:
    """Reads vault accounts and balances from Fireblocks."""

    def __init__(
        self,
        api_key: str,
        secret_key: str,
        *,
        base_url: str = "https://api.fireblocks.io",
    ) -> None:
        self._sdk = FireblocksSDK(
            private_key=_resolve_secret(secret_key),
            api_key=api_key,
            api_base_url=base_url,
        )

    @property
    def network(self) -> str:
        return FIREBLOCKS_NETWORK

    def _asset_balances(
        self, vault: FireblocksVault, assets: list[dict[str, Any]]
    ) -> list[FireblocksAssetBalance]:
        return [
            FireblocksAssetBalance(
                vault_id=vault.vault_id,
                vault_name=vault.vault_name,
                asset_id=asset.get("id", ""),
                total=_decimal(asset.get("total")),
                available=_decimal(asset.get("available")),
                pending=_decimal(asset.get("pending")),
                frozen=_decimal(asset.get("frozen")),
                locked_amount=_decimal(asset.get("lockedAmount")),
            )
            for asset in assets
        ]
    
    def get_vault_infos(self, vault_id: int) -> list[FireblocksAssetBalance]:
        """All asset balances inside a single vault account."""
        return self.get_vault_balances(vault_id)

    def get_vault_balances(self, vault_id: int) -> list[FireblocksAssetBalance]:
        """All asset balances inside a single vault account."""
        try:
            account = self._sdk.get_vault_account_by_id(str(vault_id))
        except Exception as exc:  # SDK raises bare Exceptions / API errors
            raise FireblocksError(f"Failed to fetch vault {vault_id}: {exc}") from exc

        vault = FireblocksVault(
            vault_id=str(account.get("id", vault_id)),
            vault_name=account.get("name", ""),
        )
        return self._asset_balances(vault, account.get("assets", []))

    def get_asset_balance(
        self, vault_id: str, asset_id: str
    ) -> FireblocksAssetBalance | None:
        """Balance of a single asset in a vault, or ``None`` if absent."""
        for balance in self.get_vault_balances(vault_id):
            if balance.asset_id == asset_id:
                return balance
        return None

    def get_balance(
        self, account: str, asset: AssetRef
    ) -> FireblocksAssetBalance | None:
        """BalanceProvider port. ``account`` is the vault id and
        ``asset.identifier`` is the Fireblocks asset id."""
        if asset.identifier is None:
            raise FireblocksError("AssetRef.identifier (asset id) is required")
        return self.get_asset_balance(account, asset.identifier)

    def list_vaults(self, page_size: int = 200) -> list[FireblocksVault]:
        """All vault accounts, following pagination."""
        from fireblocks_sdk import PagedVaultAccountsRequestFilters

        vaults: list[FireblocksVault] = []
        after: str | None = None
        while True:
            try:
                page = self._sdk.get_vault_accounts_with_page_info(
                    PagedVaultAccountsRequestFilters(limit=page_size, after=after)
                )
            except Exception as exc:
                raise FireblocksError(f"Failed to list vaults: {exc}") from exc

            for account in page.get("accounts", []):
                vaults.append(
                    FireblocksVault(
                        vault_id=str(account.get("id", "")),
                        vault_name=account.get("name", ""),
                    )
                )

            after = page.get("paging", {}).get("after")
            if not after:
                break

        return vaults


def _resolve_secret(secret_key: str) -> str:
    """Accept either raw PEM contents or a path to the .pem file."""
    candidate = Path(secret_key)
    if "BEGIN" not in secret_key and candidate.is_file():
        return candidate.read_text()
    return secret_key


def build_fireblocks_client() -> FireblocksClient:
    """Build a Fireblocks client with credentials pulled from settings."""
    if not settings.fireblocks_api_key or not settings.fireblocks_secret_key:
        raise FireblocksError("Fireblocks credentials are not configured")
    return FireblocksClient(
        api_key=settings.fireblocks_api_key,
        secret_key=settings.fireblocks_secret_key,
        base_url=settings.fireblocks_base_url,
    )
