# External-review disposition — Grok review (2026-10-04)

**Baseline:** `main` @ `aa57835`. Review supplied 2026-10-04 (17 numbered points). Method: every checkable claim was reproduced locally against the committed outputs + raw before disposition — a review's assertion is not itself a reproduced test result. **All 17 points reproduced; all are fixed in this pass.** One further error the review did not flag was found during verification and fixed (below). Everything here is working-tree + local verification; remote publication is a separate, gated step.

## Verification notes (review accuracy)

- Reproduced exactly, from the committed files: the global top-25 rerank (all-in: 10 / 13 / 2; after dropping the two special rows: 11 / 12 / 2, median 0.0%, bids-per-quota up 19, mix B 13 / E 9 / A 3); Cat C +8,010 = rank 44 among all increases; 586 increases above +1,255 of which 562 are absent from the jump file; the C/D post-2022 correlations (−0.162/+0.040; −0.282/−0.062); the like-for-like 2024-to-2026 Cat A numbers (962 → 1,252, +30%; 88,078 → 119,812); the Cat B −40,000 drop context (quota 472 → 636; Δbpq −0.015); the fill counts (384 exact; 1,595 short; median 0.992); the sensitivity pre rows (e.g. Cat A pre Pearson quota −0.168 vs base −0.033).
- One figure did not reproduce to the stated precision: Pearson(success rate, 1/bids-per-quota) recomputes to **0.98** (median |gap| 0.004) on the committed data, not 0.97 — the figure receipt prints ours; the README caption quotes 0.98.
- **Found additionally (not in the review):** "the two biggest jumps of the series, both in 2024-01 R2" is false on every basis — Cat B's +25,335 (2023-11 R2) outranks Cat A's +16,579 by S$ (and Cat D's % rows outrank both by %). Rewritten to the verifiable claim: *the largest single increase of the whole series (Cat B +26,990) and Cat A's largest (+16,579), both 2024-01 R2*.

## Dispositions, 1–17

| # | Point | Reproduced | Disposition |
|---|---|---|---|
| 1 | "came with flat quotas" (jumps: 633→657 **+3.8%**; 924→923 −0.1%) | Yes | Fixed: the memo's wording now used in README (answer + association), memo, site lead, card |
| 2 | "the 25 largest" = top-5 per category | Yes | Fixed: kept the stratified set (preserves all five categories and the Cat C case), relabelled everywhere; stats recomputed for the shipped file: **down 13 / up 11 / flat 1** (median −0.1%), bids-per-quota up **17 of 25**, median +0.25; smallest Cat D +1,050. The global-rerank alternative (11/12/2) was evaluated and not taken |
| 3 | Lede overclaims for C/D | Yes | Fixed: answer leads with the Cat A/B scope and quotes the C/D rows (all surfaces) |
| 4 | Mislabelled "moves"; the top S$ move is an invisible drop | Yes | Fixed: "increases only" stated; the Cat B −40,000 drop line added; the jump query now excludes `gap_spanning` + the Cat D 2010-01 anomaly (both kept in `coe_pressure.csv`, stated in README + code) |
| 5 | "% changes" basis wrong for `d_bpq`; robustness gap | Yes | Fixed: basis wording everywhere; new variant **bids % (not bids-per-quota)** in the CSV (A post +0.34 / B post +0.504) and table; rank-residual partial printed + documented (**−0.20 / −0.22** post-2022) |
| 6 | F2 axis floors clipped the 2013 spike / 2020 troughs; reciprocal panel unlabelled | Yes (bpq data 0.8059–3.5119; sr 0.2788–0.9232) | Fixed: ylims computed from data with 10% padding (pixel-verified headroom ≈36 px); caption rewritten with the receipt (corr 0.98; median gap 0.004) |
| 7 | Records conflated (Cat B is 135,001 on quota 934; record 150,001 in 2023) | Yes | Fixed: bullet rewritten; F3 caption fixed |
| 8 | "+28% vs 2024" vs 549→1,252 = +128%; partial year unlabelled | Yes | Fixed: README labels both (+28% = 2024→2026; +128% = 2022→2026) + Jan–Sep like-for-like; memo re-phrased |
| 9 | Audit "quota is fully taken" contradicts its own count | Yes | Fixed: `docs/data_audit.md` + `src/audit.py` receipts (exact fill 384; median fill 99.2%; 1,595 short) |
| 10 | Sensitivity "pre rows mirror base" false | Yes | Fixed: sentence replaced with the correct statement + example |
| 11 | CRLF vs LF regeneration; UTC-vs-SGT pull date | Yes | Fixed: `write_csv` LF + atomic replace; `.gitattributes` pins CSV worktree to LF; figures format the pull date in Asia/Singapore (stdlib, no tzdata) |
| 12 | CI cannot fail on headline errors | Yes | Fixed: smoke anchors the Cat B jump (2024-01: 26,990; 633→657), the Cat D post sign, increases-only, and docs/img byte-equality |
| 13 | A–E never defined | Yes | Fixed: one line in "The data" (from the dataset's description) |
| 14 | "the one clear quota-cut jump" | Yes (Cat D 2017-09 −10.25%; Cat B 2013-03 −5.83%) | Fixed: "the only large cut" + smaller cuts named |
| 15 | `docs/img` copies can go stale | Yes (no copy step existed) | Fixed: `figures.py` mirrors the six PNGs in-run; smoke hash-checks |
| 16 | `download.py` swallows the first-poll exception | Yes | Fixed: logged |
| 17 | `write_csv` non-atomic | Yes | Fixed: temp + `os.replace` |

## What was deliberately not changed

The review's own "don't break these" list stands: the question, the counted sample discipline (1,968 reconciled), F1 (honest chart), the download validation chain, the raw sha256 (`361d5ae2…`), dark-theme figures, F1 twin axes. The review's global-rerank option for the jump file was not taken (see #2) — Cat C's quota-cut case and per-category visibility are the reason; the relabel removes the false promise instead.

## Verification after the fixes

- `src/analysis.py`: **ALL CHECKS PASS** — exclusions reconciled (1,968), hand-checks exact, jump rows 25, sensitivity rows 20, partials printed (−0.197 / −0.220).
- `src/figures.py`: full QA suite passes both palettes (widths, clearances, in-bounds, overlaps); re-rendered twice → all 12 figure files byte-identical; new ylims printed as receipts.
- `tests/smoke_test.py`: **7/7**.
- Fresh-clone rerun: local clone of the branch → the README's commands end-to-end (fresh download, sha `361d5ae2…`; build 10/10; analysis ALL CHECKS PASS; figures QA + docs/img sync) → `git diff --quiet` clean; after the `.gitattributes` follow-up commit, `git status` is **empty** too — on Windows with `autocrlf=true`.
- No new dependencies; no changes to shared/sibling repos. Remote (PR / Pages / release) and the social-preview upload await the publish go.

### Files touched

`README.md` · `docs/index.html` · `docs/decision_memo.md` · `docs/sensitivity.md` · `docs/data_audit.md` · `src/analysis.py` · `src/figures.py` · `src/audit.py` · `src/download.py` · `tests/smoke_test.py` · `outputs/coe_jumps.csv` · `outputs/sensitivity.csv` (`coe_pressure.csv` / `coe_attribution.csv` content unchanged — LF refresh only) · `docs/img/` (f2 pair + re-rendered social card) · `reports/figures/` (f2 pair) · `.gitattributes` (new) · this file. Card source: `publish/coe-quota-premium-social-card.html` (+PNG).
