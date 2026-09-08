# Project status

Updated on 2026-09-08 after final validation.

## Submission status

Ready for submission. The repository contains the Python ETL, local raw and
processed data structure, Streamlit application, automated tests, README,
AI transcript material, and Git history.

## Latest validated run

- The World Bank API extraction completed successfully for 2010-2024.
- The run retained 217 countries and economies and excluded 78 aggregates.
- The transformation created 3,255 country-year rows.
- The quality status was `passed_with_missing_values`.
- The metrics layer identified 173 complete core comparisons, 9 GDP and life
  expectancy research signals, and 48 GDP and unemployment research signals.
- All 22 automated tests passed on 2026-09-08.
- GitHub Actions runs the unit-test suite in a fresh Python 3.11 environment
  for each push and pull request.

## Deliberate scope

The dashboard is a descriptive research-prioritization tool. It does not
provide investment advice, forecasts, causal conclusions, or country ratings.
The secondary-enrolment indicator is included as context only because its
coverage is lower than the four core measures.

The GitHub repository was confirmed publicly accessible on 2026-09-08.
