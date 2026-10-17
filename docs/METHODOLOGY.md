# OceanWatch Methodology & Algorithmic Specifications

This document outlines the scientific and mathematical methodologies implemented in OceanWatch, as well as the planned formulations for subsequent milestones.

---

## 1. Data Cleaning & Preprocessing

### 1.1 Deduplication
- **Method**: Exact record comparison across all columns.
- **Rule**: Retains the first observed instance ($i_0$) and purges subsequent identical records.
- **Limitation**: Sensor data with timestamps may have duplicate coordinates that are legitimately distinct times; deduplication must only apply when all fields (including time/depth) are identical.

### 1.2 Missing Value Imputation
Oceanographic datasets frequently suffer from sensor dropouts, transmission corruption, and depth coverage gaps. OceanWatch provides distinct strategies:

1. **Leave As-Is (Default)**:
   - Does not alter missing cells. Preserves true sample variance $\sigma^2$ and sample size $N$ for downstream unbiased estimation.

2. **Column-wise Mean Imputation**:
   $$\bar{x} = \frac{1}{N_{obs}} \sum_{i=1}^{N_{obs}} x_i$$
   - **Limitation**: Artificially depresses sample variance and inflates correlation coefficients towards zero.

3. **Column-wise Median Imputation**:
   $$\tilde{x} = \text{Median}(x_{obs})$$
   - **Advantage**: Robust against extreme sensor spikes and non-Gaussian skewness.

4. **Group-wise Median (by Basin/Region)**:
   $$\tilde{x}_g = \text{Median}(\{x_i \mid \text{region}_i = g\})$$
   - Takes regional oceanographic differences into account (e.g. Mediterranean high salinity vs Arctic freshening).

5. **Isolated Linear Interpolation**:
   $$x(d) = x(d_0) + \frac{x(d_1) - x(d_0)}{d_1 - d_0} (d - d_0)$$
   - Strictly constrained within the same geographic basin ($g$). Never interpolates across unrelated stations.

---

## 2. Statistical Anomaly & Outlier Detection (Roadmap M2 Formulation)

### 2.1 Interquartile Range (IQR) Method
- Let $Q_1$ be the 25th percentile and $Q_3$ be the 75th percentile of variable $X$.
- $\text{IQR} = Q_3 - Q_1$
- A value $x_i$ is flagged as an outlier if:
  $$x_i < Q_1 - 1.5 \times \text{IQR} \quad \text{or} \quad x_i > Q_3 + 1.5 \times \text{IQR}$$
- **Characteristics**: Non-parametric; does not assume a normal distribution.

### 2.2 Z-Score Anomaly Detection
- For normally distributed indicators with mean $\mu$ and standard deviation $\sigma > 0$:
  $$z_i = \frac{x_i - \mu}{\sigma}$$
- An observation is flagged if $|z_i| > \theta$ (default $\theta = 3.0$).
- **Handling**: If $\sigma = 0$ or NaN, the variable is skipped to avoid division-by-zero errors.

---

## 3. Dimensionality Reduction (PCA) (Roadmap M2 Formulation)

### 3.1 Standardization
Ocean indicators have differing units ($^\circ\text{C}$, $\text{PSU}$, $\text{ml/L}$). Features must be standardized to zero mean and unit variance:
$$z_{ij} = \frac{x_{ij} - \bar{x}_j}{s_j}$$

### 3.2 Covariance & Eigendecomposition
Compute the sample covariance matrix $\mathbf{C} = \frac{1}{n-1} \mathbf{Z}^T \mathbf{Z}$, and solve the eigenvalue problem:
$$\mathbf{C} \mathbf{v}_k = \lambda_k \mathbf{v}_k$$
where $\lambda_k$ represents the variance explained by the $k$-th principal component.

### 3.3 Explained Variance Ratio
$$\text{EVR}_k = \frac{\lambda_k}{\sum_{j=1}^p \lambda_j}$$
- **Rule**: Cumulative explained variance is computed dynamically from eigenvalues; never hard-coded.

---

## 4. Scientific Caveats & Limitations
1. **Correlation vs Causation**: A statistical correlation between temperature and dissolved oxygen does not alone prove biological consumption without biochemical rate modeling.
2. **Climatology vs In-Situ Real-time**: Climatological averages represent smoothed multi-year pentads. They do not represent daily weather or transient marine heatwaves.
3. **Synthetic Dataset Notice**: The sample dataset is synthetic and calibrated for educational FODS demonstration only.
