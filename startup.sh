#!/bin/bash

export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}$(cd "$(dirname "$0")" && pwd)"

get_cron_script() {
  case "$1" in
    otc-liquidity-ingest)  echo "src/service/run_all_ingest.py" ;;
    *) return 1 ;;
  esac
}

if [[ "$1" =~ ^--cron=(.+)$ ]]; then
  cron_name="${BASH_REMATCH[1]}"
  script_path=$(get_cron_script "$cron_name")
  if [[ -n "$script_path" ]]; then
    uv run "$script_path"
    exit 0
  else
    echo "Error: Unknown cron job '$cron_name'"
    exit 1
  fi
else
  uv run main.py
fi
