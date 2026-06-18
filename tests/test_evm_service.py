from decimal import Decimal
from unittest.mock import Mock

import pytest

from src.client.evmscan import EVMScanClient
from src.domain.entity.evmscan import (
    Arbitrum,
    Bsc,
    Ethereum,
    EVMChain,
    EVMTokenError,
    Optimism,
)
from src.service.evmscan import EVMLiquidityService
from tests.conftest import FakeResponse


def make_service(chain, responses):
    client = EVMScanClient(chain, api_key="key", retry_delay=0)
    client.session = Mock()
    client.session.get = Mock(side_effect=responses)
    return EVMLiquidityService(client)


# --- enums ---


def test_same_symbol_differs_per_chain():
    # USDT: 6 decimals on Ethereum, 18 on BSC, different contracts.
    assert Ethereum.USDT.value.decimals == 6
    assert Bsc.USDT.value.decimals == 18
    assert Ethereum.USDT.value.contract != Bsc.USDT.value.contract


def test_resolve_by_symbol_and_contract():
    assert Ethereum.resolve("usdt") is Ethereum.USDT
    assert (
        Ethereum.resolve("0xdac17f958d2ee523a2206206994597c13d831ec7") is Ethereum.USDT
    )


def test_resolve_unknown_returns_none():
    assert Ethereum.resolve("0xnope") is None


def test_native_members_per_chain():
    assert Bsc.BNB.value.native is True
    assert Arbitrum.ETH.value.native is True
    assert Optimism.ETH.to_asset_ref().native is True


# --- service ---


def test_get_balance_by_enum_uses_registry_decimals():
    service = make_service(
        EVMChain.ethereum, [FakeResponse({"status": "1", "result": "2500000"})]
    )
    bal = service.get_balance("0xabc", Ethereum.USDT)
    assert bal.amount == Decimal("2.5")  # 6 decimals
    _, kwargs = service.client.session.get.call_args
    assert kwargs["params"]["contractaddress"] == (
        "0xdAC17F958D2ee523a2206206994597C13D831ec7"
    )


def test_get_balance_by_symbol_string():
    service = make_service(
        EVMChain.ethereum, [FakeResponse({"status": "1", "result": "2500000"})]
    )
    assert service.get_balance("0xabc", "USDT").amount == Decimal("2.5")


def test_get_balance_bsc_uses_18_decimals():
    service = make_service(
        EVMChain.bsc, [FakeResponse({"status": "1", "result": str(3 * 10**18)})]
    )
    assert service.get_balance("0xabc", Bsc.USDT).amount == Decimal("3")


def test_get_balance_native():
    service = make_service(
        EVMChain.ethereum, [FakeResponse({"status": "1", "result": str(2 * 10**18)})]
    )
    bal = service.get_balance("0xabc", Ethereum.ETH)
    assert bal.is_native is True
    assert bal.amount == Decimal("2")


def test_get_balance_unknown_token_without_decimals_raises():
    service = make_service(EVMChain.ethereum, [])
    with pytest.raises(EVMTokenError):
        service.get_balance("0xabc", "0xunregistered")


def test_get_balance_unknown_token_with_decimals():
    service = make_service(
        EVMChain.ethereum, [FakeResponse({"status": "1", "result": "1000"})]
    )
    bal = service.get_balance("0xabc", "0xunregistered", decimals=3)
    assert bal.amount == Decimal("1")
    assert bal.token_address == "0xunregistered"


def test_get_balances_defaults_to_chain_tokens():
    chain = EVMChain.ethereum
    responses = [FakeResponse({"status": "1", "result": "1"})] * len(list(Ethereum))
    service = make_service(chain, responses)
    assert len(service.get_balances("0xabc")) == len(list(Ethereum))
