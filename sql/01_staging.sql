-- 01_staging.sql — raw COE CSV -> tidy `exercise` table (one row per month × round × category).
-- Reads:  data/raw/coe-bidding-results.csv (never modified)
-- Writes: table `exercise`; parquet copy handled by src/build_dataset.py.
-- The raw file quotes comma thousands (e.g. "1,438" in bids_received) — strip
-- commas, then TRY_CAST. The WHERE clause below mirrors the exclusion rules
-- counted in src/build_dataset.py (retained + excluded == raw rows).
-- Derived here, used everywhere: bids_per_quota, success_rate, regime
-- (regime split at the May-2022 1st exercise — the A/B definition break).

CREATE OR REPLACE TABLE exercise AS
WITH parsed AS (
    SELECT
        month          AS month_label,
        bidding_no     AS round_label,
        vehicle_class  AS category,
        quota          AS quota_raw,
        bids_success   AS success_raw,
        bids_received  AS received_raw,
        premium        AS premium_raw
    FROM read_csv_auto('data/raw/coe-bidding-results.csv', all_varchar = true)
), clean AS (
    SELECT
        TRY_CAST(month_label || '-01' AS DATE)                       AS month,
        TRY_CAST(round_label AS INTEGER)                             AS round_no,
        category,
        TRY_CAST(replace(quota_raw, ',', '') AS BIGINT)              AS quota,
        TRY_CAST(replace(received_raw, ',', '') AS BIGINT)           AS bids_received,
        TRY_CAST(replace(success_raw, ',', '') AS BIGINT)            AS bids_success,
        TRY_CAST(replace(premium_raw, ',', '') AS BIGINT)            AS premium
    FROM parsed
)
SELECT
    month,
    round_no,
    category,
    quota,
    bids_received,
    bids_success,
    premium,
    bids_received::DOUBLE / quota        AS bids_per_quota,
    bids_success::DOUBLE / bids_received AS success_rate,
    CASE WHEN month >= DATE '2022-05-01' THEN 'post' ELSE 'pre' END AS regime
FROM clean
WHERE month IS NOT NULL
  AND round_no IN (1, 2)
  AND category IN ('Category A', 'Category B', 'Category C', 'Category D', 'Category E')
  AND quota IS NOT NULL
  AND bids_received IS NOT NULL
  AND bids_success IS NOT NULL
  AND premium IS NOT NULL
ORDER BY month, round_no, category
