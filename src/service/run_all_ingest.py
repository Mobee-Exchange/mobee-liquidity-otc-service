#!/usr/bin/env python3
import argparse
import logging
import sys
from datetime import datetime
from typing import Any

from src.client.spreadsheet import SpreadsheetClient
from src.repository.balance_ingest import BalanceIngestRepository
from src.service.platform.spreadsheet import SpreadsheetIngestService
from src.service.platform.binance import build_binance_ingest_service
from src.service.platform.cold_wallet_balance import build_cold_wallet_ingest_service
from src.service.platform.fireblocks import build_fireblocks_ingest_service
from src.service.platform.gate import build_gate_ingest_service
from src.service.liquidity_snapshot import LiquiditySnapshotService
from src.service.balance_difference import BalanceDifferenceService

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
snapshot_service = LiquiditySnapshotService()
balance_difference = BalanceDifferenceService()


def _total_rows(result: Any) -> int:
    if isinstance(result, dict):
        return sum(result.values())
    return int(result)


def run_service(name: str, service: Any, **kwargs: Any) -> int | Exception:
    log.info("=" * 50)
    log.info("Running: %s", name)
    try:
        return service.run(**kwargs)
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

    # One timestamp for the whole run. Every balance_ingest row and the liquidity
    # snapshot share it, so they're joinable on the cycle:
    #   balance_ingest.timestamp == liquidity_net_position_snapshot.snapshot_ts
    # Balance diff isn't stamped here — it derives its timestamps from balance_ingest.
    snapshot_ts = datetime.now()

    results = {
        "fireblocks": run_service(
            "Fireblocks", fireblocks_service, snapshot_ts=snapshot_ts
        ),
        "cold_wallets": run_service(
            "Cold wallets", cold_wallet_service, snapshot_ts=snapshot_ts
        ),
        "binance_main": run_service(
            "Binance Main (DCI)", binance_main_service, snapshot_ts=snapshot_ts
        ),
        "binance_sub": run_service(
            "Binance Sub (DCI)", binance_sub_service, snapshot_ts=snapshot_ts
        ),
        "gate_main": run_service(
            "Gate Main (DCI)", gate_main_service, snapshot_ts=snapshot_ts
        ),
        "gate_sub": run_service(
            "Gate Sub (DCI)", gate_sub_service, snapshot_ts=snapshot_ts
        ),
        "spreadsheet": run_service(
            "Spreadsheet", spreadsheet_service, snapshot_ts=snapshot_ts
        ),
        "difference": run_service("Balance Difference", balance_difference),
        "snapshot": run_service(
            "Liquidity snapshot", snapshot_service, snapshot_ts=snapshot_ts
        ),
    }

    if print_summary(results):
        sys.exit(1)
