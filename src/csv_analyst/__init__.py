"""
CSV Analyst — AI-powered CSV data analysis agent.

Auto-detect column types, generate statistical summaries,
find anomalies, create charts, and produce markdown reports.
"""

__version__ = "0.1.0"
__author__ = "Chenney Zhuang"

from csv_analyst.pipeline import AnalysisPipeline

__all__ = ["AnalysisPipeline", "__version__"]
