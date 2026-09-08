# Development Gap Explorer

Development Gap Explorer is a small Python data product for development and
policy analysts. It combines economic and social indicators from the World
Bank to help analysts identify countries or economies that warrant further
research.

The product is descriptive. It does not provide investment advice, forecast
outcomes, assign country ratings, or establish that one indicator caused
another to change.

## What the dashboard answers

For the initial period, 2010–2024, the dashboard lets an analyst:

- compare country-level changes in GDP per capita, life expectancy,
  unemployment, and population;
- filter the comparison by region, income group, and transparent research
  signals;
- select one country or economy and inspect its annual time series;
- see data quality and missing-value information before interpreting a result.

The dashboard treats a signal as a prompt for research, not a conclusion. For
example, high GDP-per-capita growth paired with relatively low life-expectancy
improvement is a question worth investigating. It does not prove that growth
failed to improve wellbeing, or explain why a pattern occurred.

## Source and indicators

Source: [World Bank Indicators API](https://api.worldbank.org/v2/). No API key
is required.

| Indicator | World Bank code | Role |
| --- | --- | --- |
| GDP per capita, constant 2015 US dollars | `NY.GDP.PCAP.KD` | Core |
| GDP per capita growth, annual % | `NY.GDP.PCAP.KD.ZG` | Supplementary |
| Unemployment, total (% of total labor force) | `SL.UEM.TOTL.ZS` | Core |
| Life expectancy at birth, total (years) | `SP.DYN.LE00.IN` | Core |
| Population, total | `SP.POP.TOTL` | Core |
| School enrollment, secondary (gross), % | `SE.SEC.ENRR` | Optional |

The pipeline retains only country/economy entities. World Bank aggregate groups
such as “World”, income groups, and regional totals are intentionally excluded
from country comparisons.

## Architecture and data flow

```text
World Bank Indicators API
        |
        v
Raw JSON pages + manifest       data/raw/world_bank/<run_id>/
        |
        v
Validation and country-year model
        |
        v
Processed CSV and quality report data/processed/<run_id>/
        |
        v
Descriptive country metrics
        |
        v
Streamlit dashboard             app.py
```

Each extraction records complete API pages, pagination metadata, retrieval
time, and a manifest. Transformations run in a staging directory before their
output is promoted to a successful run. `data/processed/latest_run.json` points
the dashboard to the most recent successful run.

## Local setup and run

Python 3.10 or later is recommended. Use a project virtual environment rather
than the global Anaconda `base` environment, so this project cannot change the
dependencies of unrelated tools.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python etl.py
streamlit run app.py
```

`python etl.py` downloads a new, timestamped raw snapshot and creates the
processed outputs. Use this when refreshing the data. To rebuild descriptive
metrics from the latest processed run without downloading again:

```powershell
python metrics.py
```

Run automated tests with:

```powershell
python -m unittest discover -s tests -v
```

## Processed data model

The main analytical table is:

```text
data/processed/<run_id>/country_year.csv
```

It has one row per `country_code` and `year`, with country metadata and a wide
column for each indicator. The initial full run contains 3,255 rows: 217
countries/economies × 15 years.

The metrics layer writes `country_progress_2010_2024.csv`. It contains each
country’s start value, end value, change over the period, whether all core
comparisons are available, and transparent research signals.

## Data quality and validation

The pipeline checks that:

- API responses use the expected JSON envelope and all reported pages are
  retrieved;
- the country-year key is unique;
- aggregate entities do not enter the country analysis;
- identifiers map to the country metadata;
- numeric values are valid for their indicator;
- missing values stay missing rather than becoming zero.

The successful 2026-09-07 run created 3,255 country-year rows with no duplicate
keys, no unmapped entities, and no invalid values. It completed with missing
values, which is expected for some World Bank series. The dashboard exposes the
missing-observation counts so users can interpret comparisons responsibly.

The reproducible API feasibility findings are in
`outputs/world_bank_api_feasibility_report.md`. The full ETL and metrics run
reports are in `outputs/etl_run_validation_report.md` and
`outputs/metrics_validation_report.md`.

## Limitations

- World Bank coverage can vary by country, year, and indicator. The dashboard
  leaves unavailable comparisons blank.
- The data supports comparison and exploratory research, not causal inference.
- Country/economy labels follow World Bank metadata.
- The optional secondary-enrollment series has materially lower coverage, so it
  is retained but excluded from the core comparison signals.
- The default dashboard window is 2010–2024. Its research-signal thresholds are
  calculated from observed countries in that window and documented in the
  processed metric-definitions file.

## Assumptions

- A World Bank entity classified as a country/economy is appropriate for the
  comparison population. Aggregate groups are excluded.
- Start-to-end changes over 2010–2024 are useful descriptive summaries, while
  the country view retains annual observations for further inspection.
- The research signals are intentionally transparent, simple screening rules.
  They are not risk scores or a ranking of country performance.
- The data source's published values and metadata are used as received. The
  pipeline validates structure and ranges but does not revise source values.

## What I would improve with more time

- Let analysts choose a validated comparison window in the dashboard and
  regenerate metrics for that window.
- Add peer-group comparisons, such as countries in the same income group or
  region, while preserving the distinction between descriptive comparison and
  causal analysis.
- Add a scheduled refresh and historical run comparison to make data updates
  observable over time.
- Add integration tests that run against a recorded API fixture and browser
  smoke tests for the Streamlit interface.

## Repository guide

| Path | Purpose |
| --- | --- |
| `etl.py` | Runs extraction, transformation, validation, and metrics |
| `metrics.py` | Rebuilds metrics from the latest processed run |
| `app.py` | Streamlit dashboard |
| `src/` | API client, extraction, transformation, metrics, dashboard loaders |
| `tests/` | Automated unit tests |
| `data/raw/` | Timestamped raw API snapshots, ignored by Git |
| `data/processed/` | Timestamped processed outputs, ignored by Git |
| `outputs/` | Readable feasibility and validation reports |
| `ai_transcript/` | Required AI-assistance transcript material |

## AI assistance disclosure

AI assistance was used for planning, implementation, documentation, and review.
The available conversation handoff is preserved in `ai_transcript/`. Before
submission, add the complete AI transcript required by the assignment; the
current files explicitly distinguish the bounded handoff from a full transcript.
