# data/raw — immutable licensed replay snapshot

**Source:** COE Bidding Results / Prices — Land Transport Authority, via data.gov.sg
**Dataset:** [`d_69b3380ad7e51aff3a7dcc84eba52b8a`](https://data.gov.sg/datasets/d_69b3380ad7e51aff3a7dcc84eba52b8a/view)
**File (fetched by [`src/download.py`](../../src/download.py), which validates structure before replacing):**

| file | contents |
|------|----------|
| `coe-bidding-results.csv` | COE Bidding Results / Prices — **1,980 rows = 396 exercises × 5 categories**, 2010-01 → 2026-09; both bidding rounds in the single file (`bidding_no` 1/2) |

**Licence:** Singapore Open Data Licence (© Land Transport Authority).
**Pull:** scripted, `initiate → poll → signed URL` (data.gov.sg v1 public API); manifest (`pull_manifest.json`) carries SHA-256, row/coverage counts and the retrieval time — figures read the pull date from it.

**Last pull: 2026-10-04** (01:10 SGT) — `coe-bidding-results.csv` sha256 `361d5ae2…` (78,695 bytes, 1,980 rows, 396 exercises). The dataset's own metadata records *Data Last Updated: 23/09/2026*.
The 78,695-byte CSV and its original 777-byte manifest are committed unchanged under the Singapore Open Data Licence for offline replay, with Git text normalization disabled. Exact CSV SHA-256: `361d5ae2ba641be1e834ca822e4cb66a91f42b6f7663847f42fcc4a4062b4bac`; manifest SHA-256: `389de31b701d6c9318b84695367a225c5aee2ac51e06e51020f91da89e364039`. These are the recovered original local bytes, not a reconstructed manifest; recorded acquisition time is not independently authenticated. Other raw files remain ignored. `python src/download.py` validates this cache offline. `--force` intentionally refreshes from the publisher; rerun all stages and review changed claims before adopting a new vintage. Restore both tracked files from the reviewed commit to replay this snapshot again.
