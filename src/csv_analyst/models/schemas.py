"""
Pydantic models for structured data throughout the analysis pipeline.

All data flowing between pipeline stages is validated with these schemas.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Column metadata
# ---------------------------------------------------------------------------

class ColumnInfo(BaseModel):
    """Metadata about a single CSV column."""

    name: str = Field(..., description="Column name as it appears in the CSV header.")
    dtype: str = Field(..., description="Pandas dtype string, e.g. 'float64', 'object'.")
    inferred_type: str = Field(
        ...,
        description="High-level type: 'numeric', 'categorical', 'datetime', 'boolean', 'text'.",
    )
    null_count: int = Field(..., description="Number of missing values in this column.")
    null_pct: float = Field(..., description="Percentage of missing values (0-100).")
    unique_count: int = Field(..., description="Number of distinct values.")
    sample_values: list[str] = Field(
        default_factory=list,
        description="A few example values for display.",
    )


class DatasetProfile(BaseModel):
    """High-level profile of the entire CSV dataset."""

    file_path: str = Field(..., description="Path to the CSV file that was analysed.")
    file_size_bytes: int = Field(..., description="File size in bytes.")
    row_count: int = Field(..., description="Total number of data rows (excl. header).")
    column_count: int = Field(..., description="Number of columns.")
    columns: list[ColumnInfo] = Field(
        default_factory=list,
        description="Per-column metadata.",
    )
    profiled_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="ISO-8601 timestamp of when profiling was performed.",
    )


# ---------------------------------------------------------------------------
# Statistical summary
# ---------------------------------------------------------------------------

class NumericColumnStats(BaseModel):
    """Descriptive statistics for a single numeric column."""

    column: str
    count: int
    mean: float
    median: float
    std: float
    min: float
    max: float
    q25: float = Field(..., alias="25%")
    q75: float = Field(..., alias="75%")
    skewness: Optional[float] = None
    kurtosis: Optional[float] = None


class CategoricalColumnStats(BaseModel):
    """Descriptive statistics for a single categorical column."""

    column: str
    unique_count: int
    top_value: Optional[str] = None
    top_freq: Optional[int] = None
    top_pct: Optional[float] = None
    value_counts: dict[str, int] = Field(default_factory=dict)


class StatsSummary(BaseModel):
    """Complete statistical summary of the dataset."""

    numeric_stats: list[NumericColumnStats] = Field(default_factory=list)
    categorical_stats: list[CategoricalColumnStats] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Anomalies & outliers
# ---------------------------------------------------------------------------

class Anomaly(BaseModel):
    """A single detected anomaly or outlier."""

    column: str = Field(..., description="Column where the anomaly was found.")
    row_index: Optional[int] = Field(None, description="Row index (0-based) of the anomaly.")
    value: str = Field(..., description="The anomalous value.")
    reason: str = Field(..., description="Human-readable explanation of why it is anomalous.")
    severity: str = Field(
        "info",
        description="Severity level: 'info', 'warning', or 'critical'.",
    )


class AnomalyReport(BaseModel):
    """Collection of all anomalies found in the dataset."""

    anomalies: list[Anomaly] = Field(default_factory=list)
    total_count: int = 0

    def model_post_init(self, __context) -> None:
        self.total_count = len(self.anomalies)


# ---------------------------------------------------------------------------
# LLM analysis
# ---------------------------------------------------------------------------

class LLMAnalysis(BaseModel):
    """Structured output from the LLM analysis step."""

    executive_summary: str = Field(
        ...,
        description="A 2-4 sentence plain-English summary of the dataset.",
    )
    key_insights: list[str] = Field(
        default_factory=list,
        description="Bullet-point insights drawn from the data.",
    )
    correlations_noted: list[str] = Field(
        default_factory=list,
        description="Notable correlations or relationships between columns.",
    )
    data_quality_notes: list[str] = Field(
        default_factory=list,
        description="Observations about data quality, missing values, or inconsistencies.",
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description="Actionable next steps for the user.",
    )


# ---------------------------------------------------------------------------
# Pipeline result
# ---------------------------------------------------------------------------

class ChartReference(BaseModel):
    """Reference to a generated chart file."""

    title: str
    file_name: str
    file_path: str
    description: str


class AnalysisResult(BaseModel):
    """The complete output of an analysis run — everything in one structure."""

    profile: DatasetProfile
    stats: StatsSummary
    anomalies: AnomalyReport
    llm_analysis: Optional[LLMAnalysis] = None
    charts: list[ChartReference] = Field(default_factory=list)
    report_markdown: str = ""
