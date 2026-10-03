-- 02_metrics.sql — exercise-over-exercise deltas per category (the analysis base).
-- Reads: `exercise` (from sql/01, exposed via parquet in src/analysis.py).
-- Writes: table `deltas` — every exercise with its predecessor's values attached.
-- Ordering is (month, round) within a category — the only meaningful sequence.
-- Flags (defined here once, used by every consumer):
--   crosses_break : the delta whose NEW exercise is the first post-May-2022 one
--                   (definition break; excluded from A/B statistics, counted)
--   gap_spanning  : the delta spanning the Apr–Jun 2020 pause (excluded, counted)

CREATE OR REPLACE TABLE deltas AS
SELECT
    month, round_no, category, quota, bids_received, bids_success, premium,
    bids_per_quota, success_rate, regime,
    lag(month)          OVER w AS prev_month,
    lag(round_no)       OVER w AS prev_round,
    lag(quota)          OVER w AS prev_quota,
    lag(bids_received)  OVER w AS prev_bids_received,
    lag(premium)        OVER w AS prev_premium,
    lag(bids_per_quota) OVER w AS prev_bpq,
    lag(success_rate)   OVER w AS prev_success_rate,
    premium - lag(premium) OVER w                                            AS d_premium,
    100.0 * (premium - lag(premium) OVER w) / lag(premium) OVER w            AS d_premium_pct,
    quota - lag(quota) OVER w                                                AS d_quota,
    100.0 * (quota - lag(quota) OVER w) / lag(quota) OVER w                  AS d_quota_pct,
    bids_received - lag(bids_received) OVER w                                AS d_bids_received,
    100.0 * (bids_received - lag(bids_received) OVER w) / lag(bids_received) OVER w AS d_bids_received_pct,
    bids_per_quota - lag(bids_per_quota) OVER w                              AS d_bpq,
    success_rate - lag(success_rate) OVER w                                  AS d_success_rate,
    CASE WHEN month >= DATE '2022-05-01' AND lag(month) OVER w < DATE '2022-05-01'
         THEN TRUE ELSE FALSE END                                            AS crosses_break,
    CASE WHEN lag(month) OVER w = DATE '2020-03-01' AND month = DATE '2020-07-01'
         THEN TRUE ELSE FALSE END                                            AS gap_spanning
FROM exercise
WINDOW w AS (PARTITION BY category ORDER BY month, round_no)
ORDER BY category, month, round_no
