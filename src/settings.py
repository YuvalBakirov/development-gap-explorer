"""Central, reviewable configuration for the data pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Indicator:
    code: str
    column_name: str
    display_name: str
    required_for_core_analysis: bool


START_YEAR = 2010
END_YEAR = 2024
WORLD_BANK_SOURCE_ID = 2
WORLD_BANK_BASE_URL = "https://api.worldbank.org/v2"
PAGE_SIZE = 1_000
REQUEST_TIMEOUT_SECONDS = 45
MAX_RETRIES = 3
MAX_QUARANTINED_RECORD_SHARE = 0.01

INDICATORS = (
    Indicator(
        "NY.GDP.PCAP.KD",
        "gdp_per_capita_constant_2015_usd",
        "GDP per capita constant 2015 US dollars",
        True,
    ),
    Indicator(
        "NY.GDP.PCAP.KD.ZG",
        "gdp_per_capita_growth_annual_pct",
        "GDP per capita growth annual percent",
        False,
    ),
    Indicator(
        "SL.UEM.TOTL.ZS",
        "unemployment_total_pct",
        "Unemployment total percent of labor force",
        True,
    ),
    Indicator(
        "SP.DYN.LE00.IN",
        "life_expectancy_years",
        "Life expectancy at birth years",
        True,
    ),
    Indicator(
        "SP.POP.TOTL",
        "population_total",
        "Population total",
        True,
    ),
    Indicator(
        "SE.SEC.ENRR",
        "secondary_enrollment_gross_pct",
        "Secondary school enrollment gross percent",
        False,
    ),
)


def repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


def raw_data_root() -> Path:
    return repository_root() / "data" / "raw" / "world_bank"


def processed_data_root() -> Path:
    return repository_root() / "data" / "processed"
