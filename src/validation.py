"""
src/validation.py
Data validation module for OceanWatch.
Provides structured checks for column completeness, data types, physical ranges,
impossible oceanographic values, missingness, and duplicate records.
Rule: Never silently drop rows during validation.
"""

from typing import Any
import numpy as np
import pandas as pd


# Physically plausible bounds for marine indicators
DEFAULT_OCEAN_RANGES: dict[str, tuple[float | None, float | None]] = {
    "temperature_c": (-2.0, 40.0),
    "salinity_psu": (0.0, 45.0),
    "dissolved_oxygen_ml_l": (0.0, 15.0),
    "latitude": (-90.0, 90.0),
    "longitude": (-180.0, 180.0),
    "depth_m": (0.0, 11500.0),  # Challenger Deep is ~10,928m
}


def validate_dataset(
    df: pd.DataFrame,
    custom_ranges: dict[str, tuple[float | None, float | None]] | None = None,
) -> dict[str, Any]:
    """Perform comprehensive validation on an oceanographic dataset.

    Returns a structured dictionary with validation findings:
    - is_valid: bool (True if dataset contains at least one numeric indicator column)
    - total_rows: int
    - total_columns: int
    - numeric_columns: list[str]
    - non_numeric_columns: list[str]
    - missing_counts: dict[str, int]
    - missing_percentages: dict[str, float]
    - total_missing_cells: int
    - overall_missing_pct: float
    - duplicate_rows_count: int
    - range_violations: dict[str, dict] (counts, bounds, sample violating row indices)
    - impossible_values: dict[str, list[dict]]
    - suspicious_row_indices: list[int] (union of indices with violations or impossible values)
    - summary_messages: list[str]
    """
    if df is None:
        raise ValueError("DataFrame cannot be None.")

    total_rows = len(df)
    total_cols = len(df.columns)

    if total_rows == 0 or total_cols == 0:
        return {
            "is_valid": False,
            "total_rows": total_rows,
            "total_columns": total_cols,
            "numeric_columns": [],
            "non_numeric_columns": [],
            "missing_counts": {},
            "missing_percentages": {},
            "total_missing_cells": 0,
            "overall_missing_pct": 0.0,
            "duplicate_rows_count": 0,
            "range_violations": {},
            "impossible_values": {},
            "suspicious_row_indices": [],
            "summary_messages": ["Dataset is empty (0 rows or 0 columns)."],
        }

    # Identify numeric vs non-numeric columns
    numeric_cols: list[str] = []
    non_numeric_cols: list[str] = []
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            numeric_cols.append(str(col))
        else:
            non_numeric_cols.append(str(col))

    # At least one numeric column is required for ocean analysis
    is_valid = len(numeric_cols) > 0

    # Missing counts and percentages
    missing_counts = {str(col): int(df[col].isna().sum()) for col in df.columns}
    missing_pcts = {
        str(col): round((cnt / total_rows) * 100.0, 2) if total_rows > 0 else 0.0
        for col, cnt in missing_counts.items()
    }
    total_missing_cells = int(df.isna().sum().sum())
    overall_missing_pct = round(
        (total_missing_cells / (total_rows * total_cols)) * 100.0, 2
    ) if (total_rows * total_cols) > 0 else 0.0

    # Duplicate rows count
    duplicate_rows_count = int(df.duplicated().sum())

    # Range and impossible values checks
    ranges = dict(DEFAULT_OCEAN_RANGES)
    if custom_ranges:
        ranges.update(custom_ranges)

    range_violations: dict[str, dict[str, Any]] = {}
    impossible_values: dict[str, list[dict[str, Any]]] = {}
    suspicious_indices_set: set[int] = set()

    for col, (min_val, max_val) in ranges.items():
        if col not in df.columns:
            continue

        series = df[col]
        # Attempt conversion to numeric if object dtype
        if not pd.api.types.is_numeric_dtype(series):
            num_series = pd.to_numeric(series, errors="coerce")
            coerced_nans = int((series.notna() & num_series.isna()).sum())
            if coerced_nans > 0:
                impossible_values.setdefault(col, []).append({
                    "issue": "Non-numeric characters in expected numerical field",
                    "count": coerced_nans,
                })
        else:
            num_series = series

        valid_vals = num_series.dropna()
        if valid_vals.empty:
            continue

        violating_mask = pd.Series(False, index=df.index)
        if min_val is not None:
            violating_mask = violating_mask | (num_series < min_val)
        if max_val is not None:
            violating_mask = violating_mask | (num_series > max_val)

        violating_indices = df.index[violating_mask].tolist()
        if violating_indices:
            suspicious_indices_set.update(violating_indices)
            range_violations[col] = {
                "count": len(violating_indices),
                "allowed_min": min_val,
                "allowed_max": max_val,
                "observed_min": float(valid_vals.min()),
                "observed_max": float(valid_vals.max()),
                "violating_indices": violating_indices[:20],  # Sample first 20
            }

            # Check specifically for physically impossible ocean values
            if col == "depth_m" and (num_series < 0).any():
                neg_depth_count = int((num_series < 0).sum())
                impossible_values.setdefault(col, []).append({
                    "issue": "Negative depth measurement (ocean depth must be >= 0)",
                    "count": neg_depth_count,
                })
            if col == "latitude" and ((num_series < -90) | (num_series > 90)).any():
                invalid_lat = int(((num_series < -90) | (num_series > 90)).sum())
                impossible_values.setdefault(col, []).append({
                    "issue": "Latitude outside valid coordinate range [-90, +90]",
                    "count": invalid_lat,
                })
            if col == "longitude" and ((num_series < -180) | (num_series > 180)).any():
                invalid_lon = int(((num_series < -180) | (num_series > 180)).sum())
                impossible_values.setdefault(col, []).append({
                    "issue": "Longitude outside valid coordinate range [-180, +180]",
                    "count": invalid_lon,
                })
            if col == "temperature_c" and ((num_series < -2.5) | (num_series > 42.0)).any():
                extreme_temp = int(((num_series < -2.5) | (num_series > 42.0)).sum())
                impossible_values.setdefault(col, []).append({
                    "issue": "Extreme water temperature (liquid seawater freezes at ~ -1.9°C)",
                    "count": extreme_temp,
                })
            if col == "salinity_psu" and (num_series < 0).any():
                neg_salinity = int((num_series < 0).sum())
                impossible_values.setdefault(col, []).append({
                    "issue": "Negative salinity (salinity cannot be negative)",
                    "count": neg_salinity,
                })

    summary_messages: list[str] = []
    if not is_valid:
        summary_messages.append("Dataset is invalid: No numeric indicator columns detected.")
    else:
        summary_messages.append(
            f"Dataset contains {total_rows:,} rows, {total_cols} columns, "
            f"with {len(numeric_cols)} numeric indicators."
        )

    if duplicate_rows_count > 0:
        summary_messages.append(f"Found {duplicate_rows_count:,} duplicate rows.")

    if total_missing_cells > 0:
        summary_messages.append(
            f"Missing data present: {total_missing_cells:,} missing cells ({overall_missing_pct}% overall)."
        )

    if range_violations:
        total_viols = sum(v["count"] for v in range_violations.values())
        summary_messages.append(
            f"Detected {total_viols:,} range violations across {len(range_violations)} columns."
        )

    return {
        "is_valid": is_valid,
        "total_rows": total_rows,
        "total_columns": total_cols,
        "numeric_columns": numeric_cols,
        "non_numeric_columns": non_numeric_cols,
        "missing_counts": missing_counts,
        "missing_percentages": missing_pcts,
        "total_missing_cells": total_missing_cells,
        "overall_missing_pct": overall_missing_pct,
        "duplicate_rows_count": duplicate_rows_count,
        "range_violations": range_violations,
        "impossible_values": impossible_values,
        "suspicious_row_indices": sorted(suspicious_indices_set),
        "summary_messages": summary_messages,
    }
