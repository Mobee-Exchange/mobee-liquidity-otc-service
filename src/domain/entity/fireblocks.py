from decimal import Decimal
from typing import Final

from pydantic import BaseModel

FIREBLOCKS_NETWORK: Final[str] = "fireblocks"


# Fireblocks asset IDs encode the chain into the ticker, but not regularly:
# most are "<SYMBOL>_<CHAIN>" (USDT_BSC, USDC_ARB), some legacy ones are
# "<NATIVE>_<SYMBOL>_<hash>" (TRX_USDT_S2UZ), and natives are bare (ETH, TRX).
# Fireblocks rows always carry network="FIREBLOCKS" (the custody platform), so
# we only strip the chain encoding to recover the clean base ticker.

# Known chain suffixes (last "_" segment) that should be stripped off the ticker.
_FB_CHAIN_SUFFIXES: set[str] = {
    "ETH", "ERC20", "BSC", "BEP20", "ARB", "OP", "OPT",
    "TRX", "TRON", "TRC20", "MATIC", "POLYGON", "SOL", "AVAX",
}

# Explicit currency overrides for irregular asset IDs the suffix rule can't parse
# (e.g. chain-as-prefix). Extend this as you encounter new asset IDs in vaults.
_FB_CURRENCY_OVERRIDES: dict[str, str] = {
    "TRX_USDT_S2UZ": "USDT",
}


def normalize_fireblocks_asset(asset_id: str) -> str:
    """Return the clean base ticker for a Fireblocks ``asset_id``.

    e.g. ``USDT_BSC`` -> ``USDT``, ``TRX_USDT_S2UZ`` -> ``USDT``, ``ETH`` -> ``ETH``.
    Resolution: explicit override -> strip a known ``_<CHAIN>`` suffix -> as-is.
    """
    if asset_id in _FB_CURRENCY_OVERRIDES:
        return _FB_CURRENCY_OVERRIDES[asset_id]
    if "_" in asset_id:
        suffix = asset_id.rsplit("_", 1)[-1].upper()
        if suffix in _FB_CHAIN_SUFFIXES:
            return asset_id[: -(len(suffix) + 1)].upper()
    return asset_id.upper()


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
