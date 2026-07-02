import time

import requests

from src.core.config import settings
from src.domain.entity.balance import TokenBalance
from src.domain.entity.evmscan import EVMChain
from src.domain.interface.balance import AssetRef

_RATE_LIMIT_MESSAGE = "Max rate limit reached"


class EVMScanError(Exception):
    """Raised when an Etherscan-family API returns an error."""


class EVMScanClient:
    """Reads balances from an Etherscan-family block explorer.

    One client targets one chain. Use :func:`build_evm_client` to construct a
    client with the API key resolved from settings.
    """

    def __init__(
        self,
        chain: EVMChain,
        api_key: str,
        *,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 2.0,
    ) -> None:
        self.chain = chain
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.session = requests.Session()

    @property
    def network(self) -> str:
        return self.chain.network

    def _request(self, params: dict) -> str:
        params["apikey"] = self.api_key
        if self.chain.chain_id is not None:
            params["chainid"] = self.chain.chain_id

        last_error: str | None = None
        for _ in range(self.max_retries):
            try:
                response = self.session.get(
                    self.chain.base_url, params=params, timeout=self.timeout
                )
                response.raise_for_status()
                data = response.json()
            except requests.exceptions.RequestException as exc:
                raise EVMScanError(f"HTTP request failed: {exc}") from exc

            result = data.get("result")
            if data.get("status") == "0":
                # Rate-limit responses are transient; retry. Anything else is
                # a real API error.
                if result == _RATE_LIMIT_MESSAGE:
                    last_error = result
                    time.sleep(self.retry_delay)
                    continue
                raise EVMScanError(
                    f"API error: {data.get('message', 'unknown error')} ({result})"
                )
            return result

        raise EVMScanError(
            f"Max retries reached: {last_error or 'rate limit exceeded'}"
        )

    def get_native_balance(self, address: str, decimals: int = 18) -> TokenBalance:
        """Balance of the chain's native coin (ETH/BNB/...)."""
        raw = self._request(
            {
                "module": "account",
                "action": "balance",
                "address": address,
                "tag": "latest",
            }
        )
        return TokenBalance(
            network=self.chain.network,
            address=address,
            raw_balance=int(raw),
            decimals=decimals,
            symbol=self.chain.native_symbol,
            token_address=None,
        )

    def get_token_balance(
        self,
        address: str,
        token_address: str,
        decimals: int,
        symbol: str | None = None,
    ) -> TokenBalance:
        """Balance of an ERC-20 token held by ``address``."""
        raw = self._request(
            {
                "module": "account",
                "action": "tokenbalance",
                "contractaddress": token_address,
                "address": address,
                "tag": "latest",
            }
        )
        return TokenBalance(
            network=self.chain.network,
            address=address,
            raw_balance=int(raw),
            decimals=decimals,
            symbol=symbol,
            token_address=token_address,
        )

    def get_balance(self, account: str, asset: AssetRef) -> TokenBalance:
        """BalanceProvider port. Etherscan returns raw integers, so a non-native
        ``asset`` must carry ``decimals``."""
        if asset.native:
            return self.get_native_balance(account, decimals=asset.decimals or 18)
        if asset.identifier is None:
            raise EVMScanError("AssetRef.identifier is required for token balances")
        if asset.decimals is None:
            raise EVMScanError("AssetRef.decimals is required for EVM token balances")
        return self.get_token_balance(
            address=account,
            token_address=asset.identifier,
            decimals=asset.decimals,
            symbol=asset.symbol,
        )


_API_KEY_BY_CHAIN = {
    EVMChain.ethereum: "etherscan_api_key",
    EVMChain.bsc: "bscscan_api_key",
    EVMChain.arbitrum: "arbiscan_api_key",
    EVMChain.optimism: "optimism_api_key",
}


def build_evm_client(chain: EVMChain) -> EVMScanClient:
    """Build a client for ``chain`` with its API key pulled from settings."""
    api_key = getattr(settings, _API_KEY_BY_CHAIN[chain])
    return EVMScanClient(chain=chain, api_key=api_key)
