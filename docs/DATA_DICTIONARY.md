# OceanWatch Data Dictionary

## 1. Primary Oceanographic Variables (`data/raw/sample_ocean.csv`)

| Column Name | Data Type | Standard Unit | Valid Range | Physical Description | Provenance / Notes |
|:---|:---|:---|:---|:---|:---|
| `latitude` | `float64` | Degrees North (`°N`) | `[-90.0, 90.0]` | Geographic latitude of sampling station. Negative represents Southern Hemisphere. | NOAA WOA convention / Synthetic spatial distribution |
| `longitude` | `float64` | Degrees East (`°E`) | `[-180.0, 180.0]` | Geographic longitude of sampling station. Negative represents Western Hemisphere. | NOAA WOA convention / Synthetic spatial distribution |
| `depth_m` | `int64` | Meters (`m`) | `[0, 11500]` | Depth below ocean surface. Surface is 0m. Must never be negative. | Standard oceanographic depth levels |
| `region` | `object` / `str` | Text label | Categorical (8 ocean basins) | Ocean basin name: `North Atlantic`, `South Atlantic`, `North Pacific`, `South Pacific`, `Indian Ocean`, `Southern Ocean`, `Arctic Ocean`, `Mediterranean Sea`. | Regional grouping key |
| `period` | `object` / `str` | Text label | 5-year binned climatologies | Reference climatological period: `2010-2014`, `2015-2019`, `2020-2024`. **Never synthetic daily timestamps.** | Climatological decadal / pentad binning |
| `temperature_c` | `float64` | Celsius (`°C`) | `[-2.0, 40.0]` | In-situ sea water temperature. Seawater with salinity ~35 PSU freezes at approximately -1.9°C. | Thermocline and latitude-dependent profile |
| `salinity_psu` | `float64` | Practical Salinity Unit (`PSU`) | `[0.0, 45.0]` | Practical Salinity Unit (dimensionless conductivity ratio). Typical open ocean: 32–37 PSU. Mediterranean up to ~39 PSU. | Subtropical evaporation vs polar precipitation balance |
| `dissolved_oxygen_ml_l` | `float64` | Milliliters per Liter (`ml/L`) | `[0.0, 15.0]` | Volume of dissolved oxygen gas per liter of seawater. Inversely related to temperature in surface waters; oxygen minimum zone at 200–1000m. | Solubility and biochemical decomposition balance |

---

## 2. Relational Database Schema (`oceanwatch.db`)

The SQLite database uses a star-schema design with strict foreign key constraints enabled via `PRAGMA foreign_keys = ON;`.

### 2.1 Dimension: `dim_source`
Tracks dataset provenance, attribution, and ingest timestamps.

| Field | Type | Constraints | Description |
|:---|:---|:---|:---|
| `source_id` | `INTEGER` | `PRIMARY KEY AUTOINCREMENT` | Unique identifier for dataset source |
| `source_name` | `TEXT` | `NOT NULL` | Short identifier (e.g. NOAA WOA23, User Upload, Synthetic Benchmark) |
| `dataset_title` | `TEXT` | `NOT NULL` | Formal human-readable title |
| `source_url` | `TEXT` | `NULLABLE` | Source download or documentation URL |
| `access_date` | `TEXT` | `NOT NULL` | ISO 8601 UTC timestamp of ingest |
| `citation` | `TEXT` | `NULLABLE` | Formal academic reference / citation |

### 2.2 Dimension: `dim_time`
Tracks temporal reference periods without fabricating daily timestamps.

| Field | Type | Constraints | Description |
|:---|:---|:---|:---|
| `time_id` | `INTEGER` | `PRIMARY KEY AUTOINCREMENT` | Unique time dimension key |
| `period_label` | `TEXT` | `NOT NULL` | Reference label (e.g., '2015-2019', 'Annual Climatology') |
| `start_date` | `TEXT` | `NULLABLE` | Optional ISO start date |
| `end_date` | `TEXT` | `NULLABLE` | Optional ISO end date |
| `temporal_resolution` | `TEXT` | `NULLABLE` | 'Pentad', 'Decadal', 'Annual', 'Seasonal' |

### 2.3 Dimension: `dim_location`
Tracks spatial coordinates and depth levels.

| Field | Type | Constraints | Description |
|:---|:---|:---|:---|
| `location_id` | `INTEGER` | `PRIMARY KEY AUTOINCREMENT` | Unique location key |
| `latitude` | `REAL` | `NOT NULL` | Sampling latitude `[-90.0, 90.0]` |
| `longitude` | `REAL` | `NOT NULL` | Sampling longitude `[-180.0, 180.0]` |
| `region_name` | `TEXT` | `NULLABLE` | Name of ocean basin or coastal boundary |
| `depth_m` | `REAL` | `NOT NULL` | Sampling depth (non-negative) |

### 2.4 Dimension: `dim_indicator`
Stores definition and standard measurement units for marine variables.

| Field | Type | Constraints | Description |
|:---|:---|:---|:---|
| `indicator_id` | `INTEGER` | `PRIMARY KEY AUTOINCREMENT` | Unique indicator key |
| `indicator_name` | `TEXT` | `NOT NULL UNIQUE` | Canonical code (e.g., `temperature_c`) |
| `standard_unit` | `TEXT` | `NOT NULL` | Measurement unit string (e.g., `°C`) |
| `description` | `TEXT` | `NULLABLE` | Physical and biochemical definition |

### 2.5 Fact: `fact_measurement`
Normalized observations linked to dimensions.

| Field | Type | Constraints | Description |
|:---|:---|:---|:---|
| `measurement_id` | `INTEGER` | `PRIMARY KEY AUTOINCREMENT` | Unique measurement key |
| `source_id` | `INTEGER` | `NOT NULL REFERENCES dim_source(source_id)` | Foreign key to dataset source |
| `time_id` | `INTEGER` | `REFERENCES dim_time(time_id)` | Foreign key to time period |
| `location_id` | `INTEGER` | `NOT NULL REFERENCES dim_location(location_id)` | Foreign key to spatial coordinate |
| `indicator_id` | `INTEGER` | `NOT NULL REFERENCES dim_indicator(indicator_id)` | Foreign key to indicator |
| `value` | `REAL` | `NOT NULL` | Observed numeric value |
| `quality_flag` | `INTEGER` | `DEFAULT 0` | 0=Pass, 1=Suspect/Outlier, 2=Imputed |

### 2.6 Audit Log: `analysis_run`
Tracks reproducible audit trail of cleaning, validation, and analytics runs.

| Field | Type | Constraints | Description |
|:---|:---|:---|:---|
| `run_id` | `INTEGER` | `PRIMARY KEY AUTOINCREMENT` | Unique audit record key |
| `source_id` | `INTEGER` | `REFERENCES dim_source(source_id)` | Optional link to source |
| `run_timestamp` | `TEXT` | `NOT NULL` | ISO 8601 UTC timestamp |
| `cleaning_config`| `TEXT` | `NULLABLE` | JSON serialized dictionary of cleaning parameters |
| `algorithm` | `TEXT` | `NOT NULL` | Name of operation (e.g., 'Data Cleaning (fill_mean)') |
| `summary_json` | `TEXT` | `NOT NULL` | JSON serialized output metrics (row counts, missing %, etc.) |
