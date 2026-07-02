from enum import Enum

from src.client.evmscan import EVMScanClient, build_evm_client
from src.domain.entity.balance import TokenBalance
from src.domain.entity.evmscan import EVM_TOKENS, EVMChain, EVMTokenError
from src.domain.interface.balance import AssetRef


class EVMLiquidityService:
    """Reads EVM wallet balances by token, for one chain.

    Accepts a per-chain token enum member (``Bsc.USDT``), a symbol string
    (``"USDT"``), or a registered contract address. Wraps a single-chain
    :class:`~src.client.evmscan.EVMScanClient`.

    Etherscan returns raw integers, so decimals are mandatory: an unknown
    contract must be queried with an explicit ``decimals`` value.
    """

    def __init__(self, client: EVMScanClient) -> None:
        self.client = client
        self.chain = client.chain
        # The token enum (Ethereum/Bsc/Arbitrum/Optimism) for this chain.
        self.tokens = EVM_TOKENS[self.chain]

    def _resolve(self, token: "Enum | str", decimals: int | None) -> AssetRef:
        if not isinstance(token, str):
            # An enum member; trust its own contract + decimals.
            return token.to_asset_ref()
        member = self.tokens.resolve(token)
        if member is not None:
            return member.to_asset_ref()
        if decimals is not None:
            return AssetRef(identifier=token, decimals=decimals)
        raise EVMTokenError(
            f"Unknown token {token!r} on {self.chain.network}; use a known token "
            "or pass decimals= explicitly"
        )

    def get_balance(
        self, wallet: str, token: "Enum | str", *, decimals: int | None = None
    ) -> TokenBalance:
        """Balance of a single ``token`` held by ``wallet``.

        Known tokens resolve their contract and decimals automatically. For an
        unknown contract, pass ``decimals`` explicitly; otherwise this raises
        ``EVMTokenError``.
        """
        asset = self._resolve(token, decimals)
        return self.client.get_balance(wallet, asset)

    def get_balances(
        self, wallet: str, tokens: "list[Enum | str] | None" = None
    ) -> list[TokenBalance]:
        """Balances for ``tokens`` (defaults to every token for this chain)."""
        keys: list[Enum | str] = (
            list(tokens) if tokens is not None else list(self.tokens)
        )
        return [self.get_balance(wallet, key) for key in keys]


def build_evm_liquidity_service(chain: EVMChain) -> EVMLiquidityService:
    """Build the service for ``chain`` with a client wired from settings."""
    return EVMLiquidityService(build_evm_client(chain))
