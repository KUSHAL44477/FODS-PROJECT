"""
tests/test_validation.py
Unit tests for src/validation.py.
Validates detection of missing columns, non-numeric values, out-of-range bounds,
impossible oceanographic values, missingness %, and duplicates.
"""

import pytest
import pandas as pd
import numpy as np

from src.validation import validate_dataset, DEFAULT_OCEAN_RANGES


def test_validation_clean_data():
    """Verify that a compliant dataset passes validation without false alarms."""
    df = pd.DataFrame({
        "latitude": [10.5, 20.0, -15.2],
        "longitude": [-40.0, -35.2, 50.1],
        "depth_m": [0.0, 100.0, 500.0],
        "temperature_c": [25.4, 18.2, 8.5],
        "salinity_psu": [35.2, 35.8, 34.9],
        "dissolved_oxygen_ml_l": [5.2, 4.8, 3.1],
    })
    report = validate_dataset(df)
    assert report["is_valid"] is True
    assert report["total_rows"] == 3
    assert report["total_columns"] == 6
    assert report["total_missing_cells"] == 0
    assert report["overall_missing_pct"] == 0.0
    assert report["duplicate_rows_count"] == 0
    assert len(report["range_violations"]) == 0
    assert len(report["impossible_values"]) == 0
    assert len(report["suspicious_row_indices"]) == 0


def test_validation_empty_and_no_numeric_columns():
    """Empty dataframes or dataframes without numeric indicators must be flagged."""
    empty_df = pd.DataFrame()
    report_empty = validate_dataset(empty_df)
    assert report_empty["is_valid"] is False
    assert report_empty["total_rows"] == 0

    text_only_df = pd.DataFrame({"region": ["Atlantic", "Pacific"], "period": ["2015", "2020"]})
    report_text = validate_dataset(text_only_df)
    assert report_text["is_valid"] is False
    assert len(report_text["numeric_columns"]) == 0


def test_validation_detects_missing_values_and_duplicates():
    """Check precise counting of missing values, percentages, and duplicates."""
    df = pd.DataFrame({
        "temperature_c": [20.0, np.nan, 20.0, 15.0],
        "salinity_psu": [35.0, 34.0, 35.0, np.nan],
    })
    report = validate_dataset(df)
    assert report["total_rows"] == 4
    assert report["missing_counts"]["temperature_c"] == 1
    assert report["missing_counts"]["salinity_psu"] == 1
    assert report["missing_percentages"]["temperature_c"] == 25.0
    assert report["missing_percentages"]["salinity_psu"] == 25.0
    assert report["total_missing_cells"] == 2
    assert report["overall_missing_pct"] == 25.0  # 2 missing out of 8 total cells
    assert report["duplicate_rows_count"] == 1  # Row 0 and Row 2 are identical


def test_validation_range_violations_and_impossible_values():
    """Test flagging of out-of-range sensor spikes and impossible ocean values."""
    df = pd.DataFrame({
        "latitude": [10.0, 95.0, -10.0],          # 95 is > 90
        "longitude": [0.0, 200.0, 10.0],          # 200 is > 180
        "depth_m": [10.0, -25.0, 50.0],           # -25 is negative depth
        "temperature_c": [20.0, 55.0, -10.0],     # 55.0 > 40.0, -10.0 < -2.0
        "salinity_psu": [35.0, -2.0, 60.0],       # -2.0 is negative salinity, 60 > 45
        "dissolved_oxygen_ml_l": [5.0, 18.0, 6.0], # 18.0 > 15.0
    })
    report = validate_dataset(df)
    assert report["is_valid"] is True

    # Check violations detected
    assert "temperature_c" in report["range_violations"]
    assert report["range_violations"]["temperature_c"]["count"] == 2  # 55.0 and -10.0
    assert "salinity_psu" in report["range_violations"]
    assert report["range_violations"]["salinity_psu"]["count"] == 2  # -2.0 and 60.0
    assert "depth_m" in report["range_violations"]
    assert report["range_violations"]["depth_m"]["count"] == 1  # -25.0

    # Check impossible values flagged
    assert "depth_m" in report["impossible_values"]
    assert any("Negative depth" in item["issue"] for item in report["impossible_values"]["depth_m"])
    assert "latitude" in report["impossible_values"]
    assert "salinity_psu" in report["impossible_values"]

    # Verify rows were NOT dropped
    assert report["total_rows"] == 3


def test_validation_never_drops_rows():
    """Validation must never mutate the input dataframe or drop rows."""
    df = pd.DataFrame({
        "temperature_c": [100.0, np.nan, -50.0],
        "salinity_psu": [np.nan, 99.0, -10.0],
    })
    df_copy = df.copy(deep=True)
    report = validate_dataset(df)
    pd.testing.assert_frame_equal(df, df_copy)
    assert len(df) == 3
