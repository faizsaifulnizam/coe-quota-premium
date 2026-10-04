# Sensitivity — changes, definitions and source conflicts

These are descriptive associations, not causal estimates. Premium and quota use **% changes**, bids-per-quota its **level change**, except where labelled. Spearman uses **average ranks for ties**. CSVs retain full precision; this table rounds directly to three decimals.

A/B earlier changes are **February 2014 R2–April 2022**; later changes start **May 2022 R2**. Both endpoints must share the category definition. Earlier observations stay visible as context in the pressure file and plots.

Machine-readable: [sensitivity.csv](../outputs/sensitivity.csv) · [all-category base](../outputs/coe_attribution.csv). Regenerate with `python src/analysis.py`; this write-up describes the 2026-10-04 snapshot.

| Variant | Cat | Period | n | ρ premium~quota | ρ premium~pressure |
|---|---|---|---:|---:|---:|
| Base Spearman | A | post | 105 | -0.138 | +0.372 |
| Base Spearman | A | pre | 190 | -0.049 | +0.552 |
| Base Spearman | B | post | 105 | -0.094 | +0.555 |
| Base Spearman | B | pre | 190 | -0.078 | +0.483 |
| Include 2020 resume | A | post | 105 | -0.138 | +0.372 |
| Include 2020 resume | A | pre | 191 | -0.037 | +0.558 |
| Include 2020 resume | B | post | 105 | -0.094 | +0.555 |
| Include 2020 resume | B | pre | 191 | -0.062 | +0.491 |
| Absolute-change Spearman | A | post | 105 | -0.114 | +0.386 |
| Absolute-change Spearman | A | pre | 190 | -0.038 | +0.524 |
| Absolute-change Spearman | B | post | 105 | -0.078 | +0.545 |
| Absolute-change Spearman | B | pre | 190 | -0.076 | +0.482 |
| Pearson on % changes | A | post | 105 | -0.220 | +0.446 |
| Pearson on % changes | A | pre | 190 | -0.186 | +0.600 |
| Pearson on % changes | B | post | 105 | -0.270 | +0.540 |
| Pearson on % changes | B | pre | 190 | -0.156 | +0.500 |
| Bid-count % growth | A | post | 105 | -0.138 | +0.341 |
| Bid-count % growth | A | pre | 190 | -0.049 | +0.496 |
| Bid-count % growth | B | post | 105 | -0.094 | +0.504 |
| Bid-count % growth | B | pre | 190 | -0.078 | +0.419 |

The last variant’s pressure column is **bid-count % growth**, not bids-per-quota. Absolute-change basis means premium in S$ and quota in certificates, with bids-per-quota still a level change.

## Source-conflict sensitivity (all categories)

The source CSV is preserved. Against [LTA’s historical table](https://www.lta.gov.sg/content/dam/ltagov/who_we_are/statistics_and_publications/statistics/pdf/COE_Result_2010_2014.pdf), two cells disagree:

- 2010-02 R1 B quota: CSV **1,154**, table **693**.
- 2010-01 R2 D premium: CSV **S$20,090**, table **S$852**.

Exclusions cover **each disputed observation’s change and the following change**: B 2010-02 R1/R2; D 2010-01 R2/2010-02 R1. B’s pair is already outside the A/B scope. D loses two additional pre observations:

| D pre sample | n | ρ premium~quota | ρ premium~bids-per-quota |
|---|---:|---:|---:|
| Base | 288 | -0.123 | +0.069 |
| Exclude disputed-cell deltas | 286 | -0.134 | +0.062 |

Every other category/period is unchanged under this sensitivity, including the post-2022 headline. Base total: **1,772**; source-conflict sensitivity: **1,770**. This checks those two conflicts only, not every historical source cell.

## How to read it

- **A/B signs and ordering survive these variants.** Their count-pressure association is positive and larger in absolute magnitude than the negative quota association. A/B Pearson quota magnitude is below 0.28. This does not establish demand or supply causes.
- **Scaling check:** absolute-change vs percentage Spearman values differ by less than 0.03. Switching to bid-count % growth changes the metric itself and can differ by more; it is not merely a scaling check.
- **Resume check:** including the July 2020 change moves A/B correlations by less than **0.017**. It remains a four-month-span change, unlike ordinary adjacent exercises.
- **Partial correlation:** conditioning on bid-count growth, post-2022 rank-residual ρ(premium %, quota % | bids %) is **−0.20 (A) / −0.22 (B)**. Bids-per-quota has quota in its denominator. The partial is descriptive and does not identify a causal supply effect.
- **C/D are not the A/B result:** under base Spearman, their post quota associations have the larger absolute magnitude. The A/B variants above are not evidence that this ordering holds under every C/D specification or that their auction rules never changed.
- **Selection is different from all-exercise association:** the top 5 positive S$ jumps per category are not a random sample or the overall 25 largest. Two selected events coincide with quota cuts above 40%; neither is a causal supply estimate.
- **No forecast:** this re-describes history. Source restatements and new releases can change associations and event rankings.
