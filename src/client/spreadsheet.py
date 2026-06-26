import re

import pandas as pd
import pygsheets
from pygsheets import client

from src.core.config import settings

# https://docs.google.com/spreadsheets/d/<KEY>/edit#gid=0
_SHEET_KEY_RE = re.compile(r"/spreadsheets/d/([a-zA-Z0-9-_]+)")

_gc: client.Client | None = None


class SpreadsheetError(Exception):
    """Raised when a Google Sheets operation fails."""


def _get_sheets_client() -> client.Client:
    global _gc
    if _gc is None:
        _gc = pygsheets.authorize(
            service_file=settings.google_sheets_credentials_file
        )
    return _gc


def _extract_key(link: str) -> str:
    """Pull the spreadsheet key out of a full Google Sheets URL."""
    match = _SHEET_KEY_RE.search(link)
    if match is None:
        raise SpreadsheetError(f"Could not extract spreadsheet key from link: {link}")
    return match.group(1)


class SpreadsheetClient:
    """Reads from / writes to Google Sheets via a service account."""

    def _connect_sheets(self) -> client.Client:
        return _get_sheets_client()

    def _open_gs(self, sheet: str, wks: str):
        return self._connect_sheets().open(sheet).worksheet_by_title(wks)

    def _open_gs_by_link(self, link: str, wks: str):
        return (
            self._connect_sheets()
            .open_by_key(_extract_key(link))
            .worksheet_by_title(wks)
        )

    def _clear_sheet(self, sheet: str, wks: str) -> None:
        self._open_gs(sheet, wks).clear()

    def list_worksheets(self, link: str) -> list[str]:
        key = _extract_key(link)
        return [ws.title for ws in self._connect_sheets().open_by_key(key).worksheets()]

    def read_raw(self, link: str, wks: str) -> list[list[str]]:
        return self._open_gs_by_link(link, wks).get_all_values()

    def read(self, link: str, wks: str) -> pd.DataFrame:
        return self._open_gs_by_link(link, wks).get_as_df()

    def write_single_value(
        self, sheet: str, wks: str, data: str, location: tuple[int, int]
    ) -> None:
        self._open_gs(sheet, wks).update_value(location, data)

    def write_dataframe(
        self, sheet: str, wks: str, data: pd.DataFrame, location: tuple[int, int]
    ) -> None:
        self._open_gs(sheet, wks).set_dataframe(data, location)

    def append_rows_by_link(
        self,
        link: str,
        wks: str,
        rows: list[list],
        start_location: tuple[int, int] = (1, 1),
        anchor_col: int = 1,
    ) -> int | None:
        if not rows:
            return None

        worksheet = self._open_gs_by_link(link, wks)
        anchor_values = worksheet.get_col(anchor_col, include_tailing_empty=False)
        start_row = max(len(anchor_values) + 1, start_location[0])
        worksheet.update_values((start_row, start_location[1]), rows, extend=True)
        return start_row
