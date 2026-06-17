from enum import Enum


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
