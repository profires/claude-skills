"""
test_export.py — Tests for EdgarClient CSV export methods.

Run: python3 scripts/test_export.py
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.edgar_client import EdgarClient

client = EdgarClient("TestBot test@example.com")
TEST_TICKERS = ["VRT", "BE", "LEU"]


def test_snapshot_csv():
    print("test_snapshot_csv...", end=" ")
    df = client.export_snapshot_csv(TEST_TICKERS)

    # Shape: one row per ticker
    assert len(df) == 3, f"Expected 3 rows, got {len(df)}"

    # Required columns
    expected_cols = [
        "ticker", "latest_year", "revenue_m", "net_income_m", "ebit_m",
        "ebit_margin", "operating_cf_m", "cash_m", "long_term_debt_m",
        "net_debt_m", "rev_growth_yoy",
    ]
    for col in expected_cols:
        assert col in df.columns, f"Missing column: {col}"

    # VRT revenue should be ~$10,230M (within 5% tolerance)
    vrt = df[df["ticker"] == "VRT"].iloc[0]
    assert 9700 < vrt["revenue_m"] < 10800, f"VRT revenue unexpected: {vrt['revenue_m']}"
    assert vrt["latest_year"] == 2025, f"VRT latest year unexpected: {vrt['latest_year']}"

    # BE net income should be present for 2025 (ProfitLoss fallback)
    be = df[df["ticker"] == "BE"].iloc[0]
    assert be["latest_year"] == 2025, f"BE latest year unexpected: {be['latest_year']}"
    assert be["net_income_m"] is not None and be["net_income_m"] < 0, \
        f"BE net income should be negative, got: {be['net_income_m']}"

    # LEU should have data
    leu = df[df["ticker"] == "LEU"].iloc[0]
    assert 400 < leu["revenue_m"] < 600, f"LEU revenue unexpected: {leu['revenue_m']}"

    print("PASSED")


def test_timeseries_csv():
    print("test_timeseries_csv...", end=" ")
    df = client.export_timeseries_csv(TEST_TICKERS)

    # Required columns
    assert list(df.columns) == ["ticker", "year", "metric", "value_m"], \
        f"Unexpected columns: {list(df.columns)}"

    # Should have multiple years per ticker
    for t in TEST_TICKERS:
        t_df = df[df["ticker"] == t]
        assert len(t_df) > 5, f"{t} should have >5 rows, got {len(t_df)}"

    # Should have multiple metrics
    metrics = set(df["metric"].unique())
    for m in ["revenue", "net_income", "operating_cf"]:
        assert m in metrics, f"Missing metric: {m}"

    # VRT revenue for 2025 should match snapshot
    vrt_rev_2025 = df[
        (df["ticker"] == "VRT") & (df["metric"] == "revenue") & (df["year"] == 2025)
    ]
    assert len(vrt_rev_2025) == 1, f"Expected 1 VRT revenue 2025 row, got {len(vrt_rev_2025)}"
    assert 9700 < vrt_rev_2025.iloc[0]["value_m"] < 10800

    print("PASSED")


def test_csv_file_write():
    print("test_csv_file_write...", end=" ")
    import pandas as pd

    with tempfile.TemporaryDirectory() as tmpdir:
        snap_path = os.path.join(tmpdir, "snapshot.csv")
        ts_path = os.path.join(tmpdir, "timeseries.csv")

        df_snap = client.export_snapshot_csv(TEST_TICKERS, output_path=snap_path)
        df_ts = client.export_timeseries_csv(TEST_TICKERS, output_path=ts_path)

        # Files should exist
        assert os.path.exists(snap_path), "Snapshot CSV not written"
        assert os.path.exists(ts_path), "Timeseries CSV not written"

        # Round-trip: read back and verify
        df_snap_read = pd.read_csv(snap_path)
        assert len(df_snap_read) == len(df_snap), "Snapshot row count mismatch after read-back"
        assert list(df_snap_read.columns) == list(df_snap.columns), "Snapshot columns mismatch"

        df_ts_read = pd.read_csv(ts_path)
        assert len(df_ts_read) == len(df_ts), "Timeseries row count mismatch after read-back"

    print("PASSED")


if __name__ == "__main__":
    print(f"Testing with tickers: {TEST_TICKERS}\n")
    test_snapshot_csv()
    test_timeseries_csv()
    test_csv_file_write()
    print("\nAll tests passed!")
