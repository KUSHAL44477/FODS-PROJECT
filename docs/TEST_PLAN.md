# OceanWatch Quality Assurance & Test Plan

This document defines the testing strategy, test matrix, and verification commands for the OceanWatch application.

---

## 1. Test Architecture & Execution

The test suite is built on `pytest`. All tests operate on hand-computed, deterministic datasets to ensure mathematical precision without dependence on network downloads or non-deterministic state.

### Running the Test Suite
```bash
# Activate virtual environment
.\venv\Scripts\activate   # Windows
# or: source venv/bin/activate  # Unix/macOS

# Run complete test suite with verbose output
pytest -v

# Run with test coverage report
pytest --cov=src tests/
```

---

## 2. Test Matrix

| Test Module | Test Name | Target Function / Capability | Expected Outcome | Status |
|:---|:---|:---|:---|:---|
| `test_validation.py` | `test_validation_clean_data` | `validate_dataset` | Compliant dataset passes with 0 violations and 0 missingness | ✅ Passed |
| `test_validation.py` | `test_validation_empty_and_no_numeric_columns` | `validate_dataset` | Flags empty or non-numeric dataframes as invalid | ✅ Passed |
| `test_validation.py` | `test_validation_detects_missing_values_and_duplicates` | `validate_dataset` | Correctly counts missing cells, missing %, and duplicate rows | ✅ Passed |
| `test_validation.py` | `test_validation_range_violations_and_impossible_values` | `validate_dataset` | Flags temperature extremes, negative depth, and invalid coords | ✅ Passed |
| `test_validation.py` | `test_validation_never_drops_rows` | `validate_dataset` | Input DataFrame remains completely unchanged after audit | ✅ Passed |
| `test_cleaning.py` | `test_cleaning_preserves_original_dataframe` | `clean_dataset` | Deep copy preserved; original dataframe is never mutated | ✅ Passed |
| `test_cleaning.py` | `test_cleaning_deduplication` | `clean_dataset` | Removes exact duplicate rows and logs count | ✅ Passed |
| `test_cleaning.py` | `test_cleaning_leave_as_is` | `clean_dataset` | Default strategy leaves missing values intact | ✅ Passed |
| `test_cleaning.py` | `test_cleaning_drop_rows` | `clean_dataset` | Drops rows with NaNs in target columns | ✅ Passed |
| `test_cleaning.py` | `test_cleaning_fill_mean` | `clean_dataset` | Imputes exact arithmetic column mean | ✅ Passed |
| `test_cleaning.py` | `test_cleaning_fill_median` | `clean_dataset` | Imputes exact median (robust to outliers) | ✅ Passed |
| `test_cleaning.py` | `test_cleaning_group_median_does_not_cross_groups` | `clean_dataset` | Group-wise median does not bleed across basins | ✅ Passed |
| `test_cleaning.py` | `test_cleaning_quality_comparison` | `get_quality_comparison` | Computes pre/post row counts, missing %, and summary stats | ✅ Passed |
| `test_database.py` | `test_database_initialization` | `init_db` | Creates 6 relational tables + standard ocean indicators | ✅ Passed |
| `test_database.py` | `test_database_foreign_key_enforcement` | SQLite schema | Rejects invalid foreign keys with `sqlite3.IntegrityError` | ✅ Passed |
| `test_database.py` | `test_database_not_null_constraints` | SQLite schema | Rejects NULL entries on required fields | ✅ Passed |
| `test_database.py` | `test_register_source_and_run_logging` | `register_source`, `log_analysis_run` | Logs analysis run audit trail with JSON serialization | ✅ Passed |
| `test_ingestion.py` | `test_load_csv_file_not_found` | `load_csv` | Raises `FileNotFoundError` with clear message | ✅ Passed |
| `test_ingestion.py` | `test_load_csv_empty_file` | `load_csv` | Raises `ValueError` for 0-byte file | ✅ Passed |
| `test_ingestion.py` | `test_load_csv_from_buffer` | `load_csv` | Successfully reads from `StringIO` / `BytesIO` buffer | ✅ Passed |
| `test_ingestion.py` | `test_build_metadata` | `build_metadata` | Preserves units, rows, columns, and reference period | ✅ Passed |
| `test_ingestion.py` | `test_load_sample` | `load_sample` | Generates and loads 3000+ row synthetic benchmark | ✅ Passed |

---

## 3. Milestone 2 Planned Tests
- `tests/test_statistics.py`: Unit tests for Pearson/Spearman correlation matrices and grouped summaries.
- `tests/test_outliers.py`: IQR and Z-score threshold detection and zero-std handling.
- `tests/test_pca.py`: PCA standardization, explained variance ratio sum to ~1.0, and component loadings.
- `tests/test_workflow.py`: End-to-end integration test (ingest -> validate -> clean -> stats -> PCA -> DB log -> export).
