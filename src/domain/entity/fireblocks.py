from decimal import Decimal
from typing import Final

from pydantic import BaseModel

FIREBLOCKS_NETWORK: Final[str] = "fireblocks"


class FireblocksVault(BaseModel):
    vault_id: str
    vault_name: str


class FireblocksAssetBalance(FireblocksVault):
    """Balance of a single asset inside a Fireblocks vault account.

    Fireblocks already returns human-readable decimal strings, so amounts are
    kept as ``Decimal`` rather than raw integers.
    """

    asset_id: str
    total: Decimal
    available: Decimal
    pending: Decimal = Decimal("0")
    frozen: Decimal = Decimal("0")
    locked_amount: Decimal = Decimal("0")

    # --- AssetHolding protocol ---
    @property
    def network(self) -> str:
        return FIREBLOCKS_NETWORK

    @property
    def account(self) -> str:
        return self.vault_id

    @property
    def asset(self) -> str:
        return self.asset_id

    @property
    def amount(self) -> Decimal:
        return self.total
