from decimal import Decimal
from unittest.mock import Mock, patch

from src.client.evmscan import EVMScanClient
from src.client.fireblocks import FireblocksClient
from src.client.tronscan import TronscanClient
from src.domain.entity.balance import TokenBalance
from src.domain.entity.evmscan import EVMChain
from src.domain.entity.fireblocks import FireblocksAssetBalance
from src.domain.interface.balance import AssetHolding, AssetRef, BalanceProvider
from tests.conftest import FakeResponse


def test_token_balance_satisfies_asset_holding():
    bal = TokenBalance(
        network="ethereum",
        address="0xabc",
        raw_balance=1_500_000,
        decimals=6,
        symbol="USDT",
        token_address="0xdac17f958d2ee523a2206206994597c13d831ec7",
    )
    assert isinstance(bal, AssetHolding)
    assert bal.account == "0xabc"
    assert bal.asset == "0xdac17f958d2ee523a2206206994597c13d831ec7"
    assert bal.amount == Decimal("1.5")


def test_fireblocks_balance_satisfies_asset_holding():
    bal = FireblocksAssetBalance(
        vault_id="7",
        vault_name="OTC",
        asset_id="USDT_ERC20",
        total=Decimal("1000.5"),
        available=Decimal("900"),
    )
    assert isinstance(bal, AssetHolding)
    assert bal.network == "fireblocks"
    assert bal.account == "7"
    assert bal.asset == "USDT_ERC20"
    assert bal.amount == Decimal("1000.5")


def test_all_clients_are_balance_providers():
    evm = EVMScanClient(EVMChain.ethereum, api_key="k")
    tron = TronscanClient(api_key="k")
    with patch("src.client.fireblocks.FireblocksSDK", return_value=Mock()):
        fb = FireblocksClient(api_key="k", secret_key="raw")

    for provider in (evm, tron, fb):
        assert isinstance(provider, BalanceProvider)

    assert evm.network == "ethereum"
    assert tron.network == "tron"
    assert fb.network == "fireblocks"


def test_evm_get_balance_via_port_requires_decimals_for_token():
    evm = EVMScanClient(EVMChain.ethereum, api_key="k")
    evm.session = Mock()
    evm.session.get = Mock(return_value=FakeResponse({"status": "1", "result": "2500000"}))

    holding = evm.get_balance(
        "0xabc", AssetRef(identifier="0xToken", decimals=6, symbol="USDC")
    )
    assert holding.amount == Decimal("2.5")
    assert holding.asset == "0xToken"


def test_fireblocks_get_balance_via_port():
    sdk = Mock()
    sdk.get_vault_account_by_id.return_value = {
        "id": "7",
        "name": "OTC",
        "assets": [{"id": "ETH", "total": "3.0", "available": "3.0"}],
    }
    with patch("src.client.fireblocks.FireblocksSDK", return_value=sdk):
        fb = FireblocksClient(api_key="k", secret_key="raw")

    holding = fb.get_balance("7", AssetRef(identifier="ETH"))
    assert holding.amount == Decimal("3.0")
    assert holding.account == "7"


def test_aggregation_loop_over_providers():
    """A liquidity aggregator can treat heterogeneous clients uniformly."""
    sdk = Mock()
    sdk.get_vault_account_by_id.return_value = {
        "id": "1",
        "name": "V",
        "assets": [{"id": "USDT", "total": "10", "available": "10"}],
    }
    evm = EVMScanClient(EVMChain.ethereum, api_key="k")
    evm.session = Mock()
    evm.session.get = Mock(return_value=FakeResponse({"status": "1", "result": "5000000"}))
    with patch("src.client.fireblocks.FireblocksSDK", return_value=sdk):
        fb = FireblocksClient(api_key="k", secret_key="raw")

    providers: list[BalanceProvider] = [evm, fb]
    refs = {
        "ethereum": AssetRef(identifier="0xUSDT", decimals=6),
        "fireblocks": AssetRef(identifier="USDT"),
    }
    total = sum(
        (p.get_balance("acct", refs[p.network]).amount for p in providers),
        Decimal("0"),
    )
    assert total == Decimal("15")
