from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment / .env file.

    Secrets must never be hardcoded in source. Populate them through a local
    ``.env`` file (see ``.env.example``) or real environment variables.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # EVM block explorers (Etherscan-family). Etherscan V2 uses a single key
    # across chains, but each explorer family keeps its own key here so the
    # service can mix V1 and V2 endpoints.
    etherscan_api_key: str = ""
    bscscan_api_key: str = ""
    arbiscan_api_key: str = ""
    optimism_api_key: str = ""

    # Tronscan
    tronscan_api_key: str = ""

    # Fireblocks. ``fireblocks_secret_key`` accepts either the raw PEM contents
    # or a path to the .pem file (resolved by the client).
    fireblocks_api_key: str = ""
    fireblocks_secret_key: str = ""
    fireblocks_base_url: str = "https://api.fireblocks.io"

    # Google Sheets. Path to the service-account credentials JSON file.
    google_sheets_credentials_file: str = "src/core/sheets.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()
