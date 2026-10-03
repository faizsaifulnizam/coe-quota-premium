"""Smoke tests for the committed artifacts — stdlib only, no network.

Run (repo root):  python tests/smoke_test.py
In CI:            same command, on every push + PR (.github/workflows/ci.yml)

These do NOT re-run the pipeline (that needs the raw download); they check the
repo's committed outputs, figures and banners are present, parse, and keep their
expected shape. Regenerating the outputs should still keep these green:
required-column SUBSETS only, figures = existence + size floor — plus a few
deliberate historic ANCHORS (the 2024-01 Cat B jump, the Cat D post-2022 sign)
that must not drift silently; update those only with a justified data revision.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PRESSURE_CSV = ROOT / "outputs" / "coe_pressure.csv"
JUMPS_CSV = ROOT / "outputs" / "coe_jumps.csv"
ATTR_CSV = ROOT / "outputs" / "coe_attribution.csv"
SENS_CSV = ROOT / "outputs" / "sensitivity.csv"

PRESSURE_REQUIRED_COLS = {
    "month", "round", "category", "quota", "bids_received", "bids_success",
    "premium", "bids_per_quota", "success_rate", "regime",
}
JUMPS_REQUIRED_COLS = {
    "category", "rank_in_category", "month", "round", "premium_before",
    "premium_after", "d_premium", "d_quota_pct", "bpq_before", "bpq_after",
}
ATTR_REQUIRED_COLS = {"category", "regime", "n", "rho_premium_quota", "rho_premium_bpq"}
SENS_REQUIRED_COLS = {"variant", "category", "regime", "n", "rho_premium_quota", "rho_premium_bpq"}

EXPECTED_FIGURES = [
    "f1_quota_premium.png", "f1_quota_premium-dark.png",
    "f2_pressure.png", "f2_pressure-dark.png",
    "f3_scatter.png", "f3_scatter-dark.png",
]

MIN_FIGURE_BYTES = 5000


def _load_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_pressure_csv() -> None:
    rows = _load_csv(PRESSURE_CSV)
    assert rows, f"{PRESSURE_CSV.name} has no data rows"
    missing = PRESSURE_REQUIRED_COLS - set(rows[0].keys())
    assert not missing, f"{PRESSURE_CSV.name} missing columns: {sorted(missing)}"
    assert len(rows) >= 1900, f"only {len(rows)} rows — expected the full exercise × category set"
    for r in rows:
        int(r["quota"]), int(r["bids_received"]), int(r["bids_success"]), int(r["premium"])
        bpq, sr = float(r["bids_per_quota"]), float(r["success_rate"])
        assert bpq > 0 and 0 < sr <= 1, f"derived metric out of range at {r['month']} {r['category']}"
        assert r["regime"] in ("pre", "post"), f"unknown regime {r['regime']}"


def test_jumps_csv() -> None:
    rows = _load_csv(JUMPS_CSV)
    assert rows, f"{JUMPS_CSV.name} has no data rows"
    missing = JUMPS_REQUIRED_COLS - set(rows[0].keys())
    assert not missing, f"{JUMPS_CSV.name} missing columns: {sorted(missing)}"
    assert len(rows) >= 20, f"only {len(rows)} jump rows — expected top-5 per category"
    for r in rows:
        int(r["rank_in_category"]), int(r["premium_before"]), int(r["premium_after"]), int(r["d_premium"])
        float(r["d_quota_pct"]), float(r["bpq_before"]), float(r["bpq_after"])
    for r in rows:
        assert int(r["d_premium"]) > 0, "the jump set is increases-only"
    anchor = [r for r in rows if r["category"] == "Category B" and r["rank_in_category"] == "1"][0]
    assert (anchor["month"], int(anchor["d_premium"]), int(anchor["quota_before"]), int(anchor["quota_after"])) \
        == ("2024-01", 26990, 633, 657), "Cat B's anchor jump changed — update only on a data restatement"


def test_attribution_csv() -> None:
    rows = _load_csv(ATTR_CSV)
    assert rows, f"{ATTR_CSV.name} has no data rows"
    missing = ATTR_REQUIRED_COLS - set(rows[0].keys())
    assert not missing, f"{ATTR_CSV.name} missing columns: {sorted(missing)}"
    assert len(rows) >= 8, f"only {len(rows)} attribution rows"
    for r in rows:
        assert -1.0 <= float(r["rho_premium_quota"]) <= 1.0
        assert -1.0 <= float(r["rho_premium_bpq"]) <= 1.0
        assert int(r["n"]) > 0
    d_post = [r for r in rows if r["category"] == "Category D" and r["regime"] == "post"][0]
    assert float(d_post["rho_premium_bpq"]) < 0, "Cat D's post-2022 sign changed — re-check the headline's scope"


def test_sensitivity_csv() -> None:
    rows = _load_csv(SENS_CSV)
    assert rows, f"{SENS_CSV.name} has no data rows"
    missing = SENS_REQUIRED_COLS - set(rows[0].keys())
    assert not missing, f"{SENS_CSV.name} missing columns: {sorted(missing)}"
    assert len(rows) >= 12, f"only {len(rows)} sensitivity rows — expected the variant set"


def test_figures_present() -> None:
    fig_dir = ROOT / "reports" / "figures"
    missing = [n for n in EXPECTED_FIGURES if not (fig_dir / n).is_file()]
    assert not missing, f"missing figures: {missing}"
    small = [n for n in EXPECTED_FIGURES if (fig_dir / n).stat().st_size < MIN_FIGURE_BYTES]
    assert not small, f"suspiciously small figures: {small}"


def test_banner_assets_present() -> None:
    for name in ("banner.svg", "banner-dark.svg"):
        p = ROOT / "assets" / name
        assert p.is_file(), f"missing asset: {name}"
        assert p.stat().st_size > 500, f"{name} suspiciously small"


def test_figures_synced_to_docs() -> None:
    fig_dir = ROOT / "reports" / "figures"
    img_dir = ROOT / "docs" / "img"
    for n in EXPECTED_FIGURES:
        b = img_dir / n
        assert b.is_file(), f"missing site copy: docs/img/{n}"
        assert (fig_dir / n).read_bytes() == b.read_bytes(), f"docs/img/{n} is stale — re-run src/figures.py"


def main() -> int:
    checks = [test_pressure_csv, test_jumps_csv, test_attribution_csv, test_sensitivity_csv,
              test_figures_present, test_banner_assets_present, test_figures_synced_to_docs]
    failed = 0
    for fn in checks:
        try:
            fn()
            print(f"PASS  {fn.__name__}")
        except Exception as exc:  # noqa: BLE001 — report, don't crash the runner
            failed += 1
            print(f"FAIL  {fn.__name__}: {exc}")
    print(f"{len(checks) - failed}/{len(checks)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
