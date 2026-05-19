"""
LLM-based analysis agent using the DeepSeek API (OpenAI-compatible).

Sends structured information about the dataset to an LLM and parses the
response into a structured :class:`LLMAnalysis` object.
"""

from __future__ import annotations

import json
import re
from typing import Any

from openai import OpenAI

from csv_analyst.config import config
from csv_analyst.models.schemas import (
    AnomalyReport,
    DatasetProfile,
    LLMAnalysis,
    StatsSummary,
)

# ---------------------------------------------------------------------------
# Prompt template
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are an expert data analyst. You receive structured information about a CSV
dataset and produce a concise, insightful analysis report in JSON format.

## Rules
- Be precise — base every statement on the provided data.
- If you notice data-quality issues, mention them.
- Suggest concrete next steps the user could take.
- Always respond with valid JSON matching the schema below.

## JSON Schema
{
  "executive_summary": "<2-4 sentence plain-English summary>",
  "key_insights": ["<insight 1>", "<insight 2>", "..."],
  "correlations_noted": ["<correlation observation>", ...],
  "data_quality_notes": ["<quality note>", ...],
  "recommendations": ["<actionable recommendation>", ...]
}

Important: return ONLY the JSON object, no markdown fences, no extra text.
"""


def _build_user_prompt(
    profile: DatasetProfile,
    stats: StatsSummary,
    anomalies: AnomalyReport,
    correlations: dict[str, dict[str, float]],
    sample_rows: list[dict[str, Any]],
) -> str:
    """Build the user-prompt payload for the LLM."""

    # ── Profile summary ────────────────────────────────────────────────
    profile_lines: list[str] = [
        "**Dataset Profile**",
        f"- File: {profile.file_path}",
        f"- Rows: {profile.row_count:,}  |  Columns: {profile.column_count}",
        f"- File size: {profile.file_size_bytes:,} bytes",
        "",
        "**Column Metadata:**",
    ]
    for col in profile.columns:
        profile_lines.append(
            f"  - `{col.name}` → {col.inferred_type} ({col.dtype}), {col.null_pct:.1f}% missing, {col.unique_count} unique"
        )

    # ── Numeric stats ─────────────────────────────────────────────────
    stats_lines: list[str] = ["", "**Numeric Column Statistics:**"]
    for ns in stats.numeric_stats:
        line = (
            f"  - `{ns.column}`: count={ns.count}, mean={ns.mean:.2f}, "
            f"median={ns.median:.2f}, std={ns.std:.2f}, "
            f"min={ns.min:.2f}, max={ns.max:.2f}, "
            f"Q25={ns.q25:.2f}, Q75={ns.q75:.2f}"
        )
        if ns.skewness is not None:
            line += f", skew={ns.skewness:.2f}, kurt={ns.kurtosis:.2f}"
        stats_lines.append(line)

    # ── Categorical stats ─────────────────────────────────────────────
    cat_lines: list[str] = ["", "**Categorical Column Statistics:**"]
    for cs in stats.categorical_stats:
        top_info = f"top='{cs.top_value}' ({cs.top_pct:.1f}%)" if cs.top_value else "N/A"
        cat_lines.append(f"  - `{cs.column}`: {cs.unique_count} unique values, {top_info}")

    # ── Anomalies ──────────────────────────────────────────────────────
    anomaly_lines: list[str] = [
        "",
        f"**Anomalies Detected:** {anomalies.total_count} total",
    ]
    for a in anomalies.anomalies[:30]:  # cap for prompt length
        loc = f" [row {a.row_index}]" if a.row_index is not None else ""
        anomaly_lines.append(f"  - `{a.column}`{loc}: {a.value} ({a.severity}) — {a.reason}")

    # ── Correlations ────────────────────────────────────────────────────
    corr_lines: list[str] = ["", "**Correlation Matrix (Pearson):**"]
    if correlations:
        columns = list(correlations.keys())
        corr_lines.append("  " + ", ".join(columns))
        for col_a in columns:
            vals = ", ".join(f"{col_b}={correlations[col_a].get(col_b, 'N/A')}" for col_b in columns)
            corr_lines.append(f"  {col_a}: {vals}")
    else:
        corr_lines.append("  (no numeric columns for correlation)")

    # ── Sample rows ────────────────────────────────────────────────────
    sample_lines: list[str] = ["", "**Sample Rows (first 10):**"]
    for i, row in enumerate(sample_rows[:10], 1):
        row_str = ", ".join(f"{k}={v}" for k, v in row.items())
        sample_lines.append(f"  Row {i}: {row_str}")

    parts = [
        "\n".join(profile_lines),
        "\n".join(stats_lines),
        "\n".join(cat_lines),
        "\n".join(anomaly_lines),
        "\n".join(corr_lines),
        "\n".join(sample_lines),
    ]
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# JSON extraction (robust against markdown fences)
# ---------------------------------------------------------------------------


def _extract_json(text: str) -> dict[str, Any]:
    """Extract a JSON object from LLM output, even if wrapped in markdown."""
    # Try direct parse first
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try stripping ```json ... ``` fences
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence_match:
        try:
            return json.loads(fence_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Try to find the first { ... } block
    brace_match = re.search(r"\{[\s\S]*\}", text)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not parse JSON from LLM response: {text[:200]}...")


# ---------------------------------------------------------------------------
# Main analyser
# ---------------------------------------------------------------------------


def run_llm_analysis(
    profile: DatasetProfile,
    stats: StatsSummary,
    anomalies: AnomalyReport,
    correlations: dict[str, dict[str, float]],
    sample_rows: list[dict[str, Any]],
) -> LLMAnalysis:
    """Send dataset information to the LLM and parse the structured response.

    Parameters
    ----------
    profile:
        Dataset profile with column metadata.
    stats:
        Statistical summary for numeric and categorical columns.
    anomalies:
        Anomaly report with outlier and data-quality issues.
    correlations:
        Correlation matrix as nested dict.
    sample_rows:
        First N rows of the dataset for context.

    Returns
    -------
    LLMAnalysis
    """
    if not config.is_api_key_set:
        raise RuntimeError(
            "DEEPSEEK_API_KEY is not set. "
            "Copy .env.example to .env and add your API key, "
            "or set the environment variable directly."
        )

    client = OpenAI(
        api_key=config.deepseek_api_key,
        base_url=config.deepseek_base_url,
    )

    user_prompt = _build_user_prompt(profile, stats, anomalies, correlations, sample_rows)

    response = client.chat.completions.create(
        model=config.deepseek_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=config.deepseek_temperature,
        max_tokens=config.deepseek_max_tokens,
    )

    content = response.choices[0].message.content or "{}"
    data = _extract_json(content)

    return LLMAnalysis(
        executive_summary=data.get("executive_summary", "No summary provided."),
        key_insights=data.get("key_insights", []),
        correlations_noted=data.get("correlations_noted", []),
        data_quality_notes=data.get("data_quality_notes", []),
        recommendations=data.get("recommendations", []),
    )
