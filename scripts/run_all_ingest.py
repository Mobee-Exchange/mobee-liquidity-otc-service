#!/usr/bin/env python3
import argparse
import logging
import sys
from typing import Any

from src.client.clickhouse import SessionLocal
from src.client.spreadsheet import SpreadsheetClient
from src.repository.balance_ingest import BalanceIngestRepository
from src.service.balance_ingest import SpreadsheetBalanceIngestService
from src.service.cw_balance import CWBalanceIngestService
from src.service.cw_evm_balance import build_cw_evm_ingest_service
from src.service.fireblocks import build_fireblocks_ingest_service
from src.service.tronscan import build_tron_liquidity_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# --- Composition root ---
_session = SessionLocal()
repo = BalanceIngestRepository(_session)
fireblocks_service = build_fireblocks_ingest_service(repo)
cw_tron_service = CWBalanceIngestService(build_tron_liquidity_service(), repo)
cw_evm_service = build_cw_evm_ingest_service(repo)
spreadsheet_service = SpreadsheetBalanceIngestService(SpreadsheetClient(), repo)


def _total_rows(result: Any) -> int:
    if isinstance(result, dict):
        return sum(result.values())
    return int(result)


def run_service(name: str, service: Any) -> int | Exception:
    log.info("=" * 50)
    log.info("Running: %s", name)
    try:
        return service.run()
    except Exception as exc:
        log.error("%s failed: %s", name, exc)
        return exc


def print_summary(results: dict[str, Any]) -> bool:
    log.info("=" * 50)
    log.info("SUMMARY")
    any_failure = False
    for name, result in results.items():
        if isinstance(result, Exception):
            log.error("  %-20s ERROR: %s", name, result)
            any_failure = True
        else:
            rows = _total_rows(result)
            status = "OK" if rows > 0 else "WARN (0 rows)"
            log.info("  %-20s %s — %d rows", name, status, rows)
            if rows == 0:
                any_failure = True
    return any_failure


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run all platform ingest services")
    parser.add_argument("--full", action="store_true", help="Truncate balance_ingest before running")
    args = parser.parse_args()

    repo.ensure_table()
    if args.full:
        log.info("--full: truncating balance_ingest")
        repo.truncate()

    results = {
        "fireblocks":  run_service("Fireblocks",           fireblocks_service),
        "cw_tron":     run_service("CW wallets (Tron)",    cw_tron_service),
        "cw_evm":      run_service("CW wallets (EVM)",     cw_evm_service),
        "spreadsheet": run_service("Spreadsheet",          spreadsheet_service),
    }

    if print_summary(results):
        sys.exit(1)
