from decimal import Decimal
from typing import Protocol, runtime_checkable

from pydantic import BaseModel


class AssetRef(BaseModel):
    """Identifies an asset for a balance query in a provider-agnostic way.

    Each provider reads the fields it needs:
    - EVM explorers return raw integers, so ``decimals`` is required for tokens.
    - Tronscan and Fireblocks derive decimals from their own responses and ignore the field.
    ``identifier`` is the token contract address (EVM/Tron) or the Fireblocks
    ``asset_id``; it is ignored when ``native`` is set.
    """

    identifier: str | None = None
    decimals: int | None = None
    symbol: str | None = None
    native: bool = False


@runtime_checkable
class AssetHolding(Protocol):
    """A normalized "this account holds this much of this asset" record.

    Both :class:`~src.domain.entity.balance.TokenBalance` and
    :class:`~src.domain.entity.fireblocks.FireblocksAssetBalance` satisfy it.
    """

    @property
    def network(self) -> str: ...

    @property
    def account(self) -> str: ...

    @property
    def asset(self) -> str: ...

    @property
    def amount(self) -> Decimal: ...


@runtime_checkable
class BalanceProvider(Protocol):
    """Port: a source that reports how much of an asset an account holds.

    Implemented by every balance client (EVM, Tron, Fireblocks) so callers can
    aggregate liquidity across heterogeneous sources without caring which one
    they are talking to.
    """

    @property
    def network(self) -> str: ...

    def get_balance(self, account: str, asset: AssetRef) -> AssetHolding | None: ...
