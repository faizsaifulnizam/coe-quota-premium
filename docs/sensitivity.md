# Sensitivity — the association across variants

Headline association: premium moves vs **quota** moves and vs **bids-per-quota** moves, exercise over exercise, Spearman on % changes. Categories A & B, regimes split at the May-2022 redefinition. Machine-readable: [`outputs/sensitivity.csv`](../outputs/sensitivity.csv) · regenerate with `python src/analysis.py`.

| variant | Cat | regime | n | ρ prem~quota | ρ prem~bpq |
|---|---|---|---|---|---|
| base: % changes, pause + break deltas excluded | A | post | 105 | −0.139 | +0.372 |
| base | A | pre | 288 | −0.033 | +0.366 |
| base | B | post | 105 | −0.094 | **+0.555** |
| base | B | pre | 288 | −0.081 | +0.421 |
| including the 2020 resume delta | A | pre | 289 | −0.026 | +0.371 |
| including the 2020 resume delta | B | pre | 289 | −0.070 | +0.426 |
| absolute S$ change basis | A | post | 105 | −0.113 | +0.388 |
| absolute S$ change basis | B | post | 105 | −0.080 | +0.545 |
| Pearson on % changes | A | post | 105 | −0.220 | +0.446 |
| Pearson on % changes | B | post | 105 | −0.270 | +0.540 |

(Pre-regime rows for the two added variants mirror their base rows and live in the CSV; the table shows the informative pairs.)

## How to read it

- **Direction is stable; the ordering is stable.** In every variant the premium↔bids-per-quota association is positive and larger than the premium↔quota association — which stays negative and weak (|ρ| ≤ 0.28 even under Pearson). Cat B's post-2022 count-pressure link (+0.54…+0.56) is the strongest relationship in the table.
- **The basis barely moves the rank correlations** (Spearman on % changes vs on S$ changes agree within ±0.03) — so the finding is not an artifact of percentage scaling. Pearson amplifies the (still weak) negative quota association; it is shown rather than hidden.
- **The 2020 resume delta is a single observation** (the Jul-2020 exercise, first after the Apr–Jun pause): including it moves ρ by ≤0.011. Excluding it from the base sample is a discipline choice, not a data massage.
- **What ρ is and is not.** It measures co-movement of *exercise-to-exercise changes* — quotas move in smooth, administratively-set steps (median jump-event change: 0.0%), while premiums and bid counts move jumpily. A weak Δ-Δ correlation does not say supply never matters; it says single-exercise premium jumps are not quota events. The level story is separate and shown in the memo (2022–23 quota squeeze vs 2024–26 recovery).
- **Not a forecast.** Variants re-describe the same history; none projects. A re-pull can restate the newest exercise.
