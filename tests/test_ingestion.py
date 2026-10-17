"""
tests/test_ingestion.py
Unit tests for src/ingestion.py.
Verifies file loading error handling (empty, missing), metadata construction,
and sample dataset generation and loading.
"""

import io
from pathlib import Path
import pytest
import pandas as pd

from src.ingestion import load_csv, build_metadata, load_sample


def test_load_csv_file_not_found():
    """Verify FileNotFoundError is raised for non-existent paths."""
    with pytest.raises(FileNotFoundError):
        load_csv("non_existent_ocean_file_xyz.csv")


def test_load_csv_empty_file(tmp_path: Path):
    """Verify ValueError is raised for empty (0 bytes) files."""
    empty_file = tmp_path / "empty.csv"
    empty_file.write_text("")
    with pytest.raises(ValueError, match="empty"):
        load_csv(empty_file)


def test_load_csv_from_buffer():
    """Verify loading from in-memory StringIO buffer."""
    csv_data = "latitude,longitude,depth_m,temperature_c\n10.5,-30.2,100,18.4\n"
    buffer = io.StringIO(csv_data)
    df = load_csv(buffer)
    assert len(df) == 1
    assert list(df.columns) == ["latitude", "longitude", "depth_m", "temperature_c"]


def test_build_metadata():
    """Verify metadata extraction preserves row counts, columns, units, and limitations."""
    df = pd.DataFrame({
        "temperature_c": [20.0, 21.0],
        "salinity_psu": [35.0, 35.2],
        "period": ["2015-2019", "2015-2019"],
    })
    meta = build_metadata(df, source_name="Test Source", is_synthetic=True)
    assert meta["source_name"] == "Test Source"
    assert meta["is_synthetic"] is True
    assert meta["row_count"] == 2
    assert meta["column_count"] == 3
    assert meta["reference_period"] == "2015-2019"
    assert meta["units"]["temperature_c"] == "°C"
    assert meta["units"]["salinity_psu"] == "PSU"


def test_load_sample(tmp_path: Path):
    """Verify sample loading automatically generates and loads synthetic ocean dataset."""
    sample_file = tmp_path / "sample.csv"
    df, meta = load_sample(str(sample_file))
    assert sample_file.exists()
    assert len(df) >= 3000
    assert meta["is_synthetic"] is True
    assert "temperature_c" in df.columns
    assert "salinity_psu" in df.columns
    assert "dissolved_oxygen_ml_l" in df.columns
