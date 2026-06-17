from decimal import Decimal

from src.domain.entity.balance import TokenBalance


def test_amount_applies_decimals():
    bal = TokenBalance(
        network="ethereum",
        address="0xabc",
        raw_balance=1_500_000,
        decimals=6,
        symbol="USDT",
        token_address="0xdac17f958d2ee523a2206206994597c13d831ec7",
    )
    assert bal.amount == Decimal("1.5")
    assert bal.is_native is False


def test_native_when_no_token_address():
    bal = TokenBalance(
        network="ethereum",
        address="0xabc",
        raw_balance=2 * 10**18,
        decimals=18,
        symbol="ETH",
    )
    assert bal.amount == Decimal("2")
    assert bal.is_native is True


def test_amount_is_serialized():
    bal = TokenBalance(network="tron", address="T1", raw_balance=100, decimals=2)
    assert bal.model_dump()["amount"] == Decimal("1")
