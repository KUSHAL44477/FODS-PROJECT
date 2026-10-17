# OceanWatch: Architectural & Engineering Decisions Log (docs/DECISIONS.md)

This document records all architectural choices, assumptions, and engineering decisions made autonomously during the initial foundation implementation (Section 0) of the OceanWatch FODS project.

---

### DEC-001: Project Skeleton & Workspace Directory Layout
- **Context**: The workspace root was provided as `c:\Users\maury\Downloads\UE5`. The prompt specified `oceanwatch/` structure containing `app.py`, `pages/`, `src/`, etc.
- **Decision**: Implemented the Streamlit application root directly at the workspace root directory. This allows `streamlit run app.py` and `pytest` to be invoked directly from the project root without nested folder ambiguity.
- **Consequence**: Clean GitHub repository structure where `.gitignore`, `requirements.txt`, and `README.md` reside at the top level of `FODS-Project`.

---

### DEC-002: Synthetic Data Generation Physics Model
- **Context**: To prevent blocking on external network downloads (NOAA WOA23), a realistic synthetic dataset generator was required (`scripts/make_sample_data.py`).
- **Decision**: Implemented simplified ocean physics rather than uniform random numbers:
  1. **Temperature**: Modeled with latitude-dependent insolation at the surface ($T_{surface} \approx 28.5 - (\text{lat}/90)^{1.3} \times 30$) and exponential thermocline decay towards deep ocean water ($1.8^\circ\text{C}$).
  2. **Salinity**: Modeled with Mediterranean elevation (~38 PSU) and subtropical evaporation gyres vs polar freshening.
  3. **Dissolved Oxygen**: Modeled with temperature solubility dependency and an Oxygen Minimum Zone (OMZ) Gaussian depression around 500m depth, with deep water ventilation.
  4. **Anomalies**: Fixed random seed (`42`), injected ~5% missing values, 20 duplicate rows, and 15 sensor spikes (e.g., negative depths, $48^\circ\text{C}$ temperatures, $14.2$ PSU salinity).
- **Consequence**: Provides a realistic test bench for validation and cleaning without fabricating real-world scientific measurements.

---

### DEC-003: Validation Philosophy — "Never Silently Drop Rows"
- **Context**: Section 5.2 states: "Never silently drop rows."
- **Decision**: `validate_dataset` in `src/validation.py` is strictly non-destructive. It returns structured reports (counts, percentages, violating row indices, impossible values, data types) without modifying, re-indexing, or deleting any rows.
- **Consequence**: The user or downstream algorithms always have full visibility into data anomalies before deciding on cleaning actions.

---

### DEC-004: Data Cleaning Architecture & Default Strategy
- **Context**: Cleaning operations can inadvertently distort variance or introduce bias into statistical analyses.
- **Decision**:
  1. Immutability: Cleaning operates on an isolated `df.copy(deep=True)`. The raw input dataframe is never modified.
  2. Default missing value strategy: `"leave_as_is"`. Users must explicitly opt into row dropping or imputation.
  3. Isolated group-wise interpolation: When interpolating along depth or time, data is grouped by basin (`region`) so that interpolation never bridges disjoint ocean basins.
  4. Detailed audit trail: Every cleaning step returns a structured record with rows affected and exact parameters.

---

### DEC-005: Relational Database & Foreign Key Enforcement
- **Context**: SQLite defaults to disabling foreign key constraint checks unless explicitly requested per connection.
- **Decision**:
  1. `get_connection()` in `src/database.py` executes `PRAGMA foreign_keys = ON;` upon opening every connection.
  2. Tables adhere to the Section 5.7 star schema: `dim_source`, `dim_time`, `dim_location`, `dim_indicator`, `fact_measurement`, and `analysis_run`.
  3. `analysis_run` stores JSON-serialized summaries and cleaning configs for complete provenance auditing.

---

### DEC-006: Streamlit UI Design & Multi-Page Navigation
- **Context**: Streamlit multi-page routing automatically scans the `pages/` directory. Future modules (`1_Dashboard`, `3_Exploratory_Analysis`, `4_Outlier_PCA`, `5_Reports`) are scheduled for future milestones.
- **Decision**:
  1. Home page (`app.py`) provides quick ingestion, metadata inspection, and live validation snapshot.
  2. `pages/2_Data_Workspace.py` contains the complete interactive upload, validation audit, cleaning studio, and export tools.
  3. Planned pages in `pages/` are provided with clean Informational notice banners and navigation hints, ensuring no runtime crashes occur if a user clicks them.
- **Consequence**: The application provides an engaging user experience with zero broken links.

---

### DEC-007: GitHub Repository Creation & Fallback Handling
- **Context**: The GitHub CLI in the environment may be logged into an existing session (e.g. `PARADOX-457`), while the target repository is specified as `KUSHAL44477/FODS-Project`.
- **Decision**: Attempt automated creation via `gh repo create KUSHAL44477/FODS-Project --public --source=. --remote=origin --push`. If cross-account permission prevents direct creation, set the git remote to `https://github.com/KUSHAL44477/FODS-Project.git`, create clean atomic commits, and report the fallback commands.
