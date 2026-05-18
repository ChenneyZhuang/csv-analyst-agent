"""
Statistical analysis tools for CSV data.

Computes descriptive statistics, detects outliers, and builds column profiles
using pandas + numpy + scipy.
"""

from __future__ import annotations

import math
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from scipy import stats as sp_stats

from csv_analyst.models.schemas import (
    Anomaly,
    AnomalyReport,
    CategoricalColumnStats,
    ColumnInfo,
    DatasetProfile,
    NumericColumnStats,
    StatsSummary,
)

# ---------------------------------------------------------------------------
# Column type inference
# ---------------------------------------------------------------------------

NUMERIC_DTYPES = {"int64", "int32", "float64", "float32"}
CATEGORICAL_THRESHOLD = 0.05  # If unique ratio < 5 % treat as categorical


def _infer_column_type(series: pd.Series) -> str:
    """Infer the high-level semantic type of a column."""
    dtype_str = str(series.dtype)

    if dtype_str in NUMERIC_DTYPES:
        return "numeric"

    if pd.api.types.is_bool_dtype(series):
        return "boolean"

    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"

    # Heuristic: low-cardinality string/object → categorical
    unique_ratio = series.nunique(dropna=True) / max(len(series), 1)
    if unique_ratio < CATEGORICAL_THRESHOLD:
        return "categorical"

    # Try to parse as datetime
    if dtype_str == "object":
        try:
            pd.to_datetime(series.dropna(), errors="raise")
            return "datetime"
        except (ValueError, TypeError):
            pass

    return "text"


def _safe_sample(values: pd.Series, n: int = 5) -> list[str]:
    """Return up to *n* sample values as strings, skipping NaN."""
    samples = values.dropna().unique()[:n]
    return [str(v) for v in samples]


# ---------------------------------------------------------------------------
# Dataset profiling
# ---------------------------------------------------------------------------


def profile_dataset(file_path: str | Path) -> DatasetProfile:
    """Read a CSV file and build a :class:`DatasetProfile`.

    Parameters
    ----------
    file_path:
        Path to the CSV file.

    Returns
    -------
    DatasetProfile
    """
    file_path = Path(file_path)
    file_size = file_path.stat().st_size

    df = pd.read_csv(file_path)

    columns: list[ColumnInfo] = []
    for col_name in df.columns:
        series = df[col_name]
        null_count = int(series.isna().sum())
        columns.append(
            ColumnInfo(
                name=col_name,
                dtype=str(series.dtype),
                inferred_type=_infer_column_type(series),
                null_count=null_count,
                null_pct=round(null_count / max(len(series), 1) * 100, 2),
                unique_count=int(series.nunique(dropna=True)),
                sample_values=_safe_sample(series),
            )
        )

    return DatasetProfile(
        file_path=str(file_path.resolve()),
        file_size_bytes=file_size,
        row_count=len(df),
        column_count=len(df.columns),
        columns=columns,
    )


# ---------------------------------------------------------------------------
# Statistical summary
# ---------------------------------------------------------------------------


def compute_numeric_stats(series: pd.Series, col_name: str) -> NumericColumnStats:
    """Compute descriptive statistics for a numeric column."""
    clean = series.dropna()
    count = len(clean)

    if count == 0:
        return NumericColumnStats(
            column=col_name,
            count=0,
            mean=0.0,
            median=0.0,
            std=0.0,
            min=0.0,
            max=0.0,
            **{"25%": 0.0, "75%": 0.0},
            skewness=None,
            kurtosis=None,
        )

    mean_val = float(clean.mean())
    median_val = float(clean.median())
    std_val = float(clean.std(ddof=1)) if count > 1 else 0.0
    min_val = float(clean.min())
    max_val = float(clean.max())
    q25 = float(clean.quantile(0.25))
    q75 = float(clean.quantile(0.75))

    skew: Optional[float] = None
    kurt: Optional[float] = None
    if count >= 3 and std_val > 0:
        skew = float(sp_stats.skew(clean, bias=False))
        kurt = float(sp_stats.kurtosis(clean, bias=False))

    return NumericColumnStats(
        column=col_name,
        count=count,
        mean=mean_val,
        median=median_val,
        std=std_val,
        min=min_val,
        max=max_val,
        **{"25%": q25, "75%": q75},
        skewness=skew,
        kurtosis=kurt,
    )


def compute_categorical_stats(series: pd.Series, col_name: str) -> CategoricalColumnStats:
    """Compute descriptive statistics for a categorical column."""
    clean = series.dropna()
    unique = clean.nunique()
    vc = clean.value_counts()

    top_value: Optional[str] = None
    top_freq: Optional[int] = None
    top_pct: Optional[float] = None

    if len(vc) > 0:
        top_value = str(vc.index[0])
        top_freq = int(vc.iloc[0])
        top_pct = round(top_freq / max(len(clean), 1) * 100, 2)

    # Limit value counts to top 20
    vc_dict = {str(k): int(v) for k, v in vc.head(20).items()}

    return CategoricalColumnStats(
        column=col_name,
        unique_count=unique,
        top_value=top_value,
        top_freq=top_freq,
        top_pct=top_pct,
        value_counts=vc_dict,
    )


def compute_stats_summary(file_path: str | Path) -> StatsSummary:
    """Compute the full statistical summary for a CSV file.

    Parameters
    ----------
    file_path:
        Path to the CSV file.

    Returns
    -------
    StatsSummary
    """
    df = pd.read_csv(file_path)
    numeric_stats: list[NumericColumnStats] = []
    categorical_stats: list[CategoricalColumnStats] = []

    for col_name in df.columns:
        series = df[col_name]
        inferred = _infer_column_type(series)

        if inferred == "numeric":
            numeric_stats.append(compute_numeric_stats(series, col_name))
        elif inferred in ("categorical", "boolean", "text"):
            categorical_stats.append(compute_categorical_stats(series, col_name))

    return StatsSummary(
        numeric_stats=numeric_stats,
        categorical_stats=categorical_stats,
    )


# ---------------------------------------------------------------------------
# Anomaly / outlier detection
# ---------------------------------------------------------------------------


def detect_anomalies(file_path: str | Path, zscore_threshold: float = 3.0) -> AnomalyReport:
    """Detect anomalies and outliers in a CSV file.

    Uses IQR for numeric columns and null-count checks for all columns.

    Parameters
    ----------
    file_path:
        Path to the CSV file.
    zscore_threshold:
        Z-score threshold for outlier detection (default 3.0, i.e. 3σ).

    Returns
    -------
    AnomalyReport
    """
    df = pd.read_csv(file_path)
    anomalies: list[Anomaly] = []

    for col_name in df.columns:
        series = df[col_name]
        inferred = _infer_column_type(series)

        # ── Missing-value check ──────────────────────────────────────────
        null_mask = series.isna()
        null_count = null_mask.sum()
        if null_count > 0:
            null_pct = null_count / len(series) * 100
            severity = "critical" if null_pct > 20 else "warning" if null_pct > 5 else "info"
            anomalies.append(
                Anomaly(
                    column=col_name,
                    value=f"{null_count} missing values ({null_pct:.1f}%)",
                    reason=f"Column has {null_count} missing values ({null_pct:.1f}% of rows).",
                    severity=severity,
                )
            )

        # ── Numeric outlier detection (IQR method) ───────────────────────
        if inferred == "numeric":
            clean = series.dropna()
            if len(clean) < 4:
                continue

            q1 = clean.quantile(0.25)
            q3 = clean.quantile(0.75)
            iqr = q3 - q1
            if iqr == 0:
                continue

            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            outlier_mask = (clean < lower) | (clean > upper)
            outlier_indices = clean[outlier_mask].index

            # Also check Z-score
            mean_val = clean.mean()
            std_val = clean.std(ddof=1)
            if std_val > 0:
                z_scores = np.abs((clean - mean_val) / std_val)
                z_outlier_indices = clean[z_scores > zscore_threshold].index
                outlier_indices = outlier_indices.union(z_outlier_indices)

            for idx in outlier_indices[:20]:  # cap at 20 per column
                val = series.iloc[idx]
                anomalies.append(
                    Anomaly(
                        column=col_name,
                        row_index=int(idx),
                        value=str(val),
                        reason=f"Outlier detected — value {val} falls outside IQR bounds [{lower:.2f}, {upper:.2f}].",
                        severity="warning",
                    )
                )

        # ── Duplicate check on the whole dataset (once) ──────────────────
        # Handled once outside the column loop below

    return AnomalyReport(anomalies=anomalies)


# ---------------------------------------------------------------------------
# Correlation matrix helper (not a model — plain dict for LLM consumption)
# ---------------------------------------------------------------------------


def compute_correlations(file_path: str | Path, method: str = "pearson") -> dict[str, dict[str, float]]:
    """Compute a correlation matrix for numeric columns.

    Returns a nested dict suitable for JSON serialisation / LLM prompts.
    """
    df = pd.read_csv(file_path)
    numeric_cols = [
        c for c in df.columns if _infer_column_type(df[c]) == "numeric"
    ]
    if len(numeric_cols) < 2:
        return {}

    corr = df[numeric_cols].corr(method=method)
    result: dict[str, dict[str, float]] = {}
    for col_a in corr.columns:
        result[col_a] = {}
        for col_b in corr.columns:
            val = corr.loc[col_a, col_b]
            if not math.isnan(val):
                result[col_a][col_b] = round(float(val), 4)
    return result
