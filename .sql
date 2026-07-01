
-- All balance sources (client balances, IDR bank, Fireblocks, on-chain, etc.)
-- platform  : e.g. 'client_balance', 'idr_bank', 'fireblocks', 'evm', 'tron'
-- source_name  : client name, bank name, vault name, etc.
-- currency     : asset ticker (IDR, USDT, BTC, ...)
-- network      : chain / network identifier; empty for fiat sources
-- account      : wallet address, bank account number, description, etc.
-- amount       : raw balance amount (Decimal to avoid float precision loss)

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
    source_type,
    max(timestamp)                           AS last_ingest,
    dateDiff('hour', max(timestamp), now())  AS hours_since_last
FROM mobee_liquidity_otc.balance_ingest
GROUP BY source_type;

-- Latest balance view from balance_ingest
-- mobee_liquidity_otc.balance_latest source

CREATE VIEW mobee_liquidity_otc.balance_latest
(

    `platform` LowCardinality(String),

    `source_name` LowCardinality(String),

    `currency` LowCardinality(String),

    `network` LowCardinality(String),

    `amount` Decimal(38,
 18),

    `as_of` DateTime64(3,
 'Asia/Jakarta')
)
AS SELECT
    platform,

    source_name,

    currency,

    network,

    argMax(amount,
 timestamp) AS amount,

    max(timestamp) AS as_of
FROM mobee_liquidity_otc.balance_ingest
GROUP BY
    platform,

    source_name,

    currency,

    network;

-- Net liquidity per currency, in NATIVE units. Aggregates from a SUBQUERY over
-- balance_ingest (not the balance_latest view) on purpose: chaining two
-- aggregate views trips ILLEGAL_AGGREGATION under the 24.10 analyzer, which
-- flattens the two GROUP BY levels. The explicit subquery is a single
-- aggregation boundary, so it works for every consumer without any per-query
-- SETTINGS. (balance_latest stays for its own uses; this just doesn't depend on it.)
CREATE OR REPLACE VIEW mobee_liquidity_otc.liquidity_net_position AS
SELECT
    currency,
    sumIf(amount, platform NOT LIKE 'Client%') AS total_balance,
    sumIf(amount, platform LIKE 'Client%')     AS client_balance,
    sumIf(amount, platform NOT LIKE 'Client%')
        - sumIf(amount, platform LIKE 'Client%') AS liquidity_balance
FROM
(
    SELECT platform, currency, argMax(amount, timestamp) AS amount
    FROM mobee_liquidity_otc.balance_ingest
    GROUP BY platform, source_name, currency, network
)
GROUP BY currency;


-- Snapshot for liquidity_net_position at a given point in time
-- mobee_liquidity_otc.liquidity_net_position_snapshot definition

CREATE TABLE mobee_liquidity_otc.liquidity_net_position_snapshot
(

    `snapshot_ts` DateTime64(3,
 'Asia/Jakarta'),

    `currency` LowCardinality(String),

    `total_balance` Decimal(38,
 18),

    `client_balance` Decimal(38,
 18),

    `liquidity_balance` Decimal(38,
 18),

    `usd_price` Nullable(Decimal(38,
 18)),

    `liquidity_balance_usd` Nullable(Decimal(38,
 18))
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(snapshot_ts)
ORDER BY (snapshot_ts,
 currency)
SETTINGS index_granularity = 8192;

-- get balance previous and latest difference written to balance_diff
-- mobee_liquidity_otc.balance_diff definition

CREATE TABLE mobee_liquidity_otc.balance_diff
(

    `timestamp` DateTime64(3,
 'Asia/Jakarta'),

    `platform` LowCardinality(String),
    
    `source_name` LowCardinality(String),

    `network` LowCardinality(String),

    `currency` LowCardinality(String),

    `balance` Decimal(38,
 18),

    `prev_balance` Decimal(38,
 18),

    `diff` Decimal(38,
 18)
)
ENGINE = ReplacingMergeTree
PARTITION BY toYYYYMM(timestamp)
ORDER BY (timestamp,
 platform,
 network,
 source_name,
 currency)
SETTINGS index_granularity = 8192;
