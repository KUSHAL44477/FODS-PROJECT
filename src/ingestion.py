"""
src/ingestion.py
Data ingestion module for OceanWatch.
Handles loading CSV datasets, building standardized metadata, and loading the sample dataset.
"""

from datetime import datetime, timezone
import io
import os
from pathlib import Path
from typing import Any, BinaryIO, TextIO, Union

import pandas as pd


STANDARD_OCEAN_UNITS = {
    "temperature_c": "°C",
    "salinity_psu": "PSU",
    "dissolved_oxygen_ml_l": "ml/L",
    "depth_m": "meters",
    "latitude": "degrees_north",
    "longitude": "degrees_east",
}


def load_csv(file_or_path: Union[str, Path, io.BytesIO, io.StringIO, BinaryIO, TextIO]) -> pd.DataFrame:
    """Load a CSV dataset from a file path or file-like buffer into a pandas DataFrame.

    Raises clear, descriptive ValueError or FileNotFoundError if:
    - The file does not exist.
    - The file is completely empty (0 bytes).
    - The file has unreadable encoding.
    - The CSV contains no parsable columns or rows.
    """
    if file_or_path is None:
        raise ValueError("Invalid input: file_or_path cannot be None.")

    # Check path existence and empty file if string or Path
    if isinstance(file_or_path, (str, Path)):
        path_obj = Path(file_or_path)
        if not path_obj.exists():
            raise FileNotFoundError(f"CSV file not found at path: {path_obj}")
        if path_obj.stat().st_size == 0:
            raise ValueError(f"File at '{path_obj}' is empty (0 bytes).")

    # If buffer-like with getbuffer or getvalue, check length
    if hasattr(file_or_path, "getvalue"):
        val = file_or_path.getvalue()
        if len(val) == 0:
            raise ValueError("Uploaded file/buffer is empty (0 bytes).")
        # Reset pointer
        if hasattr(file_or_path, "seek"):
            file_or_path.seek(0)

    # Attempt to load with common encodings
    encodings_to_try = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]
    last_error: Exception | None = None

    for enc in encodings_to_try:
        try:
            if hasattr(file_or_path, "seek"):
                file_or_path.seek(0)
            df = pd.read_csv(file_or_path, encoding=enc)
            if df.empty and len(df.columns) == 0:
                raise ValueError("The CSV file contains no columns or data.")
            if len(df.columns) == 0:
                raise ValueError("No columns could be parsed from the CSV file.")
            return df
        except UnicodeDecodeError as ude:
            last_error = ude
            continue
        except pd.errors.EmptyDataError:
            raise ValueError("The CSV file is empty and contains no headers or records.")
        except Exception as e:
            if isinstance(e, ValueError):
                raise
            last_error = e

    raise ValueError(f"Could not read CSV file with supported encodings. Error details: {last_error}")


def build_metadata(
    df: pd.DataFrame,
    source_name: str,
    dataset_title: str | None = None,
    units: dict[str, str] | None = None,
    reference_period: str | None = None,
    limitations: str | None = None,
    is_synthetic: bool = False,
) -> dict[str, Any]:
    """Construct structured dataset metadata dictionary.

    Enforces data provenance rules:
    - Never invent timestamps for climatological averages.
    - Explicitly tags synthetic datasets.
    - Preserves row counts, column types, and unit definitions.
    """
    if df is None:
        raise ValueError("DataFrame cannot be None when building metadata.")

    # Infer or assign units
    resolved_units = {}
    for col in df.columns:
        col_lower = str(col).strip().lower()
        if units and col in units:
            resolved_units[col] = units[col]
        elif col_lower in STANDARD_OCEAN_UNITS:
            resolved_units[col] = STANDARD_OCEAN_UNITS[col_lower]
        else:
            resolved_units[col] = "unspecified"

    # Infer reference period if present in dataset
    period_str = reference_period
    if not period_str:
        if "period" in df.columns and not df["period"].dropna().empty:
            unique_periods = df["period"].dropna().astype(str).unique()
            if len(unique_periods) <= 3:
                period_str = ", ".join(unique_periods)
            else:
                period_str = f"{unique_periods[0]} to {unique_periods[-1]} ({len(unique_periods)} periods)"
        else:
            period_str = "Not specified / Climatological average"

    default_limitations = (
        "SYNTHETIC SAMPLE DATA: Generated for educational / FODS coursework demonstration only. "
        "Contains intentionally injected missing values, duplicates, and physical outliers. "
        "Not validated for maritime navigation or actual climate forecasting."
        if is_synthetic
        else "Observational or user-provided dataset. Verify sensor calibration and spatio-temporal coverage."
    )

    metadata: dict[str, Any] = {
        "source_name": source_name,
        "dataset_title": dataset_title or source_name,
        "is_synthetic": is_synthetic,
        "row_count": int(len(df)),
        "column_count": int(len(df.columns)),
        "columns": list(df.columns),
        "import_time": datetime.now(timezone.utc).isoformat(),
        "reference_period": period_str,
        "units": resolved_units,
        "limitations": limitations or default_limitations,
    }
    return metadata


def load_sample(sample_path: str = "data/raw/sample_ocean.csv") -> tuple[pd.DataFrame, dict[str, Any]]:
    """Load the realistic synthetic sample dataset, generating it first if missing.

    Returns:
        (df, metadata)
    """
    path_obj = Path(sample_path)
    if not path_obj.exists() or path_obj.stat().st_size == 0:
        # Dynamically import and run script generator
        from scripts.make_sample_data import generate_sample_dataset

        generate_sample_dataset(output_path=str(path_obj))

    df = load_csv(path_obj)
    metadata = build_metadata(
        df=df,
        source_name="Synthetic Ocean Sample (scripts/make_sample_data.py)",
        dataset_title="OceanWatch Synthetic Benchmark Dataset",
        reference_period="2010-2024 (5-year binned climatology)",
        is_synthetic=True,
    )
    return df, metadata
