# Sensitivity — the association across variants

Headline association: premium moves vs **quota** moves and vs **bids-per-quota** moves, exercise over exercise — Spearman rank correlation with premium and quota as **% changes** and bids-per-quota as its **level change** (`d_bpq`, not a percent; a bids-%-change variant is in the table). Categories A & B, regimes split at the May-2022 redefinition. Machine-readable: [`outputs/sensitivity.csv`](../outputs/sensitivity.csv) · regenerate with `python src/analysis.py`.

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
| bids % (not bids-per-quota) | A | post | 105 | −0.139 | +0.340 |
| bids % (not bids-per-quota) | B | post | 105 | −0.094 | +0.504 |

(Notes: the 2020-resume variant changes only pre rows — the pause is pre-2022 — so its post rows match base and are omitted; the absolute-S$, Pearson and bids-% pre rows do not all match base and live in the CSV — e.g. Cat A pre Pearson quota ρ **−0.168** vs base **−0.033**.)

## How to read it

- **Direction is stable; the ordering is stable.** In every variant the premium↔bids-per-quota association is positive and larger than the premium↔quota association — which stays negative and weak (|ρ| ≤ 0.28 even under Pearson). Cat B's post-2022 count-pressure link (+0.50…+0.56) is the strongest relationship in the table.
- **The quota link, net of bid growth.** Bids-per-quota has quota in its denominator, so the raw negative quota correlation could be an artifact. Holding bids % fixed (rank-residual partial Spearman, printed by [`src/analysis.py`](../src/analysis.py)), post-2022 ρ(premium %, quota %) is **−0.20 (A) / −0.22 (B)** — still far weaker than the bids links above.
- **The basis barely moves the rank correlations** (Spearman on % changes vs on S$ changes agree within ±0.03) — so the finding is not an artifact of percentage scaling. Pearson amplifies the (still weak) negative quota association; it is shown rather than hidden.
- **The 2020 resume delta is a single observation** (the Jul-2020 exercise, first after the Apr–Jun pause): including it moves ρ by ≤0.011. Excluding it from the base sample is a discipline choice, not a data massage.
- **What ρ is and is not.** It measures co-movement of *exercise-to-exercise changes* — quotas move in smooth, administratively-set steps (median jump-event change: −0.1%), while premiums and bid counts move jumpily. A weak Δ-Δ correlation does not say supply never matters; it says single-exercise premium jumps are not quota events. The level story is separate and shown in the memo (2022–23 quota squeeze vs 2024–26 recovery).
- **Not a forecast.** Variants re-describe the same history; none projects. A re-pull can restate the newest exercise.
