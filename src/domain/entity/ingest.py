from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class LiquidityBalanceRawData(BaseModel):
    """One row in the shared balance_ingest table.

    Every platform service (Fireblocks, CW wallets, EVM chains, spreadsheet)
    builds this model and hands it to BalanceIngestRepository.insert_total_balance().
    """

    timestamp: datetime
    platform: str
    source_name: str
    currency: str
    # An actual blockchain network (ETHEREUM, TRON, ...) for on-chain sources;
    # "Any" for off-chain sources (Fireblocks, Binance, bank/client balances).
    network: str = "Any"
    amount: Decimal
