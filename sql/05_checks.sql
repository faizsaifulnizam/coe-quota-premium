-- 05_checks.sql — validation queries for the staged `exercise` table.
-- Each row: one check. src/build_dataset.py runs this and asserts all violations = 0.
-- Checks must survive regeneration: nothing pins an exact row count; floors are
-- lower bounds. The 2020 pause (Apr–Jun, no exercises) is the ONE allowed month gap.

SELECT 'all five categories per exercise' AS check_name,
       count(*) AS violations
FROM (SELECT month, round_no FROM exercise GROUP BY 1, 2 HAVING count(DISTINCT category) <> 5)
UNION ALL SELECT 'no duplicate (month, round, category)',
       count(*) FROM (SELECT month, round_no, category FROM exercise GROUP BY 1, 2, 3 HAVING count(*) > 1)
UNION ALL SELECT 'two rounds per month',
       count(*) FROM (
           SELECT month FROM exercise GROUP BY 1
           HAVING count(DISTINCT round_no) <> 2
              AND NOT (month = (SELECT max(month) FROM exercise)
                       AND count(DISTINCT round_no) = 1 AND min(round_no) = 1)
       ) -- Publisher can release latest R1 before R2; older months must be complete.
UNION ALL SELECT 'months contiguous except the 2020 pause',
       count(*) FROM (
           SELECT month, lag(month) OVER (ORDER BY month) AS prev
           FROM (SELECT DISTINCT month FROM exercise)
       ) WHERE prev IS NOT NULL
         AND month <> CAST(prev + INTERVAL 1 MONTH AS DATE)
         AND NOT (prev = DATE '2020-03-01' AND month = DATE '2020-07-01')
UNION ALL SELECT 'bids_success <= quota, quota positive',
       count(*) FROM exercise WHERE bids_success > quota OR quota <= 0
UNION ALL SELECT 'bids_success <= bids_received',
       count(*) FROM exercise WHERE bids_success > bids_received
UNION ALL SELECT 'premium positive and plausible',
       count(*) FROM exercise WHERE premium <= 0 OR premium > 300000
UNION ALL SELECT 'success_rate and bids_per_quota in range',
       count(*) FROM exercise WHERE success_rate <= 0 OR success_rate > 1 OR bids_per_quota <= 0
UNION ALL SELECT 'coverage floor (>= 1900 rows, >= 190 months)',
       CASE WHEN (SELECT count(*) FROM exercise) >= 1900
             AND (SELECT count(DISTINCT month) FROM exercise) >= 190 THEN 0 ELSE 1 END
UNION ALL SELECT 'months in range 2010-01 .. today',
       count(*) FROM exercise WHERE month < DATE '2010-01-01' OR month > CURRENT_DATE
