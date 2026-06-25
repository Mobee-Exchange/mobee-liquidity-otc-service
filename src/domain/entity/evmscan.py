from enum import Enum
from typing import Final

from pydantic import BaseModel, ConfigDict

from src.domain.interface.balance import AssetRef


class EVMChain(Enum):
    """Supported EVM block-explorer endpoints.

    ``chain_id`` is set for Etherscan V2 (single multichain endpoint that
    selects the network via the ``chainid`` query param). It stays ``None`` for
    legacy V1 explorers that expose a dedicated host per network.
    """

    ethereum = ("ethereum", "ETH", "https://api.etherscan.io/v2/api", 1)
    bsc = ("bsc", "BNB", "https://api.bscscan.com/api", None)
    arbitrum = ("arbitrum", "ETH", "https://api.arbiscan.io/api", None)
    optimism = ("optimism", "ETH", "https://api-optimistic.etherscan.io/api", None)

    def __init__(
        self,
        network: str,
        native_symbol: str,
        base_url: str,
        chain_id: int | None,
    ) -> None:
        self.network = network
        self.native_symbol = native_symbol
        self.base_url = base_url
        self.chain_id = chain_id


class EVMTokenError(Exception):
    """Raised when a token cannot be resolved for a chain."""


class EVMToken(BaseModel):
    """A known EVM asset: a human-friendly ``symbol`` mapped to its ERC-20
    contract address. ``contract`` is ``None`` for the native coin.

    Frozen so it is safe to use as an enum value. Unlike Tron, Etherscan returns
    raw integer balances, so ``decimals`` here is authoritative — a wrong value
    silently yields a wrong amount.
    """

    model_config = ConfigDict(frozen=True)

    symbol: str
    contract: str | None = None
    decimals: int = 18
    native: bool = False

    def to_asset_ref(self) -> AssetRef:
        return AssetRef(
            identifier=self.contract,
            decimals=self.decimals,
            symbol=self.symbol,
            native=self.native,
        )


def _native(chain: EVMChain) -> EVMToken:
    return EVMToken(symbol=chain.native_symbol, contract=None, decimals=18, native=True)


class _ChainTokens:
    """Mixin shared by the per-chain token enums below.

    Holds the lookup/conversion helpers so each chain enum only declares its
    members. Access tokens like ``Ethereum.USDT``.
    """

    @property
    def token(self) -> EVMToken:
        return self.value  # type: ignore[attr-defined]

    def to_asset_ref(self) -> AssetRef:
        return self.value.to_asset_ref()  # type: ignore[attr-defined]

    @classmethod
    def resolve(cls, key: str) -> "_ChainTokens | None":
        """Find a member by symbol (case-insensitive) or contract address."""
        for member in cls:  # type: ignore[attr-defined]
            contract = member.value.contract
            if key.upper() == member.name or (
                contract is not None and key.lower() == contract.lower()
            ):
                return member
        return None


# Per-chain token enums (native coin + USDT + USDC). Contracts and decimals are
# verified against the issuers (Tether / Circle). Note BSC USDT and USDC use 18
# decimals, and Arbitrum/Optimism use Circle's *native* USDC.
class Ethereum(_ChainTokens, Enum):
    ETH = _native(EVMChain.ethereum)
    USDT = EVMToken(
        symbol="USDT", contract="0xdAC17F958D2ee523a2206206994597C13D831ec7", decimals=6
    )
    USDC = EVMToken(
        symbol="USDC", contract="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", decimals=6
    )
    STBT = EVMToken(
        symbol="STBT", contract="0x530824DA86689C9C17CdC2871Ff29B058345b44a", decimals=18
    )


class Bsc(_ChainTokens, Enum):
    BNB = _native(EVMChain.bsc)
    USDT = EVMToken(
        symbol="USDT", contract="0x55d398326f99059fF775485246999027B3197955", decimals=18
    )
    USDC = EVMToken(
        symbol="USDC", contract="0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d", decimals=18
    )


class Arbitrum(_ChainTokens, Enum):
    ETH = _native(EVMChain.arbitrum)
    USDT = EVMToken(
        symbol="USDT", contract="0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9", decimals=6
    )
    USDC = EVMToken(
        symbol="USDC", contract="0xaf88d065e77c8cC2239327C5EDb3A432268e5831", decimals=6
    )


class Optimism(_ChainTokens, Enum):
    ETH = _native(EVMChain.optimism)
    USDT = EVMToken(
        symbol="USDT", contract="0x94b008aA00579c1307B0EF2c499aD98a8ce58e58", decimals=6
    )
    USDC = EVMToken(
        symbol="USDC", contract="0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85", decimals=6
    )


# Maps a chain to its token enum, so a per-chain service can enumerate/resolve.
EVM_TOKENS: Final[dict[EVMChain, type[_ChainTokens]]] = {
    EVMChain.ethereum: Ethereum,
    EVMChain.bsc: Bsc,
    EVMChain.arbitrum: Arbitrum,
    EVMChain.optimism: Optimism,
}
