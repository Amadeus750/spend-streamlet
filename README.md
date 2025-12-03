# Spend Analytics Dashboard

A Streamlit dashboard for visualizing and analyzing spend data by category and subcategory.

## Features

- **Interactive Filters** – Filter by fiscal year, category, subcategory, and vendor
- **Key Metrics** – Total spend, unique vendors, transaction count, category count
- **Visualizations** – Bar charts, pie charts, trend lines, and sunburst diagrams
- **Data Table** – Detailed spend records with search and sort

## Quick Start

```bash
# Install dependencies
uv sync

# Run the dashboard
uv run streamlit run app.py
```

Open http://localhost:8501 in your browser.

## Project Structure

```
├── app.py                 # Streamlit dashboard
├── data/                  # Parquet and source data files
├── src/
│   ├── functions.py       # AI categorization utilities
│   ├── spend.ipynb        # Data processing notebook
│   └── main.ipynb         # Additional analysis
└── tests/
    └── test.py
```

## Data

The dashboard reads from `data/spend_data_categorized.parquet`, which contains spend records enriched with AI-generated `category` and `sub_category` fields.

## Requirements

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) package manager

