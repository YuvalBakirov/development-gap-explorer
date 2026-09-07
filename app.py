"""Streamlit dashboard for the Development Gap Explorer."""

from __future__ import annotations

import streamlit as st

from src.dashboard_data import (
    DashboardDataError,
    country_trend_rows,
    display_progress_rows,
    load_dashboard_data,
)


st.set_page_config(page_title="Development Gap Explorer", layout="wide")


SIGNAL_LABELS = {
    "high_gdp_growth_low_life_expectancy_gain": "High GDP growth with low life-expectancy gain",
    "gdp_growth_with_unemployment_increase": "GDP growth with unemployment increase",
    "insufficient_core_data": "Insufficient core data",
    "none": "No research signal",
}

INDICATOR_LABELS = {
    "NY.GDP.PCAP.KD": "GDP per capita (constant 2015 USD)",
    "NY.GDP.PCAP.KD.ZG": "GDP per capita growth (annual %)",
    "SL.UEM.TOTL.ZS": "Unemployment, total (% of labor force)",
    "SP.DYN.LE00.IN": "Life expectancy at birth (years)",
    "SP.POP.TOTL": "Population, total",
    "SE.SEC.ENRR": "Secondary enrollment, gross (%)",
}


def signal_options(row: dict[str, str]) -> list[str]:
    return row["research_signals"].split(";")


def main() -> None:
    st.title("Development Gap Explorer")
    st.caption(
        "A descriptive research-prioritization tool for development and policy analysts. "
        "It does not provide investment advice, forecasts, causal findings, or country ratings."
    )
    try:
        data = load_dashboard_data()
    except (DashboardDataError, OSError, ValueError) as exc:
        st.error(f"Dashboard data is unavailable: {exc}")
        st.info("Run `python etl.py` first, then refresh this page.")
        return

    progress_rows = data["progress_rows"]
    metrics_summary = data["metrics_summary"]
    quality = data["quality"]
    definitions = data["metric_definitions"]
    period = metrics_summary["period"]

    st.sidebar.header("Filters")
    regions = sorted({row["region_name"].strip() for row in progress_rows})
    income_groups = sorted({row["income_level_name"] for row in progress_rows})
    signals = sorted({signal for row in progress_rows for signal in signal_options(row)})
    chosen_regions = st.sidebar.multiselect("Region", regions)
    chosen_income_groups = st.sidebar.multiselect("Income group", income_groups)
    chosen_signals = st.sidebar.multiselect(
        "Research signal", signals, format_func=lambda signal: SIGNAL_LABELS.get(signal, signal)
    )

    filtered_rows = [
        row
        for row in progress_rows
        if (not chosen_regions or row["region_name"].strip() in chosen_regions)
        and (not chosen_income_groups or row["income_level_name"] in chosen_income_groups)
        and (not chosen_signals or any(signal in signal_options(row) for signal in chosen_signals))
    ]

    complete_filtered = sum(row["core_metrics_available"] == "True" for row in filtered_rows)
    life_signal_filtered = sum(
        "high_gdp_growth_low_life_expectancy_gain" in signal_options(row)
        for row in filtered_rows
    )
    unemployment_signal_filtered = sum(
        "gdp_growth_with_unemployment_increase" in signal_options(row)
        for row in filtered_rows
    )
    first, second, third, fourth = st.columns(4)
    first.metric("Countries / economies in scope", metrics_summary["country_count"])
    second.metric("Complete core comparisons (filtered)", complete_filtered)
    third.metric("GDP / life-expectancy signal (filtered)", life_signal_filtered)
    fourth.metric("GDP / unemployment signal (filtered)", unemployment_signal_filtered)

    st.subheader(f"Country comparison, {period['start_year']}–{period['end_year']}")
    st.write(f"{len(filtered_rows)} of {len(progress_rows)} countries / economies match the current filters.")
    st.dataframe(
        display_progress_rows(filtered_rows),
        hide_index=True,
        use_container_width=True,
        height=410,
        column_config={
            "Research signals": st.column_config.TextColumn("Research signals", width="large"),
            "GDP per capita change (%)": st.column_config.NumberColumn(
                "GDP per capita change (%)", format="%.2f"
            ),
            "Life expectancy change (years)": st.column_config.NumberColumn(
                "Life expectancy change (years)", format="%.2f"
            ),
            "Unemployment change (pp)": st.column_config.NumberColumn(
                "Unemployment change (pp)", format="%.2f"
            ),
            "Population change (%)": st.column_config.NumberColumn(
                "Population change (%)", format="%.2f"
            ),
        },
    )

    if not filtered_rows:
        st.warning("No countries match the selected filters.")
        return

    countries_by_label = {f"{row['country_name']} ({row['country_code']})": row for row in filtered_rows}
    selected_label = st.selectbox("Explore a country / economy", sorted(countries_by_label))
    selected = countries_by_label[selected_label]
    trend_rows = country_trend_rows(data["country_year_rows"], selected["country_code"])

    st.subheader(f"Annual trend: {selected['country_name']}")
    left, right = st.columns(2)
    with left:
        st.caption("GDP per capita, constant 2015 US dollars")
        st.line_chart(
            trend_rows,
            x="year",
            y="gdp_per_capita_constant_2015_usd",
            use_container_width=True,
        )
        st.caption("Life expectancy at birth (years)")
        st.line_chart(
            trend_rows,
            x="year",
            y="life_expectancy_years",
            use_container_width=True,
        )
    with right:
        st.caption("Unemployment, total (% of total labor force)")
        st.line_chart(
            trend_rows,
            x="year",
            y="unemployment_total_pct",
            use_container_width=True,
        )
        st.caption("Population")
        st.line_chart(
            trend_rows,
            x="year",
            y="population_total",
            use_container_width=True,
        )

    with st.expander("Method, data quality, and limits"):
        st.write(
            "The dashboard compares endpoint changes between the selected start "
            "and end years. A missing value remains missing; it is never treated as zero."
        )
        st.markdown("#### Data quality")
        st.write(
            f"This run produced {quality['expected_country_year_rows']:,} country-year "
            f"rows for {quality['country_count']} countries / economies. Its quality "
            f"status is **{quality['status']}**: no duplicate keys, unmapped entities, "
            "or invalid values were found."
        )
        expected_rows = quality["expected_country_year_rows"]
        coverage_rows = [
            {
                "Indicator": INDICATOR_LABELS.get(code, code),
                "Available observations": expected_rows - missing_count,
                "Coverage (%)": round((expected_rows - missing_count) / expected_rows * 100, 2),
            }
            for code, missing_count in quality["missing_observations_by_indicator"].items()
        ]
        st.dataframe(
            coverage_rows,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Coverage (%)": st.column_config.NumberColumn("Coverage (%)", format="%.2f"),
            },
        )

        signal_definition = definitions["high_gdp_growth_low_life_expectancy_gain"]
        st.markdown("#### Research signals")
        st.markdown(
            f"- **GDP growth + low life-expectancy gain:** GDP per capita changed by at "
            f"least {signal_definition['gdp_threshold']:.2f}% and life expectancy changed "
            f"by no more than {signal_definition['life_expectancy_threshold']:.2f} years. "
            "These are data-derived thresholds for this 2010–2024 comparison.\n"
            "- **GDP growth + unemployment increase:** GDP per capita increased while the "
            "unemployment rate also increased.\n"
            "- **Missing core data:** one or more of the core endpoint comparisons is unavailable."
        )
        st.info(definitions["limitation"])


if __name__ == "__main__":
    main()
