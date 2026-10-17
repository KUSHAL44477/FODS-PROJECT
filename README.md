# 🌊 OceanWatch

**Autonomous Marine Observation Analytics & Data Quality Assurance Platform**  
*A Fundamentals of Data Science (FODS) Academic Project*

---

## 📌 Overview

**OceanWatch** is an interactive web application built with Streamlit and Python for analyzing marine environmental observations, specifically sea water temperature, practical salinity, and dissolved oxygen across geographic basins and depth profiles.

This repository contains the **Initial Foundation (Section 0)** release, providing a validated, non-destructive data cleaning and ingestion pipeline, physical oceanographic integrity audits, and a normalized SQLite audit database.

---

## 🚀 Key Features & Implementation Status

### ✅ Implemented in this Release (Initial Foundation)
- **Data Ingestion Engine (`src/ingestion.py`)**: Robust CSV loader with multi-encoding fallback, empty-file safety, structured metadata generation, and provenance tracking.
- **Oceanographic Physical Validation (`src/validation.py`)**: Structured data quality audit inspecting coordinates ($[-90, 90]$, $[-180, 180]$), liquid seawater freezing/boiling bounds ($-2.0^\circ\text{C}$ to $40.0^\circ\text{C}$), salinity ($0$ to $45$ PSU), non-negative depth, missingness percentages, and duplicate records. **Rule: Never silently drops rows.**
- **Non-Destructive Cleaning Studio (`src/cleaning.py`)**:
  - Immutability: Always works on explicit copies, leaving raw data intact.
  - Deduplication: Exact duplicate row purging with logged row count.
  - Missingness strategies: `leave_as_is` (DEFAULT), `drop_rows`, `fill_mean`, `fill_median`, `fill_group_median` (by ocean basin), and `interpolate_linear` (isolated within geographic basin).
  - Before/after quality comparisons: Real-time calculation of row counts, missing percentages, and per-variable mean/std/median shifts.
- **Relational Database (`src/database.py`)**: SQLite star schema (`dim_source`, `dim_time`, `dim_location`, `dim_indicator`, `fact_measurement`, `analysis_run`) with `PRAGMA foreign_keys = ON;` and audit run logging.
- **Synthetic Benchmark Generator (`scripts/make_sample_data.py`)**: Realistic 3,000+ row oceanographic dataset modeling thermocline decay, oxygen minimum zones (OMZ), and geographic variation, with injected anomalies for validation testing.
- **Streamlit Web Interface**:
  - `app.py`: Dark navy ocean theme (`.streamlit/config.toml`), instant benchmark dataset loader, live KPI snapshot, and data preview.
  - `pages/2_Data_Workspace.py`: End-to-end workspace for custom CSV upload, validation audit inspection, interactive cleaning studio, before/after comparison tables, and cleaned CSV export.
- **Comprehensive Test Suite (`tests/`)**: 22 passing automated unit tests across validation, cleaning, ingestion, and database integrity.

---

## 🔮 Roadmap (Planned for Milestone 2 - TODO)

The following analytical modules and interface pages are scheduled for future milestones as defined in Section 0:

- [ ] **Descriptive & Grouped Statistics (`src/statistics.py`)**: Pearson and Spearman correlation matrices with paired observation count $N$, depth and region grouped summaries.
- [ ] **Outlier Detection (`src/outliers.py`)**: IQR (1.5x) and configurable Z-score anomaly detection without automatic row deletion.
- [ ] **Principal Component Analysis (`src/pca.py`)**: Standardized PCA with scree plots, cumulative variance charts, and component loadings.
- [ ] **ReportLab PDF Generator (`src/reporting.py`)**: Automated PDF report generation with metadata, cleaning logs, and methodology caveats.
- [ ] **Dashboard (`pages/1_Dashboard.py`)**: Interactive trend charts and multi-indicator filtering.
- [ ] **Exploratory Analysis (`pages/3_Exploratory_Analysis.py`)**: Histograms, box plots, and correlation heatmaps with live $N$.
- [ ] **Outlier & PCA Studio (`pages/4_Outlier_PCA.py`)**: Visual outlier inspection and interactive PCA biplots.
- [ ] **Reports & Provenance (`pages/5_Reports.py`)**: Audit run history viewer and multi-artifact export.
- [ ] **Experimental Ocean Stability Index**: Optional heuristic stability calculation (clearly tagged as experimental).

---

## 🛠️ Tech Stack

- **Language**: Python 3.10+
- **Frontend / UI**: Streamlit (with custom dark ocean theme)
- **Data Processing**: Pandas, NumPy, SciPy
- **Machine Learning**: scikit-learn
- **Visualization**: Plotly
- **Database**: SQLite3 (Standard Library with foreign key constraints)
- **Testing**: pytest
- **Reporting**: ReportLab

---

## 📦 Installation & Setup

### 1. Clone the repository
```bash
git clone https://github.com/KUSHAL44477/FODS-Project.git
cd FODS-Project
```

### 2. Create and activate a virtual environment
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

---

## 🖥️ Running the Application

Launch the Streamlit web application:
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

1. Click **"📥 Load Sample Ocean Dataset"** on the home page to explore the benchmark data.
2. Navigate to **2 Data Workspace** in the left sidebar to inspect validation checks, test different cleaning strategies, and download the cleaned CSV.

---

## 🧪 Running the Tests

Execute the automated test suite with verbose reporting:
```bash
pytest -v
```

All 22 unit tests verify data integrity, mathematical correctness, edge cases, and relational constraints.

---

## 📸 Screenshots

*(Screenshots will be captured and added following deployment of the analytical visualization modules)*

| Home Page & Quick Snapshot | Data Workspace & Validation Audit |
|:---:|:---:|
| `[Home Page Screenshot Placeholder]` | `[Data Workspace Screenshot Placeholder]` |

---

## ⚠️ Known Limitations & Scientific Caveats

1. **Synthetic Data**: The default sample dataset (`data/raw/sample_ocean.csv`) is synthetically generated by `scripts/make_sample_data.py` for educational and algorithmic testing. It is explicitly labeled as synthetic throughout the UI.
2. **Climatological Averages vs Real-Time Data**: Climatological averages represent smoothed multi-year intervals and must not be interpreted as daily maritime observations.
3. **Correlation is Not Causation**: Statistical dependencies (e.g. between temperature and dissolved oxygen) reflect physical solubility and biochemical consumption, but require domain modeling to prove causation.
4. **Non-Destructive Principle**: In accordance with scientific data curation standards, validation never deletes or alters raw data records.

---

## 📄 Documentation Links
- [Data Dictionary](docs/DATA_DICTIONARY.md)
- [Methodology & Formulas](docs/METHODOLOGY.md)
- [Test Plan & Verification](docs/TEST_PLAN.md)
- [Engineering Decisions Log](docs/DECISIONS.md)
