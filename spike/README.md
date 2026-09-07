# World Bank API feasibility spike

This spike validates the proposed data source before the full ETL and
Streamlit application are built.

Run from the repository root with Python 3.10 or newer:

```text
python spike/api_feasibility_spike.py
```

The script uses only the Python standard library. It retrieves World Bank
country metadata and the six proposed indicators for 2010-2024, deliberately
uses a page size of 1,000 to exercise pagination, stores page-one raw samples,
and writes measured summaries under `data/processed/feasibility_spike/`.

Countries and aggregate entities are separated using the current World Bank
country metadata. A country/economy has a region ID other than `NA`; aggregate
entities use `region.id = "NA"` and `region.value = "Aggregates"`.
