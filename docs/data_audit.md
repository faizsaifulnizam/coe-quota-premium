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
- **Units:** `quota` = certificates available in that exercise; `bids_received` = bids submitted; `bids_success` = bids allocated a certificate; `premium` = the **final quota premium in S$, paid by all successful bidders in that category — the auction clearing price, not the lowest winning reserve price or the PQP** (prevailing quota premium, the price existing owners pay to renew; not in this file).
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
- **Two source conflicts:** 2010-02 R1 Category B quota is **1,154 in this CSV vs 693 in LTA’s historical table**; bids received/successful are 930/690 in both. 2010-01 R2 Category D premium is **S$20,090 in this CSV vs S$852 in the table**. Source values remain unchanged. The apparent undersubscription is **not** treated as established auction behaviour. [LTA table, 2010–2014](https://www.lta.gov.sg/content/dam/ltagov/who_we_are/statistics_and_publications/statistics/pdf/COE_Result_2010_2014.pdf).
- **Exact fill** (`bids_success == quota`) is **384 / 1,980**. Median fill is **99.2%**; **1,595** of the 1,979 rows with bids received ≥ CSV quota fall short (usually by little — the shortfall is not explained here). Success rate is therefore close to, but not exactly, `1 / bids-per-quota`.

## Category-definition changes (A/B)

LTA’s historical tables show that taxis left Cat A in **August 2012** and the **97 kW power criterion began in February 2014**. The earlier A/B attribution sample is therefore **February 2014 R2–April 2022**, not the whole pre-May-2022 history. Pre-February-2014 observations remain historical context in levels and plots.

### May 2022

Category A/B vehicle definitions changed from the **May 2022 1st exercise** (electric cars up to 110 kW moved into Cat A; power limits restated — dataset description). Observed at the boundary:

| | last old-definition exercise (2022-04 R2) | first new-definition (2022-05 R1) |
|---|---|---|
| Cat A | quota 532 · premium 68,699 | quota **612** · premium 70,901 |
| Cat B | quota 560 · premium 90,002 | quota **527** · premium 92,090 |

Cat A's quota jumps ~15% at the boundary while Cat B's falls — the series is **not one unbroken definition**, and A/B association estimates use definition-consistent periods. The C/D/E split at May 2022 is only a period comparison, not a claim that their auction rules never changed.

## Rules chosen, before analysis (from the profile above)

1. **Exercise = month + round**; ordered `(month, round)`. Deltas are exercise-over-exercise within a category, never across categories.
2. **Pressure metrics:** `bids_per_quota = bids_received ÷ quota`; `success_rate = bids_success ÷ bids_received`. Counts only — the file has no bid values.
3. **Regimes:** `pre` = exercises before 2022-05 R1; `post` = from 2022-05 R1. For A/B estimates, both endpoints must be at/after February 2014 and within the same May-2022 regime. Counts: 1,975 deltas − 5 pause − 2 May-boundary − 196 earlier-definition A/B = **1,772** base observations (see `src/analysis.py`).
4. **Gap discipline:** the single delta that spans the Apr–Jun 2020 pause is excluded from attribution statistics (counted + reconciled); a sensitivity variant re-includes it.
5. **Preserve source values, flag conflicts.** Official data can contain errors. A separate sensitivity excludes changes touching either disputed cell and the next change. B’s pair is already outside A/B scope; D’s pair removes 2 additional observations (1,770 sensitivity observations, D pre n=286 vs 288 in base). D pre quota ρ changes **−0.123 → −0.134**, bids-per-quota **+0.069 → +0.062**; post-2022 is unchanged.
6. **Descriptive only** — "associated with", never "caused"; no forecast. The final premium is a common clearing price. Bid reserve values are not in the file. Bid counts are not unique participants; quotas are announced before bidding ([LTA rules and worked example](https://onemotoring.lta.gov.sg/content/onemotoring/home/buying/upfront-vehicle-costs/certificate-of-entitlement--coe-.html)). Structural checks cannot resolve publisher disagreements.
