from typing import Final

# Tron has a single mainnet explorer, so the network label is a constant rather
# than an enum like the EVM family.
TRON_NETWORK: Final[str] = "tron"
TRON_NATIVE_SYMBOL: Final[str] = "TRX"
TRONSCAN_BASE_URL: Final[str] = "https://apilist.tronscan.org/api"
