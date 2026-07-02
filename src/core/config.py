from pydantic_settings import BaseSettings
from src.utils.path import return_full_path


class Settings(BaseSettings):
    """Application settings loaded from environment / .env file.

    Secrets must never be hardcoded in source. Populate them through a local
    ``.env`` file (see ``.env.example``) or real environment variables.
    """

    # EVM block explorers (Etherscan-family). Etherscan V2 uses a single key
    # across chains, but each explorer family keeps its own key here so the
    # service can mix V1 and V2 endpoints.
    etherscan_api_key: str
    bscscan_api_key: str 
    arbiscan_api_key: str 
    optimism_api_key: str 

    # Tronscan
    tronscan_api_key: str

    # Binance — separate API keys for the main and sub accounts
    binance_main_api_key: str
    binance_main_secret: str
    binance_sub_api_key: str
    binance_sub_secret: str

    # Gate.io — separate API keys for the main and sub accounts
    gate_main_api_key: str
    gate_main_secret: str
    gate_sub_api_key: str
    gate_sub_secret: str
    # Fireblocks. ``fireblocks_secret_key`` accepts either the raw PEM contents
    # or a path to the .pem file (resolved by the client).
    fireblocks_api_key: str 
    fireblocks_secret_key: str 
    fireblocks_base_url: str 

    # Google Sheets. Path to the service-account credentials JSON file.
    google_sheets_credentials_file: str 

    # Balance ingest spreadsheet (ClientBalance + BalanceIDR + TradingBalance tabs)
    balance_ingest_spreadsheet_url: str
    balance_ingest_tab_client: str
    balance_ingest_tab_idr_bank: str
    balance_ingest_tab_trading: str
    
    # Database Connection
    clickhouse_url: str
    postgres_url: str
    
    pool_size: int = 2
    max_overflow: int = 5
    pool_timeout: int = 30
    pool_recycle: int = 900

    class Config:
        extra = "allow"
        env_file = return_full_path(".env")
        env_file_encoding = "utf-8"


settings = Settings()
