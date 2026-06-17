from decimal import Decimal
from unittest.mock import Mock

import pytest

from src.client.evmscan import EVMScanClient, EVMScanError
from src.domain.entity.evmscan import EVMChain
from tests.conftest import FakeResponse


def make_client(monkeypatch, responses):
    client = EVMScanClient(EVMChain.ethereum, api_key="key", retry_delay=0)
    client.session = Mock()
    client.session.get = Mock(side_effect=responses)
    monkeypatch.setattr("src.client.evmscan.time.sleep", lambda _: None)
    return client


def test_get_token_balance_returns_domain_model(monkeypatch):
    client = make_client(
        monkeypatch, [FakeResponse({"status": "1", "result": "1500000"})]
    )

    bal = client.get_token_balance(
        address="0xabc",
        token_address="0xdac17f958d2ee523a2206206994597c13d831ec7",
        decimals=6,
        symbol="USDT",
    )

    assert bal.network == "ethereum"
    assert bal.amount == Decimal("1.5")
    assert bal.is_native is False
    # Etherscan V2 chain must inject chainid
    _, kwargs = client.session.get.call_args
    assert kwargs["params"]["chainid"] == 1
    assert kwargs["params"]["apikey"] == "key"


def test_get_native_balance(monkeypatch):
    client = make_client(
        monkeypatch, [FakeResponse({"status": "1", "result": str(2 * 10**18)})]
    )
    bal = client.get_native_balance("0xabc")
    assert bal.symbol == "ETH"
    assert bal.is_native is True
    assert bal.amount == Decimal("2")


def test_retries_on_rate_limit_then_succeeds(monkeypatch):
    client = make_client(
        monkeypatch,
        [
            FakeResponse({"status": "0", "result": "Max rate limit reached"}),
            FakeResponse({"status": "1", "result": "100"}),
        ],
    )
    bal = client.get_native_balance("0xabc", decimals=0)
    assert bal.raw_balance == 100
    assert client.session.get.call_count == 2


def test_api_error_raises(monkeypatch):
    client = make_client(
        monkeypatch,
        [FakeResponse({"status": "0", "message": "NOTOK", "result": "bad key"})],
    )
    with pytest.raises(EVMScanError, match="NOTOK"):
        client.get_native_balance("0xabc")


def test_exhausts_retries_on_persistent_rate_limit(monkeypatch):
    client = make_client(
        monkeypatch,
        [FakeResponse({"status": "0", "result": "Max rate limit reached"})] * 3,
    )
    with pytest.raises(EVMScanError, match="Max retries"):
        client.get_native_balance("0xabc")


def test_legacy_chain_omits_chainid(monkeypatch):
    client = EVMScanClient(EVMChain.bsc, api_key="key", retry_delay=0)
    client.session = Mock()
    client.session.get = Mock(return_value=FakeResponse({"status": "1", "result": "0"}))
    client.get_native_balance("0xabc")
    _, kwargs = client.session.get.call_args
    assert "chainid" not in kwargs["params"]
