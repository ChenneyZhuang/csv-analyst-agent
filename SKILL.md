---
name: csv-analyst-agent
description: AI-powered CSV data analysis — stats, charts, and LLM insights.
version: 0.1.0
platforms: [linux, macos]
---

# CSV Analyst Agent

Upload a CSV → get statistical analysis, charts, and AI-powered insights.

## Usage in Hermes

```bash
# CLI
csv-analyst run /path/to/data.csv

# Python
from csv_analyst import AnalysisPipeline
result = AnalysisPipeline().run("data.csv")
```

## Install

```bash
pip install git+https://github.com/ChenneyZhuang/csv-analyst-agent.git
```

## Reference

- GitHub: https://github.com/ChenneyZhuang/csv-analyst-agent
- License: MIT
