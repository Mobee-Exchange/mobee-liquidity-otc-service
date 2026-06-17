from typing import Any

import requests

from src.core.config import get_settings
from src.domain.entity.balance import TokenBalance
from src.domain.entity.tronscan import (
    TRON_NATIVE_SYMBOL,
    TRON_NETWORK,
    TRONSCAN_BASE_URL,
)
from src.domain.interface.balance import AssetRef

# Tronscan reports the native coin as the "trx" pseudo-token in the tokens list.
_TRX_TOKEN_ID = "_"


class TronscanError(Exception):
    """Raised when the Tronscan API returns an error."""


class TronscanClient:
    """Reads TRC-20 / TRX balances from the Tronscan API."""

    def __init__(self, api_key: str, *, timeout: int = 10) -> None:
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "TRON-PRO-API-KEY": api_key,
                "Accept": "application/json",
            }
        )

    @property
    def network(self) -> str:
        return TRON_NETWORK

    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        try:
            response = self.session.get(
                f"{TRONSCAN_BASE_URL}/{path}", params=params, timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as exc:
            raise TronscanError(f"HTTP request failed: {exc}") from exc

    def _list_tokens(
        self, address: str, start: int = 0, limit: int = 200
    ) -> list[dict[str, Any]]:
        data = self._get(
            "account/tokens",
            {"address": address, "start": start, "limit": limit},
        )
        return data.get("data", [])

    @staticmethod
    def _to_balance(address: str, token: dict[str, Any]) -> TokenBalance:
        token_id = token.get("tokenId")
        is_native = token_id == _TRX_TOKEN_ID or token.get("tokenAbbr") == "trx"
        return TokenBalance(
            network=TRON_NETWORK,
            address=address,
            raw_balance=int(token.get("balance", 0)),
            decimals=int(token.get("tokenDecimal", 0)),
            symbol=token.get("tokenAbbr") or (TRON_NATIVE_SYMBOL if is_native else None),
            token_address=None if is_native else token_id,
        )

    def get_all_balances(self, address: str) -> list[TokenBalance]:
        """All token balances held by ``address`` (native TRX included)."""
        return [self._to_balance(address, token) for token in self._list_tokens(address)]

    def get_token_balance(self, address: str, token_address: str) -> TokenBalance:
        """Balance of a single TRC-20 token; zero balance if not held."""
        for token in self._list_tokens(address):
            if token.get("tokenId") == token_address:
                return self._to_balance(address, token)

        return TokenBalance(
            network=TRON_NETWORK,
            address=address,
            raw_balance=0,
            decimals=0,
            token_address=token_address,
        )

    def get_balance(self, account: str, asset: AssetRef) -> TokenBalance | None:
        """BalanceProvider port. Decimals come from the Tronscan response, so
        ``asset.decimals`` is ignored."""
        if asset.native:
            for balance in self.get_all_balances(account):
                if balance.is_native:
                    return balance
            return None
        if asset.identifier is None:
            raise TronscanError("AssetRef.identifier is required for token balances")
        return self.get_token_balance(account, asset.identifier)


def build_tronscan_client() -> TronscanClient:
    """Build a Tronscan client with the API key pulled from settings."""
    return TronscanClient(api_key=get_settings().tronscan_api_key)
