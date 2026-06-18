from unittest.mock import Mock, patch

import pytest

import src.client.spreadsheet as spreadsheet
from src.client.spreadsheet import (
    SpreadsheetClient,
    SpreadsheetError,
    _extract_key,
    _get_sheets_client,
)

LINK = "https://docs.google.com/spreadsheets/d/1AbC-dEf_123/edit#gid=0"


# --- _extract_key -----------------------------------------------------------


def test_extract_key_happy_path():
    assert _extract_key(LINK) == "1AbC-dEf_123"


def test_extract_key_without_trailing_path():
    assert _extract_key("https://docs.google.com/spreadsheets/d/XyZ789") == "XyZ789"


def test_extract_key_invalid_raises():
    with pytest.raises(SpreadsheetError):
        _extract_key("https://example.com/not-a-sheet")


# --- _get_sheets_client (lazy singleton) ------------------------------------


def test_get_sheets_client_authorizes_once():
    spreadsheet._gc = None  # reset module-level cache
    fake_client = Mock()
    with patch.object(
        spreadsheet.pygsheets, "authorize", return_value=fake_client
    ) as authorize, patch.object(spreadsheet, "get_settings") as get_settings:
        get_settings.return_value.google_sheets_credentials_file = "creds.json"

        first = _get_sheets_client()
        second = _get_sheets_client()

    assert first is fake_client
    assert second is fake_client
    authorize.assert_called_once_with(service_file="creds.json")


# --- append_rows_by_link ----------------------------------------------------


def _client_with_worksheet(worksheet):
    client = SpreadsheetClient()
    client._open_gs_by_link = Mock(return_value=worksheet)
    return client


def test_append_rows_empty_returns_none_without_touching_sheet():
    client = SpreadsheetClient()
    client._open_gs_by_link = Mock()
    assert client.append_rows_by_link(LINK, "Sheet1", []) is None
    client._open_gs_by_link.assert_not_called()


def test_append_rows_appends_after_existing_anchor_values():
    worksheet = Mock()
    worksheet.get_col.return_value = ["header", "a", "b"]  # 3 filled rows
    client = _client_with_worksheet(worksheet)

    rows = [["x"], ["y"]]
    start_row = client.append_rows_by_link(LINK, "Sheet1", rows)

    assert start_row == 4  # len(anchor) + 1
    worksheet.update_values.assert_called_once_with((4, 1), rows, extend=True)


def test_append_rows_respects_start_location_floor():
    worksheet = Mock()
    worksheet.get_col.return_value = ["header"]  # only 1 filled row -> next is 2
    client = _client_with_worksheet(worksheet)

    rows = [["x"]]
    start_row = client.append_rows_by_link(
        LINK, "Sheet1", rows, start_location=(10, 3)
    )

    assert start_row == 10  # floor from start_location wins over len+1
    worksheet.update_values.assert_called_once_with((10, 3), rows, extend=True)
