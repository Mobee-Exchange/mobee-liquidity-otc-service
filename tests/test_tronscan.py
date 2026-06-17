from decimal import Decimal
from unittest.mock import Mock

from src.client.tronscan import TronscanClient
from tests.conftest import FakeResponse

TOKENS_PAYLOAD = {
    "data": [
        {
            "tokenId": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
            "tokenAbbr": "USDT",
            "balance": "2500000",
            "tokenDecimal": 6,
        },
        {
            "tokenId": "_",
            "tokenAbbr": "trx",
            "balance": "5000000",
            "tokenDecimal": 6,
        },
    ]
}


def make_client(payload):
    client = TronscanClient(api_key="key")
    client.session = Mock()
    client.session.get = Mock(return_value=FakeResponse(payload))
    return client


def test_get_token_balance_found():
    client = make_client(TOKENS_PAYLOAD)
    bal = client.get_token_balance("Taddr", "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t")
    assert bal.network == "tron"
    assert bal.symbol == "USDT"
    assert bal.amount == Decimal("2.5")
    assert bal.is_native is False


def test_get_token_balance_missing_returns_zero():
    client = make_client(TOKENS_PAYLOAD)
    bal = client.get_token_balance("Taddr", "TdoesNotExist")
    assert bal.raw_balance == 0
    assert bal.amount == Decimal("0")
    assert bal.token_address == "TdoesNotExist"


def test_native_trx_detected():
    client = make_client(TOKENS_PAYLOAD)
    balances = client.get_all_balances("Taddr")
    trx = next(b for b in balances if b.symbol == "trx")
    assert trx.is_native is True
    assert trx.amount == Decimal("5")


def test_get_all_balances_count():
    client = make_client(TOKENS_PAYLOAD)
    assert len(client.get_all_balances("Taddr")) == 2
