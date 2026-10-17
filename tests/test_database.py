"""
tests/test_database.py
Unit tests for src/database.py.
Verifies schema initialization, table creation, foreign key enforcement,
NOT NULL constraints, and analysis run logging.
"""

import sqlite3
import pytest
from pathlib import Path

from src.database import init_db, get_connection, register_source, log_analysis_run, list_runs


@pytest.fixture
def temp_db(tmp_path: Path) -> str:
    """Fixture to provide a clean temporary SQLite database path."""
    db_file = tmp_path / "test_oceanwatch.db"
    init_db(str(db_file))
    return str(db_file)


def test_database_initialization(temp_db: str):
    """Verify all 6 tables from Section 5.7 and default indicators are created."""
    conn = get_connection(temp_db)
    cursor = conn.cursor()

    # Query sqlite_master for table names
    tables = [
        row[0]
        for row in cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
        ).fetchall()
    ]

    expected_tables = {
        "dim_source",
        "dim_time",
        "dim_location",
        "dim_indicator",
        "fact_measurement",
        "analysis_run",
    }
    assert expected_tables.issubset(set(tables))

    # Verify standard indicators were seeded
    indicators = [
        row["indicator_name"]
        for row in cursor.execute("SELECT indicator_name FROM dim_indicator").fetchall()
    ]
    assert "temperature_c" in indicators
    assert "salinity_psu" in indicators
    assert "dissolved_oxygen_ml_l" in indicators
    conn.close()


def test_database_foreign_key_enforcement(temp_db: str):
    """Foreign key enforcement must reject fact_measurement with non-existent foreign keys."""
    conn = get_connection(temp_db)

    # Attempt inserting fact_measurement with non-existent source_id=999, location_id=999, indicator_id=999
    with pytest.raises(sqlite3.IntegrityError):
        with conn:
            conn.execute(
                """
                INSERT INTO fact_measurement (source_id, location_id, indicator_id, value)
                VALUES (999, 999, 999, 21.5);
                """
            )
    conn.close()


def test_database_not_null_constraints(temp_db: str):
    """NOT NULL constraints must reject incomplete records."""
    conn = get_connection(temp_db)

    # dim_source requires source_name and dataset_title NOT NULL
    with pytest.raises(sqlite3.IntegrityError):
        with conn:
            conn.execute(
                """
                INSERT INTO dim_source (source_name, dataset_title, access_date)
                VALUES (NULL, 'Title', '2026-10-17');
                """
            )

    # dim_location requires latitude NOT NULL
    with pytest.raises(sqlite3.IntegrityError):
        with conn:
            conn.execute(
                """
                INSERT INTO dim_location (latitude, longitude, depth_m)
                VALUES (NULL, 10.0, 50.0);
                """
            )
    conn.close()


def test_register_source_and_run_logging(temp_db: str):
    """Verify source registration and audit run logging with JSON serialization."""
    source_id = register_source(
        db_path=temp_db,
        source_name="NOAA WOA23 Test",
        dataset_title="World Ocean Atlas 2023 Climatology",
        source_url="https://www.ncei.noaa.gov/woa23",
        citation="Locarnini et al., 2023",
    )
    assert isinstance(source_id, int)
    assert source_id > 0

    run_id = log_analysis_run(
        db_path=temp_db,
        algorithm="Data Cleaning (fill_mean)",
        summary_dict={"imputed_values": 45, "missing_pct": 0.0},
        cleaning_config_dict={"strategy": "fill_mean", "deduplicate": True},
        source_id=source_id,
    )
    assert isinstance(run_id, int)
    assert run_id > 0

    runs = list_runs(temp_db)
    assert len(runs) >= 1
    latest = runs[0]
    assert latest["run_id"] == run_id
    assert latest["source_id"] == source_id
    assert latest["source_name"] == "NOAA WOA23 Test"
    assert latest["algorithm"] == "Data Cleaning (fill_mean)"
    assert latest["summary"]["imputed_values"] == 45
    assert latest["cleaning_config"]["deduplicate"] is True
