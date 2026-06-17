from decimal import Decimal

from pydantic import BaseModel, computed_field


class TokenBalance(BaseModel):
    """A wallet's balance of a single asset on a single network.

    ``raw_balance`` is the on-chain integer amount (smallest unit). The
    human-readable value is derived from ``decimals`` so callers never have to
    repeat the conversion.
    """

    network: str
    address: str
    raw_balance: int
    decimals: int
    symbol: str | None = None
    # None for the network's native coin (ETH, BNB, TRX, ...).
    token_address: str | None = None

    @computed_field
    @property
    def amount(self) -> Decimal:
        return Decimal(self.raw_balance) / (Decimal(10) ** self.decimals)

    @property
    def is_native(self) -> bool:
        return self.token_address is None

    # --- AssetHolding protocol ---
    @property
    def account(self) -> str:
        return self.address

    @property
    def asset(self) -> str:
        return self.token_address or self.symbol or "native"
