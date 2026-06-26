#!/usr/bin/env python3
import argparse
import logging
import sys
from typing import Any

from src.client.spreadsheet import SpreadsheetClient
from src.repository.balance_ingest import BalanceIngestRepository
from src.service.platform.spreadsheet import SpreadsheetIngestService
from src.service.platform.binance import build_binance_ingest_service
from src.service.platform.cold_wallet_balance import build_cold_wallet_ingest_service
from src.service.platform.fireblocks import build_fireblocks_ingest_service
from src.service.platform.gate import build_gate_ingest_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# --- Composition root ---
repo = BalanceIngestRepository()
fireblocks_service = build_fireblocks_ingest_service(repo)
cold_wallet_service = build_cold_wallet_ingest_service(repo)
binance_main_service = build_binance_ingest_service(repo, account="main")
binance_sub_service = build_binance_ingest_service(repo, account="sub")
gate_main_service = build_gate_ingest_service(repo, account="main")
gate_sub_service = build_gate_ingest_service(repo, account="sub")
spreadsheet_service = SpreadsheetIngestService(SpreadsheetClient(), repo)


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
    repo.ensure_table()


    results = {
        "fireblocks":   run_service("Fireblocks",            fireblocks_service),
        "cold_wallets": run_service("Cold wallets",          cold_wallet_service),
        "binance_main": run_service("Binance Main (DCI)",   binance_main_service),
        "binance_sub":  run_service("Binance Sub (DCI)",    binance_sub_service),
        "gate_main":    run_service("Gate Main (DCI)",       gate_main_service),
        "gate_sub":     run_service("Gate Sub (DCI)",        gate_sub_service),
        "spreadsheet":  run_service("Spreadsheet",           spreadsheet_service),
    }

    if print_summary(results):
        sys.exit(1)
