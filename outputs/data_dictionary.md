# Data dictionary

This document describes the analytical files produced by a successful ETL run.
The exact run directory is selected by `data/processed/latest_run.json`.

## Raw API snapshot

`data/raw/world_bank/<run_id>/` holds the unmodified JSON pages returned by
the World Bank API and `manifest.json`. The manifest records the extraction
time, queried period, source resource, page counts, and API-reported totals.
Raw files are evidence for reproducibility. The dashboard does not read them.

## Country-year table

`data/processed/<run_id>/country_year.csv` is the canonical analytical model:
one row for one `country_code` and one `year`.

| Field group | Meaning |
| --- | --- |
| `country_code`, `country_name` | Country/economy identifier and label from World Bank metadata. |
| `region_*`, `income_*` | World Bank's own regional and income-group metadata. |
| `year` | Observation year. |
| `gdp_per_capita_constant_2015_usd` | GDP per capita in constant 2015 US dollars. |
| `gdp_per_capita_growth_annual_pct` | Annual GDP-per-capita growth rate, supplementary. |
| `unemployment_total_pct` | Unemployment share of the total labor force. |
| `life_expectancy_years` | Life expectancy at birth, in years. |
| `population_total` | Total population. |
| `secondary_enrollment_gross_pct` | Secondary school gross-enrolment rate, supplementary. |

Values absent from the API remain empty in the CSV. They are never converted
to zero or estimated.

## Country-progress metrics

`data/processed/<run_id>/country_progress_<start>_<end>.csv` has one row per
country/economy and converts the selected endpoints into descriptive changes.

| Field group | Meaning |
| --- | --- |
| `*_start`, `*_end` | Source values at the selected start and end years. |
| `*_change_pct` | Percentage change between non-zero start and end values, used for GDP per capita and population. |
| `*_change_pp` | End-year rate minus start-year rate, in percentage points. Used for unemployment, annual GDP-per-capita growth, and secondary enrolment. The latter two are supplementary context only. |
| `life_expectancy_change_years` | Difference in years between the two endpoints. |
| `core_metrics_available` | `true` only when every core endpoint comparison needed by the dashboard is available. |
| `missing_core_metrics` | The unavailable core measure names, if any. |
| `research_signals` | Transparent descriptive prompts for follow-up research, not scores, rankings, or causal findings. |

Definitions and data-derived thresholds for each period are written alongside
the metrics in `metric_definitions_<start>_<end>.json`. Data-quality counts and
quarantine information are in `data_quality_report.json`.
