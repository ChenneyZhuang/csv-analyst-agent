"""
Analysis Pipeline — orchestrates the full CSV analysis workflow.

Steps:
1. Profile the dataset (column types, row counts, etc.)
2. Compute statistical summaries (mean, median, std, distributions)
3. Detect anomalies and outliers
4. Compute correlations
5. Generate charts (histograms, boxplots, bar charts, heatmaps)
6. Run LLM-based analysis (optional, requires API key)
7. Build the final markdown report
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from csv_analyst.agents.analyser import run_llm_analysis
from csv_analyst.config import config
from csv_analyst.models.schemas import (
    AnalysisResult,
    ChartReference,
    LLMAnalysis,
)
from csv_analyst.tools.charts import generate_all_charts
from csv_analyst.tools.stats import (
    compute_correlations,
    compute_stats_summary,
    detect_anomalies,
    profile_dataset,
)


class AnalysisPipeline:
    """Orchestrates the complete CSV analysis workflow.

    Usage::

        pipeline = AnalysisPipeline()
        result = pipeline.run("data.csv", output_dir="./charts")
        print(result.report_markdown)

    Parameters
    ----------
    llm_enabled:
        Whether to run the LLM analysis step. Defaults to ``True``.
        Set to ``False`` for offline-only analysis.
    """

    def __init__(self, llm_enabled: bool = True) -> None:
        self.llm_enabled = llm_enabled

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(
        self,
        file_path: str | Path,
        output_dir: str | Path = "./charts",
    ) -> AnalysisResult:
        """Execute the full analysis pipeline on a CSV file.

        Parameters
        ----------
        file_path:
            Path to the CSV file to analyse.
        output_dir:
            Directory where charts will be saved.

        Returns
        -------
        AnalysisResult
            The complete analysis result including profile, stats, anomalies,
            charts, LLM analysis, and the rendered markdown report.
        """
        file_path = Path(file_path).resolve()
        output_dir = Path(output_dir)

        if not file_path.exists():
            raise FileNotFoundError(f"CSV file not found: {file_path}")

        # Load the CSV once — shared across all steps
        df = pd.read_csv(file_path)

        # Step 1 — Profile
        profile = profile_dataset(file_path)

        # Step 2 — Statistical summary
        stats = compute_stats_summary(file_path)

        # Step 3 — Anomaly detection
        anomalies = detect_anomalies(file_path)

        # Step 4 — Correlations
        correlations = compute_correlations(file_path)

        # Step 5 — Charts
        raw_charts = generate_all_charts(file_path, output_dir, corr_matrix=correlations)
        charts = [
            ChartReference(
                title=title,
                file_name=path.name,
                file_path=str(path.resolve()),
                description=desc,
            )
            for title, path, desc in raw_charts
        ]

        # Step 6 — LLM analysis (optional)
        llm_analysis: LLMAnalysis | None = None
        if self.llm_enabled and config.is_api_key_set:
            try:
                sample_rows = df.head(config.max_sample_rows).to_dict(orient="records")
                llm_analysis = run_llm_analysis(
                    profile=profile,
                    stats=stats,
                    anomalies=anomalies,
                    correlations=correlations,
                    sample_rows=sample_rows,
                )
            except Exception as exc:
                # LLM failures shouldn't block the entire pipeline
                llm_analysis = LLMAnalysis(
                    executive_summary=f"LLM analysis skipped due to error: {exc}",
                )

        # Step 7 — Build markdown report
        report_md = self._build_report(
            profile=profile,
            stats=stats,
            anomalies=anomalies,
            correlations=correlations,
            charts=charts,
            llm_analysis=llm_analysis,
        )

        return AnalysisResult(
            profile=profile,
            stats=stats,
            anomalies=anomalies,
            llm_analysis=llm_analysis,
            charts=charts,
            report_markdown=report_md,
        )

    # ------------------------------------------------------------------
    # Markdown report builder
    # ------------------------------------------------------------------

    @staticmethod
    def _build_report(
        profile,
        stats,
        anomalies,
        correlations: dict,
        charts: list[ChartReference],
        llm_analysis: LLMAnalysis | None,
    ) -> str:
        """Render the full markdown analysis report."""
        lines: list[str] = []

        # ── Title ──────────────────────────────────────────────────────
        lines.append("# CSV Analysis Report")
        lines.append("")
        lines.append(f"**File:** `{profile.file_path}`  ")
        lines.append(f"**Generated:** {profile.profiled_at}  ")
        lines.append(f"**Rows:** {profile.row_count:,}  |  **Columns:** {profile.column_count}  ")
        lines.append(f"**File size:** {profile.file_size_bytes:,} bytes  ")
        lines.append("")

        # ── LLM Executive Summary ─────────────────────────────────────
        if llm_analysis and llm_analysis.executive_summary:
            lines.append("## 🤖 AI Analysis Summary")
            lines.append("")
            lines.append(f"{llm_analysis.executive_summary}")
            lines.append("")

        # ── Column Overview ───────────────────────────────────────────
        lines.append("## 📋 Column Overview")
        lines.append("")
        lines.append("| # | Column | Type | Missing | Unique | Sample |")
        lines.append("|---|--------|------|---------|--------|--------|")
        for i, col in enumerate(profile.columns, 1):
            sample = ", ".join(col.sample_values[:3])
            lines.append(f"| {i} | `{col.name}` | {col.inferred_type} | {col.null_pct:.1f}% | {col.unique_count} | {sample} |")
        lines.append("")

        # ── Numeric Stats ─────────────────────────────────────────────
        if stats.numeric_stats:
            lines.append("## 📊 Numeric Column Statistics")
            lines.append("")
            lines.append("| Column | Count | Mean | Median | Std | Min | Max | Q25 | Q75 | Skew | Kurt |")
            lines.append("|--------|-------|------|--------|-----|-----|-----|-----|-----|------|------|")
            for ns in stats.numeric_stats:
                skew_str = f"{ns.skewness:.2f}" if ns.skewness is not None else "N/A"
                kurt_str = f"{ns.kurtosis:.2f}" if ns.kurtosis is not None else "N/A"
                lines.append(
                    f"| `{ns.column}` | {ns.count} | {ns.mean:.2f} | {ns.median:.2f} | "
                    f"{ns.std:.2f} | {ns.min:.2f} | {ns.max:.2f} | "
                    f"{ns.q25:.2f} | {ns.q75:.2f} | "
                    f"{skew_str} | {kurt_str} |"
                )
            lines.append("")

        # ── Categorical Stats ─────────────────────────────────────────
        if stats.categorical_stats:
            lines.append("## 🏷️ Categorical Column Statistics")
            lines.append("")
            for cs in stats.categorical_stats:
                lines.append(f"### `{cs.column}`")
                lines.append("")
                lines.append(f"- **Unique values:** {cs.unique_count}")
                if cs.top_value:
                    lines.append(f"- **Most common:** `{cs.top_value}` ({cs.top_freq} occurrences, {cs.top_pct:.1f}%)")
                if cs.value_counts:
                    lines.append("- **Top values:**")
                    for val, cnt in list(cs.value_counts.items())[:10]:
                        lines.append(f"  - `{val}`: {cnt}")
                lines.append("")
            lines.append("")

        # ── Anomalies ─────────────────────────────────────────────────
        lines.append("## ⚠️ Anomalies & Outliers")
        lines.append("")
        lines.append(f"**Total anomalies detected:** {anomalies.total_count}")
        lines.append("")
        if anomalies.anomalies:
            for a in anomalies.anomalies[:50]:
                loc = f" [row {a.row_index}]" if a.row_index is not None else ""
                lines.append(f"- **`{a.column}`**{loc} ({a.severity}): {a.value} — {a.reason}")
        else:
            lines.append("✅ No anomalies detected.")
        lines.append("")

        # ── Correlations ──────────────────────────────────────────────
        if correlations:
            lines.append("## 🔗 Correlations")
            lines.append("")
            cols = list(correlations.keys())
            header = "| | " + " | ".join(f"`{c}`" for c in cols) + " |"
            lines.append(header)
            lines.append("|" + "---|" * (len(cols) + 1))
            for col_a in cols:
                vals = " | ".join(f"{correlations[col_a].get(col_b, 0):.3f}" for col_b in cols)
                lines.append(f"| `{col_a}` | {vals} |")
            lines.append("")

        # ── Charts ────────────────────────────────────────────────────
        if charts:
            lines.append("## 📈 Charts")
            lines.append("")
            for chart in charts:
                lines.append(f"### {chart.title}")
                lines.append("")
                lines.append(f"![{chart.title}]({chart.file_name})")
                lines.append("")
                lines.append(f"_{chart.description}_")
                lines.append("")

        # ── LLM Insights ──────────────────────────────────────────────
        if llm_analysis:
            if llm_analysis.key_insights:
                lines.append("## 💡 Key Insights")
                lines.append("")
                for insight in llm_analysis.key_insights:
                    lines.append(f"- {insight}")
                lines.append("")

            if llm_analysis.correlations_noted:
                lines.append("## 🔍 Notable Correlations")
                lines.append("")
                for c in llm_analysis.correlations_noted:
                    lines.append(f"- {c}")
                lines.append("")

            if llm_analysis.data_quality_notes:
                lines.append("## 🧹 Data Quality Notes")
                lines.append("")
                for dq in llm_analysis.data_quality_notes:
                    lines.append(f"- {dq}")
                lines.append("")

            if llm_analysis.recommendations:
                lines.append("## 🚀 Recommendations")
                lines.append("")
                for rec in llm_analysis.recommendations:
                    lines.append(f"- {rec}")
                lines.append("")

        # ── Footer ────────────────────────────────────────────────────
        lines.append("---")
        lines.append("")
        lines.append("*Report generated by [csv-analyst](https://github.com/ChenneyZhuang/csv-analyst-agent) v0.1.0*")
        lines.append("")

        return "\n".join(lines)
