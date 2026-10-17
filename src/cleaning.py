"""
src/cleaning.py
Data cleaning module for OceanWatch.
Provides non-destructive cleaning transformations with comprehensive audit logging
and before/after quality metric comparisons.
Rule: Always work on a copy. Keep the original dataframe untouched.
"""

from typing import Any
import numpy as np
import pandas as pd


VALID_MISSING_STRATEGIES = {
    "leave_as_is",
    "drop_rows",
    "fill_mean",
    "fill_median",
    "fill_group_median",
    "interpolate_linear",
}


def clean_dataset(
    df: pd.DataFrame,
    remove_duplicates: bool = False,
    missing_strategy: str = "leave_as_is",
    target_columns: list[str] | None = None,
    group_col: str | None = "region",
    sort_col: str | None = "depth_m",
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    """Clean dataset based on explicit user strategies.

    Args:
        df: Input pandas DataFrame (will NOT be mutated).
        remove_duplicates: Whether to drop duplicate rows.
        missing_strategy: One of 'leave_as_is', 'drop_rows', 'fill_mean',
                          'fill_median', 'fill_group_median', 'interpolate_linear'.
        target_columns: Subset of numeric columns to apply missing imputation to.
                        If None, applies to all numeric columns.
        group_col: Categorical column used for group-wise median or isolated interpolation (e.g., 'region').
        sort_col: Sorting column for isolated interpolation (e.g. 'depth_m').

    Returns:
        (cleaned_df, cleaning_log)
    """
    if df is None:
        raise ValueError("Input DataFrame cannot be None.")
    if missing_strategy not in VALID_MISSING_STRATEGIES:
        raise ValueError(
            f"Invalid missing_strategy: '{missing_strategy}'. Must be one of {sorted(VALID_MISSING_STRATEGIES)}"
        )

    # Always make an explicit deep copy
    cleaned_df = df.copy(deep=True)
    cleaning_log: list[dict[str, Any]] = []

    # 1. Deduplication
    if remove_duplicates:
        initial_count = len(cleaned_df)
        cleaned_df = cleaned_df.drop_duplicates()
        dropped_dupes = initial_count - len(cleaned_df)
        cleaning_log.append({
            "step": "Deduplication",
            "description": f"Removed {dropped_dupes} duplicate rows.",
            "rows_affected": dropped_dupes,
            "details": {"previous_rows": initial_count, "remaining_rows": len(cleaned_df)},
        })

    # Determine numeric columns for missing value operations
    all_numeric_cols = [col for col in cleaned_df.columns if pd.api.types.is_numeric_dtype(cleaned_df[col])]
    if target_columns is not None:
        num_cols = [c for c in target_columns if c in all_numeric_cols]
    else:
        num_cols = all_numeric_cols

    # 2. Missing Value Treatment
    if missing_strategy == "leave_as_is":
        total_missing = int(cleaned_df[num_cols].isna().sum().sum()) if num_cols else 0
        cleaning_log.append({
            "step": "Missing Value Handling",
            "description": f"Retained {total_missing} missing values as-is (Default strategy).",
            "rows_affected": 0,
            "details": {"strategy": "leave_as_is", "total_missing": total_missing},
        })

    elif missing_strategy == "drop_rows":
        initial_count = len(cleaned_df)
        if num_cols:
            cleaned_df = cleaned_df.dropna(subset=num_cols)
        else:
            cleaned_df = cleaned_df.dropna()
        dropped_missing = initial_count - len(cleaned_df)
        cleaning_log.append({
            "step": "Missing Value Handling (Drop Rows)",
            "description": f"Dropped {dropped_missing} rows containing missing values in target columns.",
            "rows_affected": dropped_missing,
            "details": {"strategy": "drop_rows", "columns_evaluated": num_cols},
        })

    elif missing_strategy == "fill_mean":
        imputed_total = 0
        for col in num_cols:
            n_nan = int(cleaned_df[col].isna().sum())
            if n_nan > 0:
                mean_val = float(cleaned_df[col].mean())
                cleaned_df[col] = cleaned_df[col].fillna(mean_val)
                imputed_total += n_nan
        cleaning_log.append({
            "step": "Missing Value Handling (Mean Imputation)",
            "description": f"Imputed {imputed_total} missing values using column-wise means.",
            "rows_affected": imputed_total,
            "details": {"strategy": "fill_mean", "columns_imputed": num_cols},
        })

    elif missing_strategy == "fill_median":
        imputed_total = 0
        for col in num_cols:
            n_nan = int(cleaned_df[col].isna().sum())
            if n_nan > 0:
                median_val = float(cleaned_df[col].median())
                cleaned_df[col] = cleaned_df[col].fillna(median_val)
                imputed_total += n_nan
        cleaning_log.append({
            "step": "Missing Value Handling (Median Imputation)",
            "description": f"Imputed {imputed_total} missing values using robust column-wise medians.",
            "rows_affected": imputed_total,
            "details": {"strategy": "fill_median", "columns_imputed": num_cols},
        })

    elif missing_strategy == "fill_group_median":
        if group_col and group_col in cleaned_df.columns:
            imputed_total = 0
            for col in num_cols:
                n_nan = int(cleaned_df[col].isna().sum())
                if n_nan > 0:
                    # Calculate group medians
                    group_medians = cleaned_df.groupby(group_col)[col].transform("median")
                    # Fallback to global median if whole group is NaN
                    global_median = cleaned_df[col].median()
                    filled = cleaned_df[col].fillna(group_medians).fillna(global_median)
                    cleaned_df[col] = filled
                    imputed_total += n_nan
            cleaning_log.append({
                "step": "Missing Value Handling (Group-wise Median)",
                "description": f"Imputed {imputed_total} missing values using medians grouped by '{group_col}'.",
                "rows_affected": imputed_total,
                "details": {"strategy": "fill_group_median", "group_column": group_col, "columns_imputed": num_cols},
            })
        else:
            # Fallback to global median if group_col is unavailable
            return clean_dataset(
                df=df,
                remove_duplicates=remove_duplicates,
                missing_strategy="fill_median",
                target_columns=target_columns,
            )

    elif missing_strategy == "interpolate_linear":
        # Time or depth ordered linear interpolation strictly within location/group
        # Never interpolate across unrelated regions
        imputed_total = 0
        sort_cols = []
        if group_col and group_col in cleaned_df.columns:
            sort_cols.append(group_col)
        if sort_col and sort_col in cleaned_df.columns:
            sort_cols.append(sort_col)

        if sort_cols:
            cleaned_df = cleaned_df.sort_values(by=sort_cols).reset_index(drop=True)

        for col in num_cols:
            n_nan = int(cleaned_df[col].isna().sum())
            if n_nan > 0:
                if group_col and group_col in cleaned_df.columns:
                    # Interpolate strictly within groups
                    cleaned_df[col] = cleaned_df.groupby(group_col)[col].transform(
                        lambda s: s.interpolate(method="linear", limit_direction="both")
                    )
                else:
                    cleaned_df[col] = cleaned_df[col].interpolate(method="linear", limit_direction="both")
                
                # If any leading/trailing remains NaN, fill with median
                remaining = int(cleaned_df[col].isna().sum())
                if remaining > 0:
                    cleaned_df[col] = cleaned_df[col].fillna(cleaned_df[col].median())

                imputed_total += n_nan

        cleaning_log.append({
            "step": "Missing Value Handling (Isolated Linear Interpolation)",
            "description": f"Interpolated {imputed_total} missing values within isolated '{group_col}' groups.",
            "rows_affected": imputed_total,
            "details": {"strategy": "interpolate_linear", "group_column": group_col},
        })

    return cleaned_df, cleaning_log


def get_quality_comparison(raw_df: pd.DataFrame, cleaned_df: pd.DataFrame) -> dict[str, Any]:
    """Compute comprehensive before-and-after data quality metrics.

    Calculates:
    - Row count before vs after
    - Duplicate count before vs after
    - Missing percentage before vs after
    - Summary statistics (mean, std, median, min, max) for numeric columns
    """
    if raw_df is None or cleaned_df is None:
        raise ValueError("Both raw_df and cleaned_df must be provided.")

    raw_rows = len(raw_df)
    clean_rows = len(cleaned_df)

    raw_dupes = int(raw_df.duplicated().sum())
    clean_dupes = int(cleaned_df.duplicated().sum())

    raw_missing_cells = int(raw_df.isna().sum().sum())
    clean_missing_cells = int(cleaned_df.isna().sum().sum())

    raw_total_cells = raw_rows * len(raw_df.columns) if raw_rows > 0 else 1
    clean_total_cells = clean_rows * len(cleaned_df.columns) if clean_rows > 0 else 1

    raw_missing_pct = round((raw_missing_cells / raw_total_cells) * 100.0, 2)
    clean_missing_pct = round((clean_missing_cells / clean_total_cells) * 100.0, 2)

    # Per-variable comparison
    stats_comparison: dict[str, dict[str, Any]] = {}
    numeric_cols = [
        col for col in raw_df.columns
        if pd.api.types.is_numeric_dtype(raw_df[col]) and col in cleaned_df.columns
    ]

    for col in numeric_cols:
        r_series = raw_df[col].dropna()
        c_series = cleaned_df[col].dropna()

        stats_comparison[str(col)] = {
            "raw_count": int(r_series.count()),
            "clean_count": int(c_series.count()),
            "raw_mean": round(float(r_series.mean()), 3) if not r_series.empty else None,
            "clean_mean": round(float(c_series.mean()), 3) if not c_series.empty else None,
            "raw_std": round(float(r_series.std()), 3) if len(r_series) > 1 else None,
            "clean_std": round(float(c_series.std()), 3) if len(c_series) > 1 else None,
            "raw_median": round(float(r_series.median()), 3) if not r_series.empty else None,
            "clean_median": round(float(c_series.median()), 3) if not c_series.empty else None,
            "raw_min": round(float(r_series.min()), 3) if not r_series.empty else None,
            "clean_min": round(float(c_series.min()), 3) if not c_series.empty else None,
            "raw_max": round(float(r_series.max()), 3) if not r_series.empty else None,
            "clean_max": round(float(c_series.max()), 3) if not c_series.empty else None,
        }

    return {
        "raw_rows": raw_rows,
        "clean_rows": clean_rows,
        "raw_duplicates": raw_dupes,
        "clean_duplicates": clean_dupes,
        "raw_missing_pct": raw_missing_pct,
        "clean_missing_pct": clean_missing_pct,
        "raw_missing_cells": raw_missing_cells,
        "clean_missing_cells": clean_missing_cells,
        "variables": stats_comparison,
    }
