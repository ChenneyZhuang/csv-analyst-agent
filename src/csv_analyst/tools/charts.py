"""
Chart generation tools using matplotlib + seaborn.

Produces PNG charts for numeric distributions, categorical bar plots,
correlation heatmaps, and outlier box plots.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

matplotlib.use("Agg")  # non-interactive backend

# ---------------------------------------------------------------------------
# Style & colour palette
# ---------------------------------------------------------------------------

COLOURS = ["#4C72B0", "#DD8452", "#55A868", "#C44E52", "#8172B3", "#937860", "#DA8BC3", "#8C8C8C"]


def _ensure_output_dir(output_dir: str | Path) -> Path:
    """Create the output directory if it doesn't exist."""
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


# ---------------------------------------------------------------------------
# Individual chart generators
# ---------------------------------------------------------------------------


def histogram(
    series: pd.Series,
    col_name: str,
    output_dir: str | Path,
    bins: int = 30,
) -> Path:
    """Generate a histogram for a numeric column."""
    out_dir = _ensure_output_dir(output_dir)
    path = out_dir / f"hist_{_sanitise(col_name)}.png"

    clean = series.dropna()
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(clean, bins=bins, color=COLOURS[0], edgecolor="white", alpha=0.85)
    ax.set_title(f"Distribution of {col_name}", fontsize=14, fontweight="bold")
    ax.set_xlabel(col_name)
    ax.set_ylabel("Frequency")
    _add_grid(ax)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def boxplot(
    series: pd.Series,
    col_name: str,
    output_dir: str | Path,
) -> Path:
    """Generate a box plot for a numeric column."""
    out_dir = _ensure_output_dir(output_dir)
    path = out_dir / f"box_{_sanitise(col_name)}.png"

    clean = series.dropna()
    fig, ax = plt.subplots(figsize=(5, 6))
    bp = ax.boxplot(clean, patch_artist=True, widths=0.4)
    for patch in bp["boxes"]:
        patch.set_facecolor(COLOURS[0])
        patch.set_alpha(0.7)
    ax.set_title(f"Box Plot — {col_name}", fontsize=14, fontweight="bold")
    ax.set_ylabel(col_name)
    ax.set_xticklabels([col_name])
    _add_grid(ax, axis="y")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def bar_chart(
    series: pd.Series,
    col_name: str,
    output_dir: str | Path,
    top_n: int = 10,
) -> Path:
    """Generate a horizontal bar chart for a categorical column."""
    out_dir = _ensure_output_dir(output_dir)
    path = out_dir / f"bar_{_sanitise(col_name)}.png"

    counts = series.dropna().value_counts().head(top_n)
    fig, ax = plt.subplots(figsize=(8, max(4, len(counts) * 0.35)))
    colours = [COLOURS[i % len(COLOURS)] for i in range(len(counts))]
    ax.barh(counts.index.astype(str)[::-1], counts.values[::-1], color=colours[::-1])
    ax.set_title(f"Top {top_n} — {col_name}", fontsize=14, fontweight="bold")
    ax.set_xlabel("Count")
    _add_grid(ax, axis="x")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def correlation_heatmap(
    corr_matrix: dict[str, dict[str, float]],
    output_dir: str | Path,
) -> Path | None:
    """Generate a correlation heatmap from the computed correlation dict.

    Returns None if the matrix is empty or has fewer than 2 columns.
    """
    columns = list(corr_matrix.keys())
    if len(columns) < 2:
        return None

    out_dir = _ensure_output_dir(output_dir)
    path = out_dir / "correlation_heatmap.png"

    n = len(columns)
    mat = np.zeros((n, n))
    for i, col_a in enumerate(columns):
        for j, col_b in enumerate(columns):
            mat[i][j] = corr_matrix[col_a].get(col_b, 0.0)

    fig, ax = plt.subplots(figsize=(max(6, n * 0.8), max(5, n * 0.7)))
    im = ax.imshow(mat, cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(columns, rotation=45, ha="right", fontsize=9)
    ax.set_yticklabels(columns, fontsize=9)
    ax.set_title("Correlation Heatmap", fontsize=14, fontweight="bold")

    # Annotate cells
    for i in range(n):
        for j in range(n):
            ax.text(
                j,
                i,
                f"{mat[i][j]:.2f}",
                ha="center",
                va="center",
                fontsize=7,
                color="white" if abs(mat[i][j]) > 0.6 else "black",
            )

    cbar = fig.colorbar(im, ax=ax, shrink=0.8)
    cbar.set_label("Pearson r")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def missing_values_heatmap(
    df: pd.DataFrame,
    output_dir: str | Path,
) -> Path | None:
    """Visualise missing values in a DataFrame as a heatmap."""
    nulls = df.isnull()
    if not nulls.any().any():
        return None  # no missing values — skip

    out_dir = _ensure_output_dir(output_dir)
    path = out_dir / "missing_values.png"

    # Sample rows if dataset is large
    sample = df if len(df) <= 200 else df.sample(200, random_state=42)
    null_sample = sample.isnull()

    fig, ax = plt.subplots(figsize=(max(8, len(sample.columns) * 0.8), 5))
    ax.imshow(null_sample.T, aspect="auto", cmap="binary_r", interpolation="none")
    ax.set_yticks(range(len(sample.columns)))
    ax.set_yticklabels(sample.columns, fontsize=8)
    ax.set_title("Missing Values (black = missing)", fontsize=14, fontweight="bold")
    ax.set_xlabel("Row (sample)")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


# ---------------------------------------------------------------------------
# Batch chart generation
# ---------------------------------------------------------------------------


def generate_all_charts(
    file_path: str | Path,
    output_dir: str | Path,
    corr_matrix: dict[str, dict[str, float]] | None = None,
) -> list[tuple[str, Path, str]]:
    """Generate all relevant charts for a CSV file.

    Returns a list of (title, file_path, description) tuples.
    """
    from csv_analyst.tools.stats import _infer_column_type

    df = pd.read_csv(file_path)
    charts: list[tuple[str, Path, str]] = []

    # ── Numeric columns: histogram + boxplot ───────────────────────────
    for col in df.columns:
        series = df[col]
        inferred = _infer_column_type(series)

        if inferred == "numeric":
            hist_path = histogram(series, col, output_dir)
            charts.append((f"Histogram: {col}", hist_path, f"Distribution of {col}"))

            box_path = boxplot(series, col, output_dir)
            charts.append((f"Box Plot: {col}", box_path, f"Outlier detection for {col}"))

        elif inferred in ("categorical", "boolean", "text"):
            bar_path = bar_chart(series, col, output_dir)
            charts.append((f"Bar Chart: {col}", bar_path, f"Top categories for {col}"))

    # ── Correlation heatmap ───────────────────────────────────────────
    if corr_matrix is None:
        from csv_analyst.tools.stats import compute_correlations

        corr_matrix = compute_correlations(file_path)

    heatmap_path = correlation_heatmap(corr_matrix, output_dir)
    if heatmap_path:
        charts.append(("Correlation Heatmap", heatmap_path, "Numeric column correlations"))

    # ── Missing values heatmap ────────────────────────────────────────
    mv_path = missing_values_heatmap(df, output_dir)
    if mv_path:
        charts.append(("Missing Values", mv_path, "Visualisation of missing data"))

    return charts


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sanitise(name: str) -> str:
    """Replace non-alphanumeric characters with underscores for safe filenames."""
    return "".join(c if c.isalnum() or c == "_" else "_" for c in name)


def _add_grid(ax: plt.Axes, axis: str = "y") -> None:
    """Add a light dashed grid to the given axis."""
    ax.grid(visible=True, axis=axis, linestyle="--", alpha=0.4)
