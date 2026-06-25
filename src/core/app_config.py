from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


_DEFAULT_CONFIG_PATH = Path("configurations/config.yaml")


class CWWallet(BaseModel):
    name: str = Field(..., alias="Name")
    address: str = Field(..., alias="Address")

    model_config = {"populate_by_name": True}


class ServiceConfig(BaseModel):
    fireblocks_vault_ids: list[int] = Field(default_factory=list, alias="FireblocksVaultIds")
    evm_cw_wallets: list[CWWallet] = Field(default_factory=list, alias="EVMCWWallets")
    cw_wallets: list[CWWallet] = Field(default_factory=list, alias="CWWallets")

    model_config = {"populate_by_name": True}


class AppConfig(BaseModel):
    """Non-secret configuration loaded from YAML (configurations/config.yaml).

    Credentials and secrets live in .env / Settings (pydantic-settings).
    This class holds only structural config: vault IDs, wallet addresses, etc.
    """

    service: ServiceConfig = Field(..., alias="ServiceConfig")

    model_config = {"populate_by_name": True}

    @classmethod
    def from_yaml(cls, path: Path = _DEFAULT_CONFIG_PATH) -> "AppConfig":
        raw: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
        return cls.model_validate(raw)


@lru_cache
def get_app_config() -> AppConfig:
    return AppConfig.from_yaml()
