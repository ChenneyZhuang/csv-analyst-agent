# CSV Analyst Agent

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Upload any CSV file → AI analyses it → get charts + a markdown report.**

An AI agent that understands your data: column types, statistical patterns, outliers, trends, and generates professional analysis reports with matplotlib charts.

## Table of Contents

- [What It Does](#what-it-does)
- [Features](#features)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Usage](#usage)
- [Output](#output)
- [How It Works](#how-it-works)
- [FAQ](#faq)
- [License](#license)

## What It Does

```
   data.csv
      │
      ▼
┌──────────────┐
│ 1. Load CSV   │ → pandas DataFrame
├──────────────┤
│ 2. Profile    │ → column types, stats, distributions
├──────────────┤
│ 3. Analyse    │ → DeepSeek: patterns, anomalies, insights
├──────────────┤
│ 4. Visualise  │ → matplotlib charts (PNG)
├──────────────┤
│ 5. Report     │ → analysis.md (markdown)
└──────────────┘
      │
      ▼
   analysis.md + charts/*.png
```

## Features

- **Auto-detect column types** — numeric, categorical, datetime, text
- **Full statistical summary** — mean, median, std, quartiles, skew, unique values
- **Anomaly detection** — IQR-based outlier detection for numeric columns
- **Correlation analysis** — heatmap for numeric columns
- **LLM-powered insights** — DeepSeek interprets patterns and writes analysis
- **Chart generation** — bar charts, histograms, scatter plots, box plots, heatmaps
- **Markdown report** — clean, professional report with charts embedded

## Quick Start

```bash
# 1. Install
pip install git+https://github.com/ChenneyZhuang/csv-analyst-agent.git

# 2. Set API key
export DEEPSEEK_API_KEY="sk-..."

# 3. Analyse
csv-analyst run data.csv
```

That's it. You'll get an `analysis/` folder with a report and charts.

## Installation

### From GitHub (recommended)

```bash
pip install git+https://github.com/ChenneyZhuang/csv-analyst-agent.git
```

### From source

```bash
git clone https://github.com/ChenneyZhuang/csv-analyst-agent.git
cd csv-analyst-agent
pip install -e .
```

### Requirements

- Python 3.11+
- DeepSeek API key (or any OpenAI-compatible endpoint)
- pandas and matplotlib (auto-installed as dependencies)

## Usage

### CLI

```bash
# Basic analysis
csv-analyst run data.csv

# Custom output directory
csv-analyst run data.csv --output ./my-report

# Skip LLM analysis (stats + charts only)
csv-analyst run data.csv --no-llm

# Specify columns to analyse
csv-analyst run data.csv --columns price,quantity,region
```

### Python API

```python
from csv_analyst import run_analysis

result = run_analysis("sales_data.csv")
# result.report  → markdown text
# result.charts  → list of chart file paths
# result.stats   → pandas describe() output
# result.insights → LLM-generated insights
```

## Output

```
analysis/
├── report.md          # Full markdown report
├── charts/
│   ├── distribution_price.png
│   ├── correlation_heatmap.png
│   └── boxplot_outliers.png
└── stats.json         # Raw statistics
```

## How It Works

### Step 1: Profile
Load CSV with pandas → detect types → basic stats (describe(), info(), null counts)

### Step 2: Statistics
For each numeric column: mean, median, std, min, max, quartiles, skewness, outliers (IQR method). For categorical: unique values, frequencies, mode.

### Step 3: Charts
Auto-generate appropriate charts:
- Histogram for numeric distributions
- Box plot for outlier visualisation
- Bar chart for categorical counts
- Correlation heatmap for numeric relationships
- Scatter plot for pairs with high correlation

### Step 4: LLM Analysis
Send stats summary + sample data to DeepSeek → get back:
- Data overview
- Key findings
- Anomalies explained
- Recommendations
- Suggested next steps

### Step 5: Report
Combine everything into `report.md` with embedded chart references.

## Configuration

| Env Variable | Default | Description |
|-------------|---------|-------------|
| `DEEPSEEK_API_KEY` | (required) | Your API key |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | API endpoint |
| `CSV_ANALYST_MAX_ROWS` | `100000` | Max rows to load |

## FAQ

**Q: What file formats are supported?**
A: CSV files (`.csv`). TSV, Excel coming soon.

**Q: How much does it cost?**
A: ~$0.01-0.05 per analysis (DeepSeek API cost). Stats + charts only mode is free.

**Q: Can it handle large files?**
A: Up to 100,000 rows by default. Configurable via `CSV_ANALYST_MAX_ROWS`.

**Q: Does it modify my data?**
A: No. Read-only analysis. Your original CSV is never modified.

**Q: What if my CSV has messy data?**
A: Auto-skips unparseable rows, reports them in the analysis.

## License

MIT — free for personal and commercial use.
