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
    network: str
    amount: Decimal
