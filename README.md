# Development Gap Explorer

Development Gap Explorer compares economic and social progress across
countries over time. It combines World Bank indicators to help development and
policy analysts identify countries or economies that warrant further research.

The product is descriptive. It does not provide investment advice, forecast
outcomes, assign country ratings, or establish that one indicator caused
another to change.

## What the dashboard answers

For the initial period, 2010-2024, the dashboard lets an analyst:

- compare country-level changes in GDP per capita, life expectancy,
  unemployment, and population.
- filter the comparison by region and income group.
- start with a concise research shortlist, then switch to the complete country
  reference table when needed.
- choose an analysis period from the locally stored annual data, without a new
  API request.
- select one country or economy (Israel is the default when it is in scope) and
  inspect its annual time series.
- compare the selected country with the median of a clearly named comparison
  group: similar income level or the World Bank's broad regional classification,
  with its other member countries available in an expandable list.
- use a GDP-per-capita and life-expectancy scatter plot to explore patterns and
  outliers.
- inspect annual GDP-per-capita growth and secondary enrolment as supplementary
  context, without treating their lower-coverage values as core signals.
- use the **All country comparisons** view as the full reference table: it
  shows period changes for all six indicators, while clearly keeping the two
  supplementary measures outside research-signal logic.
- switch between dark and light presentation modes.
- see data quality and missing-value information before interpreting a result.

The dashboard treats a signal as a prompt for research, not a conclusion. For
example, high GDP-per-capita change paired with relatively low life-expectancy
improvement is a question worth investigating. It does not prove that growth
failed to improve wellbeing, or explain why a pattern occurred.

## Source and indicators

Source: [World Bank Indicators API documentation](https://datahelpdesk.worldbank.org/knowledgebase/articles/898581-api-basic-call-structures). No API key is required. The pipeline calls the technical API endpoint `https://api.worldbank.org/v2` and requests JSON responses.

### Data attribution and license

Data source: **World Bank, World Development Indicators (WDI)**, retrieved
through the World Bank Indicators API. WDI is listed by the World Bank Data
Catalog as [Creative Commons Attribution 4.0 (CC BY 4.0)](https://datacatalog.worldbank.org/search/dataset/0037712/world-development-indicators).
This project preserves the raw API responses and creates derived, descriptive
calculations. It does not imply World Bank endorsement. The source values,
metadata, and any applicable indicator-specific terms remain those of the
World Bank and its data providers.

### Visual asset attribution

The locally bundled country-flag SVGs in `assets/flags/` are derived from
[flag-icons](https://github.com/lipis/flag-icons), version 7.3.2, under its
[MIT License](https://github.com/lipis/flag-icons/blob/v7.3.2/LICENSE). They
are visual aids only and are not World Bank data.

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
output is promoted to a successful run. `data/processed/latest_run.json` is
updated only after the ETL's transformation and metrics steps both succeed.

## Local setup and run

Python 3.10 or later is recommended. Use a project virtual environment rather
than the global Anaconda `base` environment, so this project cannot change the
dependencies of unrelated tools.

After cloning the repository, run the following commands from its folder.
Replace `<repository-url>` and `<repository-folder>` with the submission
repository's URL and folder name.

```text
git clone <repository-url>
cd <repository-folder>
python -m venv .venv
```

Activate the environment:

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

```bash
# macOS / Linux
source .venv/bin/activate
```

Then install and run the product:

```text
pip install -r requirements.txt
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

## Continuous test check

GitHub Actions runs the same test command on every push and pull request with
Python 3.11. The workflow installs `requirements.txt` in a fresh environment.
It does not call the live World Bank API, write project data, or require any
credentials. Local execution remains the submission path described above.

## Processed data model

The main analytical table is:

```text
data/processed/<run_id>/country_year.csv
```

It has one row per `country_code` and `year`, with country metadata and a wide
column for each indicator. The initial full run contains 3,255 rows: 217
countries/economies × 15 years.

The metrics layer writes `country_progress_2010_2024.csv`. It contains each
country’s start value, end value, and change over the period for all six
indicators. GDP per capita, life expectancy, unemployment, and population are
the four core measures used for data-completeness status and research signals.
GDP growth and secondary enrolment are supplementary context measures only.

See [`outputs/data_dictionary.md`](outputs/data_dictionary.md) for the fields
used in the raw, country-year, and country-progress layers.

## Data quality and validation

The pipeline checks that:

- API responses use the expected JSON envelope and all reported pages are
  retrieved.
- the country-year key is unique.
- aggregate entities do not enter the country analysis.
- identifiers map to the country metadata.
- numeric values are valid for their indicator.
- missing values stay missing rather than becoming zero.

An invalid numeric observation is quarantined in the quality report, retained
in raw data for investigation, and left missing in the analytical output. Exact
duplicate records are retained once and reported. Conflicting duplicates are
quarantined and left missing. The run fails if the number of quarantined
observations exceeds 1% of country-year-indicator observations (with a minimum
tolerance of five records), or if structural checks such as unmapped entities
fail.

The successful 2026-09-08 run created 3,255 country-year rows with no duplicate
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
- The default dashboard window is 2010-2024. Its research-signal thresholds are
  calculated from observed countries in that window and documented in the
  processed metric-definitions file.

## Assumptions

- A World Bank entity classified as a country/economy is appropriate for the
  comparison population. Aggregate groups are excluded.
- Start-to-end changes over 2010-2024 are useful descriptive summaries, while
  the country view retains annual observations for further inspection.
- The research signals are intentionally transparent, simple screening rules.
  They are not risk scores or a ranking of country performance.
- The data source's published values and metadata are used as received. The
  pipeline validates structure and ranges but does not revise source values.

## What I would improve with more time

- Add peer-specific signal thresholds rather than using thresholds calculated
  across all observed countries.
- Add a scheduled refresh and historical run comparison to make data updates
  observable over time.
- Add integration tests that run against a recorded API fixture and browser
  smoke tests for the Streamlit interface.
- Add a documented workflow for reviewing and resolving quarantined records.

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
The complete user-visible transcripts are stored in `ai_transcript/`.
`AI_USAGE_INDEX.md` maps the assignment's AI requirements to the relevant
parts of those transcripts. The earlier `conversation_handoff.md` is retained
as supporting context and is clearly labelled as a handoff, not as a transcript.
