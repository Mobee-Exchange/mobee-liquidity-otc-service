-- Unified balance ingest table.
-- All balance sources (client balances, IDR bank, Fireblocks, on-chain, etc.)
-- land here so freshness and totals can be queried in one place.
--
-- platform    : e.g. 'client_balance', 'BCA', 'fireblocks', 'evm', 'tron',
--               or the bank name for IDR sources
-- source_name : client name, bank account number, vault name, wallet name, etc.
-- currency    : asset ticker (IDR, USDT, BTC, ...)
-- network     : chain / network identifier; empty for fiat sources
-- amount      : raw balance amount (Decimal to avoid float precision loss)

CREATE TABLE IF NOT EXISTS mobee_liquidity_otc.balance_ingest
(
    timestamp   DateTime64(3, 'Asia/Jakarta'),
    platform    LowCardinality(String),
    source_name LowCardinality(String),
    currency    LowCardinality(String),
    network     LowCardinality(String),
    amount      Decimal(38, 18)
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (timestamp, platform, source_name, currency);


-- Freshness view — query this to detect stale cron runs.
-- Alert if hours_since_last exceeds your expected run interval.
CREATE VIEW IF NOT EXISTS mobee_liquidity_otc.ingest_freshness AS
SELECT
    platform,
    max(timestamp)                           AS last_ingest,
    dateDiff('hour', max(timestamp), now())  AS hours_since_last
FROM mobee_liquidity_otc.balance_ingest
GROUP BY platform;
