from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


_DEFAULT_CONFIG_PATH = Path("etc/config.yaml")


class FireblocksVault(BaseModel):
    name: str = Field(..., alias="Name")
    id: int = Field(..., alias="id")

    model_config = {"populate_by_name": True}


class ColdWallet(BaseModel):
    name: str = Field(..., alias="Name")
    address: str = Field(..., alias="Address")
    tokens: list[str] = Field(default_factory=list, alias="Token")

    model_config = {"populate_by_name": True}


class AppConfig(BaseModel):
    """Non-secret configuration loaded from YAML (configurations/config.yaml).

    Credentials and secrets live in .env / Settings (pydantic-settings).
    This class holds only structural config: vaults, cold wallet addresses, etc.
    Keys are top-level in the YAML (no wrapper section).
    """

    fireblocks_vaults: list[FireblocksVault] = Field(default_factory=list, alias="FireblocksVaults")
    # network name (e.g. "Ethereum", "Tron") -> its cold wallets
    cold_wallets: dict[str, list[ColdWallet]] = Field(default_factory=dict, alias="ColdWallets")

    model_config = {"populate_by_name": True}

    @classmethod
    def from_yaml(cls, path: Path = _DEFAULT_CONFIG_PATH) -> "AppConfig":
        raw: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
        return cls.model_validate(raw)


@lru_cache
def get_app_config() -> AppConfig:
    return AppConfig.from_yaml()
