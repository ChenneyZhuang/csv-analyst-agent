# 📊 CSV Analyst Agent

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Status: Alpha](https://img.shields.io/badge/Status-Alpha-orange.svg)]()

**Drop in a CSV → get a full statistical analysis report with charts.**
Zero config. AI-powered insights optional.

---

## ✨ What It Does

```
   sales.csv
      │
      ▼
┌──────────────┐
│ 1. Profile    │ → Column types, null counts, unique values
├──────────────┤
│ 2. Statistics │ → Mean, median, std, quartiles, skew, kurtosis
├──────────────┤
│ 3. Anomalies  │ → IQR + Z-score outlier detection
├──────────────┤
│ 4. Charts     │ → Histograms, box plots, bar charts, heatmaps
├──────────────┤
│ 5. AI Summary │ → DeepSeek interprets patterns (optional)
├──────────────┤
│ 6. Report     │ → Single markdown file with embedded charts
└──────────────┘
      │
      ▼
   report.md + charts/*.png
```

---

## 🚀 Quick Start

```bash
# 1. Install
pip install git+https://github.com/ChenneyZhuang/csv-analyst-agent.git

# 2. Set API key (optional — skip with --no-llm for stats + charts only)
export DEEPSEEK_API_KEY="sk-..."

# 3. Analyse
csv-analyst run data.csv

# Done. Open report.md.
```

---

## 📦 Installation

### From GitHub

```bash
pip install git+https://github.com/ChenneyZhuang/csv-analyst-agent.git
```

### From source

```bash
git clone https://github.com/ChenneyZhuang/csv-analyst-agent.git
cd csv-analyst-agent
pip install -e .
```

### Dependencies

All installed automatically:

| Package | Purpose |
|---------|---------|
| `pandas>=2.0` | CSV parsing and data manipulation |
| `numpy>=1.24` | Numerical computation |
| `scipy>=1.10` | Skew, kurtosis, statistical tests |
| `matplotlib>=3.7` | Chart generation |
| `pydantic>=2.0` | Data validation |
| `openai>=1.0` | DeepSeek API client (OpenAI-compatible) |
| `rich>=13.0` | Terminal output formatting |
| `click>=8.0` | CLI framework |
| `python-dotenv>=1.0` | `.env` file loading |

---

## 🧰 Usage

### CLI

```bash
# Basic analysis
csv-analyst run data.csv

# Custom output
csv-analyst run data.csv --output my-report.md --charts-dir ./plots

# Stats + charts only (no AI, no API key needed)
csv-analyst run data.csv --no-llm

# Verbose mode
csv-analyst run data.csv -v

# Check version
csv-analyst version
```

### Python API

```python
from csv_analyst import AnalysisPipeline

# With AI analysis (needs DEEPSEEK_API_KEY)
pipeline = AnalysisPipeline(llm_enabled=True)
result = pipeline.run("data.csv", output_dir="./charts")

# Stats + charts only (offline)
pipeline = AnalysisPipeline(llm_enabled=False)
result = pipeline.run("data.csv")

# Access results
print(result.report_markdown)       # Full markdown report
print(result.profile.row_count)     # Number of rows
print(result.profile.column_count)  # Number of columns
print(result.anomalies.total_count) # Anomalies found
print(len(result.charts))           # Number of charts generated
print(result.llm_analysis)          # AI insights (None if --no-llm)
```

### Using with Hermes Agent

```bash
# Install the skill
hermes skills install csv-analyst-agent

# Then in Hermes: "analyse this CSV file"
```

---

## 📂 Output Structure

```
report.md                  # Complete markdown analysis report
charts/
├── hist_age.png           # Histogram for each numeric column
├── hist_salary.png
├── box_age.png            # Box plot for outlier detection
├── box_salary.png
├── bar_department.png     # Bar chart for each categorical column
├── correlation_heatmap.png # Numeric correlation matrix
└── missing_values.png     # Missing data heatmap (only if missing values exist)
```

---

## 🧠 How It Works

### Step 1 — Profile
Read CSV with pandas → infer column types (numeric, categorical, datetime, boolean, text) → count nulls, unique values, file size.

### Step 2 — Statistics
For numeric columns: count, mean, median, std, min, max, Q25, Q75, skewness, kurtosis.
For categorical columns: unique count, top value, frequency distribution.

### Step 3 — Anomalies
- **Missing values**: flagged as info/warning/critical by percentage
- **Outliers**: IQR method (1.5× IQR) + Z-score (3σ default)
- Each anomaly includes severity level and row index

### Step 4 — Charts (matplotlib Agg backend)
- Histogram for every numeric column
- Box plot for every numeric column
- Horizontal bar chart for every categorical column (top 10 values)
- Correlation heatmap for numeric columns (2+ columns required)
- Missing values heatmap (only if missing data exists)

### Step 5 — LLM Analysis (optional)
Sends structured profile + stats + anomalies + correlations + sample rows to DeepSeek.
Returns: executive summary, key insights, correlation observations, data quality notes, recommendations.

### Step 6 — Report
Combines everything into a clean markdown report with embedded chart images.

---

## ⚙️ Configuration

All via environment variables or `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `DEEPSEEK_API_KEY` | *(required for AI)* | DeepSeek API key |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com/v1` | API endpoint |
| `DEEPSEEK_MODEL` | `deepseek-chat` | Model name |
| `DEEPSEEK_MAX_TOKENS` | `4096` | Max tokens for LLM response |
| `DEEPSEEK_TEMPERATURE` | `0.3` | LLM temperature |
| `CSV_ANALYST_CHARTS_DIR` | `./charts` | Default chart output directory |
| `CSV_ANALYST_MAX_SAMPLE_ROWS` | `50` | Sample rows sent to LLM for context |

---

## 📊 Example

Input `employees.csv`:

| name | age | salary | department |
|------|-----|--------|------------|
| Alice | 28 | 75000 | Engineering |
| Bob | 35 | 85000 | Engineering |
| Charlie | 42 | 120000 | Management |
| ... | ... | ... | ... |

Generated report includes:

```markdown
# CSV Analysis Report

**File:** employees.csv
**Rows:** 10 | **Columns:** 4

## 📋 Column Overview
| # | Column | Type | Missing | Unique | Sample |
|---|--------|------|---------|--------|--------|
| 1 | name | text | 0.0% | 10 | Alice, Bob, Charlie |
| 2 | age | numeric | 0.0% | 10 | 28, 35, 42 |
| 3 | salary | numeric | 0.0% | 10 | 75000, 85000, 120000 |
| 4 | department | text | 0.0% | 3 | Engineering, Management, Marketing |

## 📊 Numeric Column Statistics
| Column | Count | Mean | Median | Std | Min | Max | Q25 | Q75 | Skew | Kurt |
|--------|-------|------|--------|-----|-----|-----|-----|-----|------|------|
| age | 10 | 35.70 | 34.00 | 7.92 | 26.00 | 50.00 | 29.50 | 41.00 | 0.61 | -0.68 |
| salary | 10 | 93800.00 | 81500.00 | 29453.54 | 65000.00 | 150000.00 | 72750.00 | 113750.00 | 0.98 | -0.36 |

## ⚠️ Anomalies & Outliers
✅ No anomalies detected.

## 🔗 Correlations
| | age | salary |
|---|-----|--------|
| age | 1.000 | 0.893 |
| salary | 0.893 | 1.000 |

## 📈 Charts
### Histogram: age
![Histogram: age](hist_age.png)
...
```

---

## ❓ FAQ

**What file formats are supported?**
CSV (`.csv`). Excel (`.xlsx`) support planned.

**How much does it cost?**
$0 with `--no-llm` (stats + charts only). With LLM enabled, ~$0.01 per analysis (DeepSeek pricing).

**Does it modify my data?**
No. Read-only analysis. Your CSV is never modified.

**What Python version do I need?**
Python 3.11 or later.

**Can I use it without internet?**
Yes — `--no-llm` mode works fully offline.

**What if my CSV has messy data?**
Missing values are reported as anomalies. Non-numeric data in numeric columns is handled gracefully.

---

## 🧪 Testing

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run linting
ruff check src/

# Type checking
mypy src/
```

---

## 🛣️ Roadmap

- [ ] Excel (`.xlsx`) support
- [ ] Interactive HTML reports
- [ ] Multi-file comparison
- [ ] Time series analysis
- [ ] Custom chart themes
- [ ] Streaming mode for large files (>100k rows)

---

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch
3. Commit your changes
4. Push and open a Pull Request

---

## 📄 License

MIT © [Chenney Zhuang](https://github.com/ChenneyZhuang)
