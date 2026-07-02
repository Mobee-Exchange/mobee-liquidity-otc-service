from decimal import Decimal
from unittest.mock import Mock

from src.client.tronscan import TronscanClient
from src.domain.entity.tronscan import Tron
from src.service.platform.tronscan import TronLiquidityService
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


def make_service(payload):
    client = TronscanClient(api_key="key")
    client.session = Mock()
    client.session.get = Mock(return_value=FakeResponse(payload))
    return TronLiquidityService(client)


# --- enum ---


def test_enum_exposes_token_and_asset_ref():
    assert Tron.USDT.value.contract == "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
    assert Tron.USDT.to_asset_ref().identifier == "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
    assert Tron.TRX.to_asset_ref().native is True


def test_resolve_by_symbol_case_insensitive():
    assert Tron.resolve("usdt") is Tron.USDT


def test_resolve_by_contract():
    assert Tron.resolve("TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t") is Tron.USDT


def test_resolve_unknown_returns_none():
    assert Tron.resolve("TunknownContract") is None


# --- service ---


def test_get_balance_by_enum():
    service = make_service(TOKENS_PAYLOAD)
    bal = service.get_balance("Taddr", Tron.USDT)
    assert bal.amount == Decimal("2.5")
    assert bal.symbol == "USDT"


def test_get_balance_by_symbol_string():
    service = make_service(TOKENS_PAYLOAD)
    assert service.get_balance("Taddr", "USDT").amount == Decimal("2.5")


def test_get_balance_native_trx():
    service = make_service(TOKENS_PAYLOAD)
    bal = service.get_balance("Taddr", Tron.TRX)
    assert bal.is_native is True
    assert bal.amount == Decimal("5")


def test_get_balance_unknown_contract_returns_zero():
    service = make_service(TOKENS_PAYLOAD)
    bal = service.get_balance("Taddr", "TnotHeldContract")
    assert bal.raw_balance == 0
    assert bal.token_address == "TnotHeldContract"


def test_get_balances_defaults_to_all_members():
    service = make_service(TOKENS_PAYLOAD)
    balances = service.get_balances("Taddr")
    assert len(balances) == len(list(Tron))
    by_symbol = {b.symbol: b for b in balances}
    assert by_symbol["USDT"].amount == Decimal("2.5")


def test_get_balances_explicit_tokens_mixed():
    service = make_service(TOKENS_PAYLOAD)
    balances = service.get_balances("Taddr", [Tron.USDT, "TRX"])
    assert len(balances) == 2


def test_get_all_balances_delegates_to_client():
    service = make_service(TOKENS_PAYLOAD)
    assert len(service.get_all_balances("Taddr")) == 2
