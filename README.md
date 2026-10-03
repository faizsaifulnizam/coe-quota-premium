<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/banner-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/banner.svg">
  <img src="assets/banner.svg" width="100%" alt="coe-quota-premium — a six-repo series on Singapore's public data">
</picture>

# coe-quota-premium

[![CI](https://github.com/faizsaifulnizam/coe-quota-premium/actions/workflows/ci.yml/badge.svg)](https://github.com/faizsaifulnizam/coe-quota-premium/actions/workflows/ci.yml) [![license: MIT](https://img.shields.io/badge/license-MIT-2E7D6B.svg)](LICENSE) ![Python 3.12](https://img.shields.io/badge/Python-3.12-C0552B.svg) ![DuckDB](https://img.shields.io/badge/analytics-DuckDB-22607B.svg) [![data: data.gov.sg](https://img.shields.io/badge/data-data.gov.sg-14293D.svg)](https://data.gov.sg/datasets/d_69b3380ad7e51aff3a7dcc84eba52b8a/view) ![COE auctions](https://img.shields.io/badge/COE%20auctions-396%20since%202010-8A6EAF.svg)

> **Answer:** For cars (Cat A/B) — not for goods vehicles (C) or motorcycles (D) — premium moves line up with **bids-per-quota** (Spearman ρ **+0.37** Cat A / **+0.56** Cat B since May 2022) more than with **quota** (ρ **−0.14 / −0.09**). Cat C and D do not: post-2022, quota is their larger correlate (ρ **−0.16 / −0.28** vs bids-per-quota **+0.04 / −0.06**; [`outputs/coe_attribution.csv`](outputs/coe_attribution.csv)). At the top-5 increases in each category (25 jumps — not the series' 25 largest), quota moved 13 down / 11 up / 1 flat (median **−0.1%**) while bids-per-quota rose in **17 of 25**; the largest single increase of the whole series — and Cat A's largest — both landed in **2024-01 R2**, with bid surges and no quota cut worth the name (Cat B **+26,990**, quota 633 → 657, +3.8%, bids per quota 1.34 → 1.99; Cat A **+16,579**, quota 924 → 923, −0.1%, 1.28 → 2.04). The only large quota cut in the set: Cat C **+8,010** after **−43.6%**. But the recent high (Cat A's record **133,009**, Sep 2026) rose on a *recovering* quota — counts alone don't explain it; premiums follow the marginal bid value, which this file doesn't contain. Descriptive; May-2022 A/B redefinition handled.

**Status:** built 2026-10-04; external-review remediation 2026-10-04 ([dispositions](docs/review-remediation.md)). Part of a six-repo series on Singapore's public data.

## Key numbers (all reproducible)

- **Association:** for Cat A/B (both regimes) premium moves vs quota ρ **−0.03…−0.14**, vs bids-per-quota ρ **+0.37…+0.56** (Spearman: premium % / quota % vs the level change in bids-per-quota). Cat C/D do not follow the split — quota is their larger (negative) correlate ([`outputs/coe_attribution.csv`](outputs/coe_attribution.csv)).
- **Jump events — the top 5 S$ increases per category** (so not the series' 25 largest; smallest here: Cat D **+1,050**): quota down 13 / up 11 / flat 1 (median **−0.1%**), bids-per-quota up in **17 of 25**, median +0.25 ([`outputs/coe_jumps.csv`](outputs/coe_jumps.csv)). Increases only — the largest single S$ move in the series is a drop: Cat B 2023-10 R2 → 2023-11 R1, **−40,000**, quota **+34.7%** (472 → 636), bids-per-quota −0.015.
- **Records on a recovering quota:** Cat A's record **133,009** (2026-09 R1, quota **1,195**); latest R2 **131,890** (quota 1,193) — Cat A's 2022 average quota was **549**. Cat B in Sep 2026: **135,001 / 133,000** on quotas **934 / 927** — below its record **150,001** (2023-10 R2, quota 472). **2024 → 2026** (full 2024 vs Jan–Sep): Cat A average quota **980 → 1,252 (+28%)**, average premium 90,495 → 119,812; like-for-like Jan–Sep: quota **962 → 1,252 (+30%)**, premium 88,078 → 119,812.
- **Data quality:** 1,980/1,980 rows retained, **0 exclusions**, **10/10 checks**; 3 dated cells + 1 delta recomputed from the raw file in plain Python (stdlib) — exact ([`docs/data_audit.md`](docs/data_audit.md)).

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="reports/figures/f1_quota_premium-dark.png">
  <source media="(prefers-color-scheme: light)" srcset="reports/figures/f1_quota_premium.png">
  <img src="reports/figures/f1_quota_premium.png" width="100%" alt="Quota premium and quota per exercise, Category A and B, 2010–2026, with the May 2022 redefinition marked">
</picture>

*Quota premium (left) vs quota (right), Category A and B — the quota cycles; Cat A's premium climbs to a record, Cat B stays below its 2023 peak. Dotted line: the May-2022 A/B redefinition. No exercises Apr–Jun 2020 (bidding pause).*

### More views

| | |
|---|---|
| <a href="reports/figures/f2_pressure.png"><picture><source media="(prefers-color-scheme: dark)" srcset="reports/figures/f2_pressure-dark.png"><source media="(prefers-color-scheme: light)" srcset="reports/figures/f2_pressure.png"><img src="reports/figures/f2_pressure.png" alt="Bids per quota and success rate over time, Category A and B"></picture></a> | <a href="reports/figures/f3_scatter.png"><picture><source media="(prefers-color-scheme: dark)" srcset="reports/figures/f3_scatter-dark.png"><source media="(prefers-color-scheme: light)" srcset="reports/figures/f3_scatter.png"><img src="reports/figures/f3_scatter.png" alt="Quota vs premium scatter, pre and post May 2022 coloured, Category A and B"></picture></a> |
| *Count pressure: bids per quota and the success rate. The lower panel is almost the reciprocal of the upper one (corr **0.98** vs 1/bids-per-quota — the quota is nearly filled; median gap 0.004), so it is not a second measure. The spikes are exercises where bid counts surged relative to quota.* | *Same quota, higher price: one dot per exercise; post-2022 exercises sit at higher premiums across the quota range — the 2026 points are Cat A's record; Cat B's record is the high dot at quota ≈470 (2023-10).* |

*All figures are code-generated, light + dark ([`src/figures.py`](src/figures.py)); full size in [`reports/figures/`](reports/figures/) · half-page write-up in [`docs/decision_memo.md`](docs/decision_memo.md).*

## The question

COE prices come out of an auction: a fixed quota of certificates meets however many bids show up. When premiums jump, two very different things could be happening — the quota got tighter (supply), or more bids chased the same quota (demand pressure). The two look identical in a price chart. This repo separates them auction by auction since 2010, category by category, and carries the one break that makes the series not-one-series: the May-2022 Category A/B redefinition.

## The data

- **COE Bidding Results / Prices** — LTA via [data.gov.sg](https://data.gov.sg/datasets/d_69b3380ad7e51aff3a7dcc84eba52b8a/view): **1,980 rows = 396 exercises × 5 categories, 2010-01 → 2026-09**; two bidding rounds per month live in the same file; no category is ever missing; the only interruption is the COVID pause (no exercises Apr–Jun 2020).
- **Fields:** month · round (1/2) · category (A–E) · quota (certificates offered) · bids received · successful bids · **premium = the quota premium, S$ — the lowest successful bid price for the exercise; not the PQP** (the renewal price for existing vehicles, which is not in this file).
- **Categories:** A — cars ≤1,600cc and ≤97kW (from May 2022, also electric cars ≤110kW); B — cars above those limits; C — goods vehicles and buses; D — motorcycles; E — open (all except motorcycles).
- Licence: Singapore Open Data Licence (© Land Transport Authority). A [script](src/download.py) pulls the file into `data/raw/` (gitignored, SHA-256 manifest, structure-validated before replacing); the raw file is never edited.

## Method

DuckDB throughout; one row per exercise × category after staging. The pipeline, end to end:

1. **Pull** — scripted from data.gov.sg, structure-validated before replacing, SHA-256 + coverage in a manifest: [`src/download.py`](src/download.py)
2. **Audit** — profile and the `[VERIFY]`s resolved from the live file (round structure, category completeness, the pause, dirty cells) *before* analysis: [`docs/data_audit.md`](docs/data_audit.md)
3. **Stage** — comma-formatted thousands (`"1,438"`) parsed with a counted rule set; month + round → an ordered exercise; regime flag: [`sql/01_staging.sql`](sql/01_staging.sql)
4. **Check** — 10 assertions (five categories per exercise, contiguity with the documented pause, success ≤ quota, ranges), run *before* the parquet is written; failures leave existing files untouched: [`sql/05_checks.sql`](sql/05_checks.sql) — 10/10 pass, 1,980/1,980 rows
5. **Measure** — exercise-over-exercise deltas per category, with the definition-break and pause flags defined once: [`sql/02_metrics.sql`](sql/02_metrics.sql)
6. **Jump events** — the top 5 S$ increases per category (increases only; the 2020-resume delta and the known Cat D source anomaly are excluded from the ranking and stay in the pressure file) with quota/bids context: [`outputs/coe_jumps.csv`](outputs/coe_jumps.csv)
7. **Attribute (descriptively)** — premium moves vs quota moves vs bid-pressure moves; 5 variants + a rank-residual partial: [`src/analysis.py`](src/analysis.py) → [`outputs/coe_attribution.csv`](outputs/coe_attribution.csv) · [`docs/sensitivity.md`](docs/sensitivity.md)
8. **Draw · write** — figures are code, light + dark ([`src/figures.py`](src/figures.py)); the memo ([`docs/decision_memo.md`](docs/decision_memo.md))

### The comparison, made computable

The unit is the **auction exercise** (month + round) — the decision point where a quota meets bids. Two candidate movers are read from the same rows:

```text
bids per quota = bids received ÷ quota           count pressure — bids per certificate
quota change   = quota vs the previous exercise  supply — certificates offered
```

Both are compared with the premium move using **Spearman rank correlation** — premium and quota enter as % changes; bids-per-quota as its **level change** (`d_bpq`, not a percent — a bids-% variant ships in the sensitivity). Rank correlation because a handful of extreme swings (the 2020 recovery, the 2022–23 squeeze) would otherwise dominate a linear fit; % changes so the early low-base categories (Cat D premiums ~S$1k) don't masquerade as large dollar moves.

### The association (the core, in words)

For cars (Cat A/B), premium moves track **bids-per-quota** (ρ **+0.37** / **+0.56** since May 2022) far more than **quota** (ρ **−0.14 / −0.09**) — Cat C/D are the exception, with quota their larger correlate. The event end tells the same story: at the top-5 increases per category, quota moved down 13 / up 11 / flat 1 (median **−0.1%**) while bids-per-quota rose in **17 of 25**. The series' largest single increase (Cat B **+26,990**) and Cat A's largest (**+16,579**) are both **2024-01 R2** — no quota cut worth the name, bid surges both. The only large quota cut in the set is Cat C **2023-02 (+8,010)** after **−43.6%**.

**Why counts are only a proxy.** Bids-per-quota counts participants; the premium is set by the marginal successful **bid value**. A flood of low bids moves the count without moving the price; one determined bidder moves the price without moving the count. This file sees counts and the resulting price — never the values in between. That gap is why the 2024–26 highs can sit at the top of the chart while quotas recover and count pressure eases: whatever lifted the winning bids is not visible here. The level history is two-phased — **2022–23: the squeeze** (Cat B average quota 483 in 2023 vs 820 in 2021; premium doubled) vs **2024–26: recovery** (Cat A average quota **+28%**, 2024 → 2026; premiums kept climbing).

### Rules chosen, and why

| Rule | Choice | Why |
|------|--------|-----|
| Unit | one auction exercise (month + round) | the auction is the decision point; both rounds live in one file |
| Pressure metric | bids per quota · success rate (counts) | the file has no bid values; counts are the observable proxy — stated as such everywhere |
| Jump basis | **S$ increases**, ranked per category | COE is quoted in S$; % moves on early low-base values are small-denominator noise. Increases only — the two special deltas (2020-resume, Cat D source anomaly) are excluded from the ranking, kept in the pressure file |
| Regime split | at the May-2022 1st exercise (A/B redefined) | never average across a definition break; the line sits on every timeline |
| Boundary delta | excluded from statistics, counted | that one delta mixes the redefinition with auction dynamics (A/B; C/D/E were not redefined) |
| 2020 pause | the resume delta excluded, counted; re-included in sensitivity | a 4-month break is not an exercise-over-exercise change |
| Outliers | none trimmed | an official series has nothing to trim; the largest moves are findings, not errors |

### Validation — receipts, not claims

- **10/10 checks** pass on the staged table; **1,980/1,980 rows** retained, **0 exclusions** — reconciliation printed by [`src/build_dataset.py`](src/build_dataset.py).
- **Independent recompute:** 3 dated cells + 1 delta recomputed from the *raw CSV* in plain Python stdlib — exact match (2013-01 R1 Cat A premium 92,100; 2022-05 R2 Cat B 95,889; 2026-09 R2 Cat E 137,000; the 2026-09 R2 Cat A move −1,119).
- **Statistics exclusions, counted:** 1,975 deltas − (5 pause-spanning + 2 boundary-crossing) = **1,968** in the base sample.
- **Sensitivity:** 5 variants (base · including the 2020 resume · absolute-S$ basis · Pearson · bids-% instead of bids-per-quota) plus a rank-residual partial — direction and ordering stable; the Spearman bases agree within ±0.03; net of bid-count growth, post-2022 ρ(premium %, quota %) is **−0.20 / −0.22** — still far weaker than the bids links. Pearson amplifies the (still weak, ≤0.28) negative quota link ([`docs/sensitivity.md`](docs/sensitivity.md)).
- **Determinism:** figures re-render byte-identical; the CSVs regenerate identical (`git diff --quiet`).
- **Stranger-rerun:** fresh clone → the commands below → same outputs for the 2026-10-04 pull (a later re-pull can move the newest exercise).
- **Rounding:** correlations are display-rounded to 3 dp, deltas in the CSVs to 2–4 dp; sums of rounded columns may differ from full precision in the last digit.

### Limits

**Not a forecast; not causal; not bid values.** The file counts bids and shows the price that cleared — it cannot say *why* bidders show up, who they are, or what they bid, and it cannot time the market. The association table is descriptive co-movement of changes, not a mechanism; the level story is separate. Full list under **Caveats** below.

### Principles this repo follows

1. **One question per repo** — the method serves the question, not the reverse.
2. **Define before use** — quota premium vs PQP, the regime boundary, the pressure metric — all defined before any chart uses them.
3. **SQL first** — the numbers live in `sql/`; Python glues, correlates and draws.
4. **Nothing hand-edited** — raw data immutable; every number regenerates from code.
5. **Limits are part of the deliverable.**

## Reproduce

```bash
git clone https://github.com/faizsaifulnizam/coe-quota-premium && cd coe-quota-premium
uv venv .venv --python 3.12          # or: python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
uv pip install -r requirements.txt   # or: pip install -r requirements.txt

python src/download.py       # raw CSV → data/raw/ (gitignored; add --force to re-pull)
python src/build_dataset.py  # staging + 10 checks → data/processed/coe_exercises.parquet
python src/analysis.py       # pressure table + jumps + attribution + sensitivity → outputs/
python src/figures.py        # re-renders reports/figures/ (light + dark)
```

Then check `outputs/coe_pressure.csv`: the **2026-09 R1 Category A** row reads premium **133,009** with quota 1,195 and bids per quota 1.43; **R2** reads **131,890**. And the first Category B row of `outputs/coe_jumps.csv` reads **+26,990** (2024-01 R2; bids per quota 1.34 → 1.99). Data as of the 2026-10-04 pull — a later re-pull can move the newest exercise.

## Caveats

- **The series is not one definition.** Category A/B rules changed at the May 2022 1st exercise (observable: Cat A quota +15.0% at the boundary). Regimes are never averaged together; the boundary delta is excluded from statistics (counted). Categories C/D/E were not redefined — their same-date split is a period comparison only.
- **Counts, not values.** Bids-per-quota and success rate are participation measures; the premium is set by the marginal bid value, which the file does not contain.
- **The 2020 pause.** No exercises Apr–Jun 2020; the resume delta is excluded from statistics (counted) and re-included in sensitivity (moves ρ by ≤0.011).
- **One source anomaly, left visible.** Cat D, 2010-01 R2: premium 20,090 after 889, reverting to 852 the next exercise. Not trimmed — it stays in the data (`coe_pressure.csv`), is excluded from the jump-events ranking, and is noted here.
- The newest exercise can be restated by the publisher.
- Descriptive only — no forecast, no causal claim.

## Out of scope

Premium forecasts or early-warning models; causal attribution of bidder behaviour; dealer-level analysis; bid-value modelling; the PQP (renewal price) series; cross-country comparisons.

## Licence

Code: MIT. Data: Singapore Open Data Licence — © Land Transport Authority, via data.gov.sg. This is an independent, unofficial analysis.

---

*Part of a six-repo series on Singapore's public data — the other five repos go live as they're built:* **[hdb-resale-mart](https://github.com/faizsaifulnizam/hdb-resale-mart)** · **[card-book-quality](https://github.com/faizsaifulnizam/card-book-quality)** · **[retail-sales-split](https://github.com/faizsaifulnizam/retail-sales-split)** · **coe-category-break · hdb-lease-slope**

*If you found this useful, a star helps others find it.*
