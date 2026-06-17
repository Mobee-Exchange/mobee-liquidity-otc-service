from decimal import Decimal
from unittest.mock import Mock, patch

import pytest

from src.client.fireblocks import FireblocksClient, FireblocksError

VAULT_PAYLOAD = {
    "id": "7",
    "name": "OTC Hot Wallet",
    "assets": [
        {"id": "USDT_ERC20", "total": "1000.5", "available": "900.5", "pending": "100"},
        {"id": "ETH", "total": "2.25", "available": "2.25"},
    ],
}


def make_client(sdk_mock):
    with patch("src.client.fireblocks.FireblocksSDK", return_value=sdk_mock):
        return FireblocksClient(api_key="k", secret_key="raw-secret")


def test_get_vault_balances_maps_domain_model():
    sdk = Mock()
    sdk.get_vault_account_by_id.return_value = VAULT_PAYLOAD
    client = make_client(sdk)

    balances = client.get_vault_balances("7")

    assert len(balances) == 2
    usdt = balances[0]
    assert usdt.vault_id == "7"
    assert usdt.vault_name == "OTC Hot Wallet"
    assert usdt.asset_id == "USDT_ERC20"
    assert usdt.total == Decimal("1000.5")
    assert usdt.available == Decimal("900.5")
    assert usdt.pending == Decimal("100")
    # missing fields default to zero
    assert balances[1].frozen == Decimal("0")


def test_get_asset_balance_found_and_missing():
    sdk = Mock()
    sdk.get_vault_account_by_id.return_value = VAULT_PAYLOAD
    client = make_client(sdk)

    assert client.get_asset_balance("7", "ETH").total == Decimal("2.25")
    assert client.get_asset_balance("7", "NOPE") is None


def test_list_vaults_follows_pagination():
    sdk = Mock()
    sdk.get_vault_accounts_with_page_info.side_effect = [
        {"accounts": [{"id": "1", "name": "A"}], "paging": {"after": "cursor"}},
        {"accounts": [{"id": "2", "name": "B"}], "paging": {}},
    ]
    client = make_client(sdk)

    vaults = client.list_vaults()
    assert [v.vault_id for v in vaults] == ["1", "2"]
    assert sdk.get_vault_accounts_with_page_info.call_count == 2


def test_sdk_failure_wrapped():
    sdk = Mock()
    sdk.get_vault_account_by_id.side_effect = Exception("boom")
    client = make_client(sdk)
    with pytest.raises(FireblocksError, match="Failed to fetch vault"):
        client.get_vault_balances("7")
