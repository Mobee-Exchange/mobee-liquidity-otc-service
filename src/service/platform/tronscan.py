from src.client.tronscan import TronscanClient, build_tronscan_client
from src.domain.entity.balance import TokenBalance
from src.domain.entity.tronscan import Tron, TronToken


class TronLiquidityService:
    """Reads Tron wallet balances by token.

    Accepts a :class:`~src.domain.entity.tronscan.Tron` member (``Tron.USDT``),
    a symbol string (``"USDT"``), or a raw TRC-20 contract address. Wraps a
    :class:`~src.client.tronscan.TronscanClient`.
    """

    def __init__(self, client: TronscanClient) -> None:
        self.client = client

    @staticmethod
    def _resolve(token: "Tron | str") -> TronToken:
        if isinstance(token, Tron):
            return token.value
        member = Tron.resolve(token)
        if member is not None:
            return member.value
        # Unknown string: treat as a raw TRC-20 contract (Tronscan returns the
        # authoritative decimals on the balance response).
        return TronToken(symbol=token, contract=token)

    def get_balance(self, wallet: str, token: "Tron | str") -> TokenBalance | None:
        """Balance of a single ``token`` held by ``wallet``.

        Returns ``None`` only when a native-coin balance cannot be located;
        an unheld TRC-20 token resolves to a zero balance (per the client).
        """
        asset = self._resolve(token).to_asset_ref()
        return self.client.get_balance(wallet, asset)

    def get_balances(
        self, wallet: str, tokens: "list[Tron | str] | None" = None
    ) -> list[TokenBalance]:
        """Balances for ``tokens`` (defaults to every :class:`Tron` member).

        Native-coin lookups that return ``None`` are dropped from the result.
        """
        keys: list[Tron | str] = list(tokens) if tokens is not None else list(Tron)
        balances = [self.get_balance(wallet, key) for key in keys]
        return [balance for balance in balances if balance is not None]

    def get_all_balances(self, wallet: str) -> list[TokenBalance]:
        """Every asset the wallet holds, as reported by Tronscan (native TRX
        included), regardless of whether it is a known token."""
        return self.client.get_all_balances(wallet)


def build_tron_liquidity_service() -> TronLiquidityService:
    """Build the service with a Tronscan client wired from settings."""
    return TronLiquidityService(build_tronscan_client())
