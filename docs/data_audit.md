# Data audit — LTA COE bidding results (repo 03)

**File:** `data/raw/coe-bidding-results.csv` — pulled scripted from data.gov.sg on **2026-10-04** (01:10 SGT; `pull_manifest.json` has SHA-256 + coverage).
The dataset's own metadata records *Data Last Updated: 23/09/2026* (update frequency: twice monthly, after each exercise).
Produced by `src/audit.py` (stdlib only — independent of the DuckDB pipeline by design).

## Shape & units (the `[VERIFY]`s, resolved from the live file)

- **Coverage:** **1,980 rows = 396 exercises × 5 categories, 2010-01 → 2026-09, no category gaps.** 198 months, exactly 2 exercises per month.
- **Round structure `[VERIFY]`:** both rounds live in the **single CSV** — `bidding_no` ∈ {1, 2}, 990 rows each. There is no separate round-1/round-2 file.
- **Category completeness `[VERIFY]`:** **every one of the 396 exercises carries all 5 categories** (A–E) — the "missing category rows in some rounds" concern does **not** reproduce in this file. No exclusions needed on that basis.
- **The only interruption:** no exercises in **Apr–Jun 2020** (COVID-19 bidding pause; 2020-03 → 2020-07 is the one month gap). The file does not explain it; it is documented, not filled.
- **Fields:** month (YYYY-MM) · bidding_no (1/2) · vehicle_class (Category A–E) · quota · bids_received · bids_success · premium.
- **Units:** `quota` = certificates available in that exercise; `bids_received` = bids submitted; `bids_success` = bids allocated a certificate; `premium` = the **quota premium in S$ — the lowest successful bid price for that exercise, not the PQP** (prevailing quota premium, the price existing owners pay to renew; not in this file).
- **Dirty cells:** `bids_received` carries **109** comma-formatted cells and `bids_success` **41** (e.g. `"1,438"`, quoted, from 2023 onward). `quota` and `premium` are clean integers. The parse rule is `strip "," → integer`; everything is countable, nothing dropped.

| Category | quota range | premium range (S$) |
|---|---|---|
| A | 333 – 2,272 | 18,502 – **133,009** |
| B | 302 – 1,537 | 19,190 – **150,001** |
| C | 43 – 1,091 | 19,001 – 95,000 |
| D | 285 – 1,121 | 852 – 20,090 |
| E | 124 – 750 | 19,889 – **158,004** |

## Integrity

- 0 duplicate (month, round, category) keys · 0 rows with `bids_success > bids_received` · 0 with `bids_success > quota` · 0 non-positive premiums.
- **1 undersubscribed exercise** in 16 years: 2010-02 R1 Category B — 930 bids for 1,154 certificates, 690 successful (bids below the reserve price still fail). Every other exercise received at least as many bids as certificates.
- When bids exceed quota the quota is fully taken: 384 of 1,980 rows have `bids_success == quota` exactly.

## The May-2022 definition break (A/B)

Category A/B vehicle definitions changed from the **May 2022 1st exercise** (electric cars up to 110 kW moved into Cat A; power limits restated — dataset description). Observed at the boundary:

| | last old-definition exercise (2022-04 R2) | first new-definition (2022-05 R1) |
|---|---|---|
| Cat A | quota 532 · premium 68,699 | quota **612** · premium 70,901 |
| Cat B | quota 560 · premium 90,002 | quota **527** · premium 92,090 |

Cat A's quota jumps ~15% at the boundary while Cat B's falls — the series is **not one unbroken definition**, and the analysis treats it as two regimes (categories C/D/E were not redefined; their split by the same date is a period comparison only).

## Rules chosen, before analysis (from the profile above)

1. **Exercise = month + round**; ordered `(month, round)`. Deltas are exercise-over-exercise within a category, never across categories.
2. **Pressure metrics:** `bids_per_quota = bids_received ÷ quota`; `success_rate = bids_success ÷ bids_received`. Counts only — the file has no bid values.
3. **Regimes:** `pre` = exercises before 2022-05 R1; `post` = from 2022-05 R1. No statistic is ever averaged across the boundary; the one delta that crosses it (A/B) is excluded from statistics and counted (see reconciliation in `src/analysis.py`).
4. **Gap discipline:** the single delta that spans the Apr–Jun 2020 pause is excluded from attribution statistics (counted + reconciled); a sensitivity variant re-includes it.
5. **No outlier rule.** An official auction series has no micro-outliers to trim; the largest moves are findings, not errors to remove.
6. **Descriptive only** — "associated with", never "caused"; no forecast. Premiums are set by the marginal successful bid value, which this file does not contain (it has counts and the resulting price).
