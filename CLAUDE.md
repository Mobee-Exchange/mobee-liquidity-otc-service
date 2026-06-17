# mobee-liquidity-otc-service

Service for reading on-chain and custody balances to track OTC liquidity across
EVM chains, Tron, and Fireblocks.

## Architecture

Layered (ports & adapters):

```
src/
├── core/            # cross-cutting concerns
│   └── config.py    # pydantic-settings (secrets from .env, never hardcoded)
├── client/          # adapters: one client per external source
│   ├── evmscan.py   # Etherscan-family explorers (EVMScanClient)
│   ├── tronscan.py  # Tronscan API (TronscanClient)
│   └── fireblocks.py# Fireblocks SDK (FireblocksClient)
└── domain/
    ├── entity/      # pydantic value objects (TokenBalance, Fireblocks*, EVMChain)
    └── interface/   # ports/protocols (BalanceProvider, AssetHolding, AssetRef)
```

- **Every client implements the `BalanceProvider` port** (`network` + `get_balance(account, asset)`), so callers can aggregate balances across heterogeneous sources uniformly.
- Balance value objects satisfy the `AssetHolding` protocol structurally — no inheritance.
- We use `Protocol` (structural typing), not `ABC`, so implementers don't depend on the port. Switch to `ABC` only if shared implementation or construction-time enforcement is needed.

## Conventions

- **Synchronous by design.** Do NOT introduce async/asyncio/concurrency. Stay sync (session reuse, batching, caching) for any perf work.
- **Secrets via settings only.** Add new keys to `src/core/config.py` and `.env.example`; never hardcode.
- Use `pydantic` models (not `dataclasses`) for domain types.
- Money/amounts use `Decimal`, never `float`.

## Commands

```bash
uv sync                 # install deps
uv run pytest -q        # run tests (all mocked, no live API calls)
```

## TODO / Roadmap

Ordered roughly by priority. Owner does these incrementally.

- [ ] **Service layer** — a use-case (e.g. `LiquidityService`) that consumes `BalanceProvider` to aggregate liquidity across providers. The port currently has no production consumer.
- [ ] **Logging** — structured logging across clients (requests, retries, errors, balances fetched). None exists yet.
- [ ] **Retry/backoff for Tronscan & Fireblocks** — only `EVMScanClient` handles rate-limit/transient errors today.
- [ ] **DB / persistence layer** — wire up the unused deps (clickhouse, sqlalchemy, redis, psycopg2, pygsheets) for storing/caching balances.
- [ ] **Token decimals resolution for EVM** — `AssetRef.decimals` is manual today; risk of silently wrong amounts. Add a token registry or on-chain `decimals()` lookup.
- [ ] **Rotate the old API keys** — the 4 Etherscan-family keys that were previously hardcoded in `evmscan.py` were never committed (initial commit had no `src/`), but they were exposed in plaintext, so regenerate them as a precaution and put the new values in `.env`.
- [ ] **Verify Tron native marker** — `_TRX_TOKEN_ID = "_"` in `tronscan.py` is an assumption; confirm against the live API.
- [ ] **Tooling** — add ruff + mypy config and CI; type checker enforces the Protocol contracts.
- [ ] **Tests for factories** — `build_evm_client` / `build_tronscan_client` / `build_fireblocks_client` are untested.
