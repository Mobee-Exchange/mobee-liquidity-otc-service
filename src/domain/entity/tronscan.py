from enum import Enum
from typing import Final

from pydantic import BaseModel, ConfigDict

from src.domain.interface.balance import AssetRef

# Tron has a single mainnet explorer, so the network label is a constant rather
# than an enum like the EVM family.
TRON_NETWORK: Final[str] = "tron"
TRON_NATIVE_SYMBOL: Final[str] = "TRX"
TRON_NATIVE_DECIMALS: Final[int] = 6
TRONSCAN_BASE_URL: Final[str] = "https://apilist.tronscan.org/api"


class TronToken(BaseModel):
    """A known Tron asset: a human-friendly ``symbol`` mapped to its TRC-20
    contract address. ``contract`` is ``None`` for the native coin (TRX).

    Frozen so it is safe to use as an :class:`Tron` enum value. ``decimals`` is
    canonical reference data; Tronscan returns decimals on every balance
    response, so it is not relied on for amount conversion.
    """

    model_config = ConfigDict(frozen=True)

    symbol: str
    contract: str | None = None
    decimals: int = TRON_NATIVE_DECIMALS
    native: bool = False

    def to_asset_ref(self) -> AssetRef:
        return AssetRef(
            identifier=self.contract,
            decimals=self.decimals,
            symbol=self.symbol,
            native=self.native,
        )


class Tron(Enum):
    """Known Tron assets. Access like ``Tron.USDT``.

    Decimals are documented for reference; Tronscan returns the authoritative
    value per balance. Add a member to track a new token.
    """

    TRX = TronToken(symbol=TRON_NATIVE_SYMBOL, contract=None, decimals=6, native=True)
    USDT = TronToken(
        symbol="USDT", contract="TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t", decimals=6
    )
    USDC = TronToken(
        symbol="USDC", contract="TEkxiTehnzSmSe2XqrBj4w32RUN966rdz8", decimals=6
    )

    @property
    def token(self) -> TronToken:
        return self.value

    def to_asset_ref(self) -> AssetRef:
        return self.value.to_asset_ref()

    @classmethod
    def resolve(cls, key: str) -> "Tron | None":
        """Find a member by symbol (case-insensitive) or contract address."""
        for member in cls:
            if key.upper() == member.name or key == member.value.contract:
                return member
        return None
