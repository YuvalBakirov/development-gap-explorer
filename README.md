# Development Gap Explorer

This repository is currently at the raw-extraction foundation stage. The proposed
product helps development and policy analysts compare economic and social
progress across countries and identify cases that merit deeper research. It is
not an investment recommendation or forecasting product.

The reproducible World Bank Indicators API spike is documented in
`spike/README.md`. The raw extraction entry point is `etl.py`; it saves every
API page under a timestamped folder in `data/raw/world_bank/` and writes a run
manifest. Transformation into the analytical country-year table and the
Streamlit application have not yet been built.
