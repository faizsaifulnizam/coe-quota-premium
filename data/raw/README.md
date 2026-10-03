# data/raw — raw files are never edited or committed

**Source:** COE Bidding Results / Prices — Land Transport Authority, via data.gov.sg
**Dataset:** [`d_69b3380ad7e51aff3a7dcc84eba52b8a`](https://data.gov.sg/datasets/d_69b3380ad7e51aff3a7dcc84eba52b8a/view)
**File (fetched by [`src/download.py`](../../src/download.py), which validates structure before replacing):**

| file | contents |
|------|----------|
| `coe-bidding-results.csv` | COE Bidding Results / Prices — **1,980 rows = 396 exercises × 5 categories**, 2010-01 → 2026-09; both bidding rounds in the single file (`bidding_no` 1/2) |

**Licence:** Singapore Open Data Licence (© Land Transport Authority).
**Pull:** scripted, `initiate → poll → signed URL` (data.gov.sg v1 public API); manifest (`pull_manifest.json`) carries SHA-256, row/coverage counts and the retrieval time — figures read the pull date from it.

**Last pull: 2026-10-04** (01:10 SGT) — `coe-bidding-results.csv` sha256 `361d5ae2…` (78,695 bytes, 1,980 rows, 396 exercises). The dataset's own metadata records *Data Last Updated: 23/09/2026*.
The raw file itself is gitignored (this note is the committed record). Re-pull any time with `python src/download.py --force`.
