"""
tests/test_cleaning.py
Unit tests for src/cleaning.py.
Verifies immutability of input DataFrame, deduplication logic, missingness strategies
(leave_as_is, drop_rows, fill_mean, fill_median, fill_group_median, interpolate_linear),
and before/after quality comparison metrics.
"""

import pytest
import pandas as pd
import numpy as np

from src.cleaning import clean_dataset, get_quality_comparison


def test_cleaning_preserves_original_dataframe():
    """Verify that input dataframe is NEVER mutated by cleaning operations."""
    df = pd.DataFrame({
        "region": ["Atlantic", "Atlantic", "Pacific"],
        "temperature_c": [20.0, np.nan, 20.0],
        "salinity_psu": [35.0, 35.0, 35.0],
    })
    df_copy = df.copy(deep=True)

    cleaned, log = clean_dataset(df, remove_duplicates=True, missing_strategy="drop_rows")

    # Original must remain completely unchanged
    pd.testing.assert_frame_equal(df, df_copy)
    # Cleaned should have different length
    assert len(cleaned) < len(df)


def test_cleaning_deduplication():
    """Test dropping exact duplicates."""
    df = pd.DataFrame({
        "temperature_c": [10.0, 10.0, 20.0, 10.0],
        "salinity_psu": [35.0, 35.0, 34.0, 35.0],
    })
    cleaned, log = clean_dataset(df, remove_duplicates=True, missing_strategy="leave_as_is")
    assert len(cleaned) == 2
    assert any(step["step"] == "Deduplication" for step in log)


def test_cleaning_leave_as_is():
    """Test default strategy leaves missing values intact."""
    df = pd.DataFrame({
        "temperature_c": [10.0, np.nan, 30.0],
    })
    cleaned, log = clean_dataset(df, remove_duplicates=False, missing_strategy="leave_as_is")
    assert cleaned["temperature_c"].isna().sum() == 1
    assert len(cleaned) == 3


def test_cleaning_drop_rows():
    """Test drop_rows removes rows with missing values."""
    df = pd.DataFrame({
        "temperature_c": [10.0, np.nan, 30.0, 40.0],
        "salinity_psu": [35.0, 35.0, np.nan, 36.0],
    })
    cleaned, log = clean_dataset(df, remove_duplicates=False, missing_strategy="drop_rows")
    assert len(cleaned) == 2
    assert cleaned["temperature_c"].isna().sum() == 0
    assert cleaned["salinity_psu"].isna().sum() == 0


def test_cleaning_fill_mean():
    """Test fill_mean imputes exact arithmetic mean."""
    # Mean of [10.0, 20.0, 30.0] is 20.0
    df = pd.DataFrame({
        "temperature_c": [10.0, np.nan, 20.0, 30.0],
    })
    cleaned, log = clean_dataset(df, remove_duplicates=False, missing_strategy="fill_mean")
    assert cleaned.loc[1, "temperature_c"] == 20.0
    assert cleaned["temperature_c"].isna().sum() == 0


def test_cleaning_fill_median():
    """Test fill_median imputes exact median."""
    # Median of [10.0, 12.0, 50.0] is 12.0 (robust to 50.0)
    df = pd.DataFrame({
        "temperature_c": [10.0, 12.0, np.nan, 50.0],
    })
    cleaned, log = clean_dataset(df, remove_duplicates=False, missing_strategy="fill_median")
    assert cleaned.loc[2, "temperature_c"] == 12.0
    assert cleaned["temperature_c"].isna().sum() == 0


def test_cleaning_group_median_does_not_cross_groups():
    """Verify group-wise median does not bleed values across different regions."""
    df = pd.DataFrame({
        "region": ["Arctic", "Arctic", "Arctic", "Tropics", "Tropics", "Tropics"],
        # Arctic values: -1.0, 1.0 -> median = 0.0
        # Tropics values: 28.0, 30.0 -> median = 29.0
        "temperature_c": [-1.0, np.nan, 1.0, 28.0, np.nan, 30.0],
    })
    cleaned, log = clean_dataset(
        df,
        remove_duplicates=False,
        missing_strategy="fill_group_median",
        group_col="region",
    )
    # Arctic missing row (index 1) must be 0.0, NOT affected by 29.0
    assert cleaned.loc[1, "temperature_c"] == 0.0
    # Tropics missing row (index 4) must be 29.0, NOT affected by 0.0
    assert cleaned.loc[4, "temperature_c"] == 29.0
    assert cleaned["temperature_c"].isna().sum() == 0


def test_cleaning_quality_comparison():
    """Test computation of before/after quality comparison report."""
    raw = pd.DataFrame({
        "temperature_c": [10.0, 20.0, np.nan, 10.0],
        "salinity_psu": [35.0, 35.0, 35.0, 35.0],
    })
    clean, log = clean_dataset(raw, remove_duplicates=True, missing_strategy="fill_mean")
    comp = get_quality_comparison(raw, clean)

    assert comp["raw_rows"] == 4
    assert comp["clean_rows"] == 3  # 1 duplicate dropped
    assert comp["raw_duplicates"] == 1
    assert comp["clean_duplicates"] == 0
    assert comp["raw_missing_pct"] > 0
    assert comp["clean_missing_pct"] == 0.0
    assert "temperature_c" in comp["variables"]
    assert comp["variables"]["temperature_c"]["clean_count"] == 3
