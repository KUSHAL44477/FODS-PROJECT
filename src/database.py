"""
src/database.py
Database management module for OceanWatch (SQLite backend).
Implements a normalized star schema with dimension tables, measurement facts,
and audit logs of data analysis runs. Enforces foreign key constraints.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any


DEFAULT_DB_PATH = "oceanwatch.db"


def get_connection(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Open a connection to the SQLite database with foreign keys enabled."""
    db_file = Path(db_path)
    if db_file.parent and not db_file.parent.exists():
        db_file.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_file))
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    """Initialize database tables, foreign keys, and indexes if they do not exist."""
    conn = get_connection(db_path)
    with conn:
        conn.executescript("""
        PRAGMA foreign_keys = ON;

        CREATE TABLE IF NOT EXISTS dim_source (
            source_id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_name TEXT NOT NULL,
            dataset_title TEXT NOT NULL,
            source_url TEXT,
            access_date TEXT NOT NULL,
            citation TEXT
        );

        CREATE TABLE IF NOT EXISTS dim_time (
            time_id INTEGER PRIMARY KEY AUTOINCREMENT,
            period_label TEXT NOT NULL,
            start_date TEXT,
            end_date TEXT,
            temporal_resolution TEXT
        );

        CREATE TABLE IF NOT EXISTS dim_location (
            location_id INTEGER PRIMARY KEY AUTOINCREMENT,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            region_name TEXT,
            depth_m REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS dim_indicator (
            indicator_id INTEGER PRIMARY KEY AUTOINCREMENT,
            indicator_name TEXT NOT NULL UNIQUE,
            standard_unit TEXT NOT NULL,
            description TEXT
        );

        CREATE TABLE IF NOT EXISTS fact_measurement (
            measurement_id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id INTEGER NOT NULL REFERENCES dim_source(source_id) ON DELETE CASCADE,
            time_id INTEGER REFERENCES dim_time(time_id) ON DELETE SET NULL,
            location_id INTEGER NOT NULL REFERENCES dim_location(location_id) ON DELETE CASCADE,
            indicator_id INTEGER NOT NULL REFERENCES dim_indicator(indicator_id) ON DELETE CASCADE,
            value REAL NOT NULL,
            quality_flag INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS analysis_run (
            run_id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id INTEGER REFERENCES dim_source(source_id) ON DELETE SET NULL,
            run_timestamp TEXT NOT NULL,
            cleaning_config TEXT,
            algorithm TEXT NOT NULL,
            summary_json TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_measurement_source ON fact_measurement(source_id);
        CREATE INDEX IF NOT EXISTS idx_measurement_indicator ON fact_measurement(indicator_id);
        CREATE INDEX IF NOT EXISTS idx_measurement_location ON fact_measurement(location_id);
        CREATE INDEX IF NOT EXISTS idx_analysis_timestamp ON analysis_run(run_timestamp);
        """)

        # Seed standard oceanographic indicators if not present
        standard_indicators = [
            ("temperature_c", "°C", "Sea water temperature in Celsius"),
            ("salinity_psu", "PSU", "Practical Salinity Unit"),
            ("dissolved_oxygen_ml_l", "ml/L", "Dissolved oxygen volume per liter of seawater"),
        ]
        for name, unit, desc in standard_indicators:
            conn.execute(
                """
                INSERT OR IGNORE INTO dim_indicator (indicator_name, standard_unit, description)
                VALUES (?, ?, ?)
                """,
                (name, unit, desc),
            )
    conn.close()


def register_source(
    db_path: str = DEFAULT_DB_PATH,
    source_name: str = "Unknown",
    dataset_title: str = "Ocean Dataset",
    source_url: str | None = None,
    citation: str | None = None,
) -> int:
    """Register a dataset source in dim_source and return its source_id."""
    init_db(db_path)
    conn = get_connection(db_path)
    access_date = datetime.now(timezone.utc).isoformat()
    with conn:
        cursor = conn.execute(
            """
            INSERT INTO dim_source (source_name, dataset_title, source_url, access_date, citation)
            VALUES (?, ?, ?, ?, ?)
            """,
            (source_name, dataset_title, source_url, access_date, citation),
        )
        source_id = cursor.lastrowid
    conn.close()
    return int(source_id)


def log_analysis_run(
    db_path: str = DEFAULT_DB_PATH,
    algorithm: str = "Generic Analysis",
    summary_dict: dict[str, Any] | None = None,
    cleaning_config_dict: dict[str, Any] | None = None,
    source_id: int | None = None,
) -> int:
    """Log an analysis run event into analysis_run table. Returns run_id."""
    init_db(db_path)
    conn = get_connection(db_path)
    run_timestamp = datetime.now(timezone.utc).isoformat()
    cleaning_json = json.dumps(cleaning_config_dict or {})
    summary_json = json.dumps(summary_dict or {})

    with conn:
        cursor = conn.execute(
            """
            INSERT INTO analysis_run (source_id, run_timestamp, cleaning_config, algorithm, summary_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (source_id, run_timestamp, cleaning_json, algorithm, summary_json),
        )
        run_id = cursor.lastrowid
    conn.close()
    return int(run_id)


def list_runs(db_path: str = DEFAULT_DB_PATH, limit: int = 50) -> list[dict[str, Any]]:
    """Retrieve logged analysis runs with parsed summary JSON."""
    init_db(db_path)
    conn = get_connection(db_path)
    with conn:
        rows = conn.execute(
            """
            SELECT r.run_id, r.source_id, s.source_name, r.run_timestamp,
                   r.cleaning_config, r.algorithm, r.summary_json
            FROM analysis_run r
            LEFT JOIN dim_source s ON r.source_id = s.source_id
            ORDER BY r.run_id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    results: list[dict[str, Any]] = []
    for r in rows:
        results.append({
            "run_id": r["run_id"],
            "source_id": r["source_id"],
            "source_name": r["source_name"] or "None",
            "run_timestamp": r["run_timestamp"],
            "cleaning_config": json.loads(r["cleaning_config"]) if r["cleaning_config"] else {},
            "algorithm": r["algorithm"],
            "summary": json.loads(r["summary_json"]) if r["summary_json"] else {},
        })
    conn.close()
    return results
