"""
scripts/make_sample_data.py
Generates a realistic synthetic oceanographic dataset for OceanWatch (FODS Project).
LABEL: SYNTHETIC SAMPLE DATA - FOR EDUCATIONAL / FODS TESTING ONLY.
"""

from pathlib import Path
import numpy as np
import pandas as pd


def generate_sample_dataset(
    output_path: str = "data/raw/sample_ocean.csv",
    n_rows: int = 3000,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate realistic synthetic ocean measurement data and save to CSV.

    Columns:
    - latitude: -90.0 to 90.0 degrees
    - longitude: -180.0 to 180.0 degrees
    - depth_m: 0 to 4500 meters
    - region: Ocean basin
    - period: Climatological reference period label (e.g., '2015-2019', '2020-2024')
    - temperature_c: Sea water temperature in Celsius (-2.0 to 35.0 C realistic)
    - salinity_psu: Practical Salinity Unit (30.0 to 40.0 PSU realistic)
    - dissolved_oxygen_ml_l: Dissolved oxygen in ml/L (0.0 to 10.0 ml/l realistic)
    """
    rng = np.random.default_rng(seed)

    # 1. Spatial distribution & regions
    regions = [
        "North Atlantic",
        "South Atlantic",
        "North Pacific",
        "South Pacific",
        "Indian Ocean",
        "Southern Ocean",
        "Arctic Ocean",
        "Mediterranean Sea",
    ]
    region_weights = [0.18, 0.14, 0.22, 0.16, 0.15, 0.08, 0.04, 0.03]
    selected_regions = rng.choice(regions, size=n_rows, p=region_weights)

    latitudes = []
    longitudes = []
    for reg in selected_regions:
        if reg == "North Atlantic":
            lat = rng.uniform(10.0, 65.0)
            lon = rng.uniform(-75.0, -10.0)
        elif reg == "South Atlantic":
            lat = rng.uniform(-55.0, 0.0)
            lon = rng.uniform(-50.0, 15.0)
        elif reg == "North Pacific":
            lat = rng.uniform(10.0, 60.0)
            lon = rng.choice([rng.uniform(130.0, 180.0), rng.uniform(-180.0, -120.0)])
        elif reg == "South Pacific":
            lat = rng.uniform(-55.0, 0.0)
            lon = rng.choice([rng.uniform(150.0, 180.0), rng.uniform(-180.0, -75.0)])
        elif reg == "Indian Ocean":
            lat = rng.uniform(-45.0, 25.0)
            lon = rng.uniform(40.0, 105.0)
        elif reg == "Southern Ocean":
            lat = rng.uniform(-75.0, -55.0)
            lon = rng.uniform(-180.0, 180.0)
        elif reg == "Arctic Ocean":
            lat = rng.uniform(70.0, 88.0)
            lon = rng.uniform(-180.0, 180.0)
        else:  # Mediterranean Sea
            lat = rng.uniform(30.0, 44.0)
            lon = rng.uniform(-5.0, 36.0)
        latitudes.append(round(lat, 4))
        longitudes.append(round(lon, 4))

    latitudes = np.array(latitudes)
    longitudes = np.array(longitudes)

    # 2. Depth distribution (standard oceanographic profiles: surface heavy, tapering to abyss)
    depth_discrete_steps = np.array([0, 10, 25, 50, 75, 100, 200, 300, 500, 750, 1000, 1500, 2000, 3000, 4000])
    depth_probs = np.array([0.15, 0.12, 0.10, 0.09, 0.08, 0.08, 0.08, 0.07, 0.06, 0.05, 0.04, 0.03, 0.02, 0.02, 0.01])
    depth_probs = depth_probs / depth_probs.sum()
    depth_m = rng.choice(depth_discrete_steps, size=n_rows, p=depth_probs)

    # 3. Periods (climatological decades / 5-year binned intervals, never synthetic daily dates)
    periods = ["2010-2014", "2015-2019", "2020-2024"]
    selected_periods = rng.choice(periods, size=n_rows, p=[0.25, 0.40, 0.35])

    # 4. Realistic ocean physics relationships
    # Surface temperature decreases with latitude (equator ~28C, poles ~-1.5C)
    abs_lat = np.abs(latitudes)
    surface_temp = 28.5 - (abs_lat / 90.0) ** 1.3 * 30.0
    # Thermocline decay with depth: temperature drops towards 1.0 - 3.0 C at abyss
    temp_decay = np.exp(-depth_m / 450.0)
    deep_water_temp = 1.8 + rng.normal(0, 0.4, size=n_rows)
    temperature_c = surface_temp * temp_decay + deep_water_temp * (1.0 - temp_decay)
    temperature_c += rng.normal(0, 0.6, size=n_rows)
    # Physical clamp for baseline
    temperature_c = np.clip(temperature_c, -1.8, 32.5)

    # Salinity: Mediterranean is salty (~38.5), subtropical gyres (~36-37), subpolar/polar lower (~31-33)
    base_salinity = 34.8 - 1.5 * (abs_lat / 90.0) + rng.normal(0, 0.4, size=n_rows)
    med_mask = selected_regions == "Mediterranean Sea"
    base_salinity[med_mask] += 3.2
    # Slight depth stabilization (deep ocean salinity is ~34.6 - 34.9)
    salinity_psu = (
        base_salinity * temp_decay + (34.7 + rng.normal(0, 0.15, size=n_rows)) * (1.0 - temp_decay)
    )
    salinity_psu = np.clip(salinity_psu, 30.2, 39.8)

    # Dissolved Oxygen:
    # Cold surface waters hold more oxygen (solubility ~ 6 to 9 ml/L; warm tropics ~ 4 to 5 ml/L)
    solubility = 8.5 - 0.14 * temperature_c
    # Oxygen minimum zone (OMZ) at 200 - 900m due to organic decomposition
    omz_deficit = 3.5 * np.exp(-((depth_m - 500) ** 2) / (2 * (300**2)))
    # Deep water re-ventilation from polar sinking (thermohaline circulation)
    deep_ventilation = 1.5 * (1.0 - np.exp(-depth_m / 1500.0))
    dissolved_oxygen_ml_l = solubility - omz_deficit + deep_ventilation + rng.normal(0, 0.35, size=n_rows)
    dissolved_oxygen_ml_l = np.clip(dissolved_oxygen_ml_l, 0.4, 9.8)

    # Round to realistic precision
    df = pd.DataFrame({
        "latitude": np.round(latitudes, 4),
        "longitude": np.round(longitudes, 4),
        "depth_m": depth_m.astype(int),
        "region": selected_regions,
        "period": selected_periods,
        "temperature_c": np.round(temperature_c, 2),
        "salinity_psu": np.round(salinity_psu, 2),
        "dissolved_oxygen_ml_l": np.round(dissolved_oxygen_ml_l, 2),
    })

    # 5. Inject about 5% missing values across indicators
    n_missing = int(n_rows * 0.05)
    for col in ["temperature_c", "salinity_psu", "dissolved_oxygen_ml_l"]:
        nan_indices = rng.choice(n_rows, size=rng.integers(int(n_missing * 0.7), int(n_missing * 1.3)), replace=False)
        df.loc[nan_indices, col] = np.nan

    # 6. Inject a handful of outliers (sensor faults / anomalous spikes)
    outlier_indices = rng.choice(n_rows, size=15, replace=False)
    # High temp anomaly (e.g. 44.5 C - impossible surface ocean temp)
    df.loc[outlier_indices[0:3], "temperature_c"] = [43.8, 48.2, -4.5]
    # Salinity anomaly (e.g. 48.0 PSU or sensor short-circuit 12.0 PSU)
    df.loc[outlier_indices[3:6], "salinity_psu"] = [49.5, 14.2, 52.0]
    # Oxygen anomaly (e.g. 14.8 ml/l or -1.5)
    df.loc[outlier_indices[6:9], "dissolved_oxygen_ml_l"] = [13.9, -0.8, 15.5]
    # Location / depth anomalies (e.g. negative depth or latitude out of bounds)
    df.loc[outlier_indices[9], "depth_m"] = -50
    df.loc[outlier_indices[10], "latitude"] = 105.4
    df.loc[outlier_indices[11], "longitude"] = 210.0

    # 7. Add duplicate rows (exact duplicates to test deduplication)
    n_dupes = 20
    dupe_rows = df.iloc[rng.choice(n_rows, size=n_dupes, replace=False)].copy()
    df = pd.concat([df, dupe_rows], ignore_index=True)

    # Save to disk
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_file, index=False)
    print(f"Generated {len(df)} rows of synthetic ocean data -> {output_path}")
    return df


if __name__ == "__main__":
    generate_sample_dataset()
