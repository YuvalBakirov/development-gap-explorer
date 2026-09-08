"""Streamlit dashboard for the Development Gap Explorer."""

from __future__ import annotations

import altair as alt
import streamlit as st
from html import escape
from typing import Any

from src.dashboard_data import (
    DashboardDataError,
    country_trend_rows,
    display_summary_rows,
    load_dashboard_data,
    peer_comparison,
)
from src.metrics import (
    GDP_PER_CAPITA_INCREASE_WITH_UNEMPLOYMENT_INCREASE,
    HIGH_GDP_PER_CAPITA_CHANGE_LOW_LIFE_EXPECTANCY_GAIN,
    INSUFFICIENT_CORE_DATA,
    MetricsError,
    calculate_country_progress,
)


st.set_page_config(page_title="Development Gap Explorer", layout="wide")


SIGNAL_LABELS = {
    HIGH_GDP_PER_CAPITA_CHANGE_LOW_LIFE_EXPECTANCY_GAIN: "High GDP-per-capita change + low life-expectancy gain",
    GDP_PER_CAPITA_INCREASE_WITH_UNEMPLOYMENT_INCREASE: "GDP-per-capita increase + unemployment increase",
    INSUFFICIENT_CORE_DATA: "Missing core data",
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


def apply_theme(appearance: str) -> dict[str, str]:
    """Apply a small, explicit dashboard palette without relying on browser settings."""
    palettes = {
        "Dark": {
            "background": "#0e1117",
            "surface": "#171b26",
            "text": "#f7f9fc",
            "muted": "#b9c2d0",
            "grid": "#394150",
            "border": "#394150",
            "input": "#262730",
            "header": "#1a1c24",
            "line": "#6bb9f0",
            "other": "#8aa5bf",
            "selected": "#f26b38",
        },
        "Light": {
            "background": "#ffffff",
            "surface": "#f4f6f9",
            "text": "#17202a",
            "muted": "#4d5b6b",
            "grid": "#d9e0e8",
            "border": "#cbd5e1",
            "input": "#ffffff",
            "header": "#edf2f7",
            "line": "#2877a8",
            "other": "#527a9b",
            "selected": "#c95628",
        },
    }
    palette = palettes[appearance]
    st.markdown(
        f"""
        <style>
        :root {{ color-scheme: {appearance.lower()}; }}
        .stApp, [data-testid="stAppViewContainer"], [data-testid="stAppViewContainer"] > .main {{
          background: {palette['background']}; color: {palette['text']};
        }}
        [data-testid="stSidebar"], [data-testid="stSidebar"] > div {{
          background: {palette['surface']};
        }}
        .stApp h1, .stApp h2, .stApp h3, .stApp p, .stApp label {{ color: {palette['text']}; }}
        .stApp h1 {{ letter-spacing: -0.025em; }}
        .stApp [data-testid="stCaptionContainer"] * {{ color: {palette['muted']}; }}
        [data-baseweb="select"], [data-baseweb="select"] > div,
        [data-baseweb="select"] > div > div, [data-baseweb="base-input"] > div,
        [data-baseweb="input"] > div {{
          background-color: {palette['input']} !important;
          border-color: {palette['border']} !important;
        }}
        [data-baseweb="select"] *, [data-baseweb="base-input"] input,
        [data-baseweb="input"] input {{ color: {palette['text']} !important; }}
        [data-baseweb="select"] svg {{ fill: {palette['muted']} !important; }}
        [data-testid="stMetric"] {{
          background: {palette['surface']}; border: 1px solid {palette['border']};
          border-radius: 0.55rem; border-top: 3px solid {palette['selected']};
          padding: 0.6rem 0.75rem;
        }}
        .dashboard-table-wrap {{ max-height: 410px; overflow: auto; border: 1px solid {palette['border']};
          border-radius: 0.55rem; background: {palette['input']}; }}
        table.dashboard-table {{ width: 100%; border-collapse: collapse; font-size: 0.88rem; }}
        .dashboard-table th {{ position: sticky; top: 0; background: {palette['header']}; color: {palette['text']};
          text-align: left; font-weight: 650; padding: 0.7rem 0.75rem; border-bottom: 1px solid {palette['border']}; }}
        .dashboard-table td {{ color: {palette['text']}; padding: 0.62rem 0.75rem;
          border-bottom: 1px solid {palette['border']}; vertical-align: top; }}
        .dashboard-table tbody tr:nth-child(even) {{ background: {palette['surface']}; }}
        .dashboard-table tbody tr:hover {{ background: {palette['header']}; }}
        .dashboard-table td.number {{ text-align: right; font-variant-numeric: tabular-nums; }}
        </style>
        """,
        unsafe_allow_html=True,
    )
    return palette


def signal_options(row: dict[str, object]) -> list[str]:
    return str(row["research_signals"]).split(";")


def render_trend_chart(
    title: str,
    explanation: str,
    trend_rows: list[dict[str, object]],
    measure: str,
    palette: dict[str, str],
) -> None:
    """Show an annual trend or a clear availability message, never a blank chart."""
    st.caption(title)
    st.caption(explanation)
    available_rows = [row for row in trend_rows if row[measure] is not None]
    if not available_rows:
        st.info("No annual observation is available for this measure in the selected country / economy.")
        return
    chart = (
        alt.Chart(alt.Data(values=available_rows))
        .mark_line(color=palette["line"], strokeWidth=2.5, point=True)
        .encode(
            x=alt.X("year:O", title="Year"),
            y=alt.Y(f"{measure}:Q", title=None),
            tooltip=[alt.Tooltip("year:O", title="Year"), alt.Tooltip(f"{measure}:Q", title=title, format=",.2f")],
        )
        .properties(height=240)
        .configure(background=palette["background"])
        .configure_view(stroke=palette["grid"])
        .configure_axis(labelColor=palette["text"], titleColor=palette["text"], gridColor=palette["grid"])
    )
    st.altair_chart(chart, use_container_width=True)


def format_table_value(value: object) -> tuple[str, bool]:
    """Render a value safely for a lightweight stakeholder-facing HTML table."""
    if value is None or value == "":
        return "—", False
    if isinstance(value, float):
        return f"{value:,.2f}", True
    if isinstance(value, int):
        return f"{value:,}", True
    return str(value), False


def render_table(rows: list[dict[str, Any]], max_height: int = 410) -> None:
    """Render a compact, theme-controlled table without Streamlit grid theme leakage."""
    if not rows:
        st.info("No rows are available for this view.")
        return
    columns = list(rows[0])
    header_html = "".join(f"<th>{escape(column)}</th>" for column in columns)
    body_html = []
    for row in rows:
        cells = []
        for column in columns:
            value, is_number = format_table_value(row.get(column))
            css_class = ' class="number"' if is_number else ""
            cells.append(f"<td{css_class}>{escape(value)}</td>")
        body_html.append(f"<tr>{''.join(cells)}</tr>")
    st.markdown(
        f'<div class="dashboard-table-wrap" style="max-height: {max_height}px;"><table class="dashboard-table">'
        f"<thead><tr>{header_html}</tr></thead><tbody>{''.join(body_html)}</tbody></table></div>",
        unsafe_allow_html=True,
    )


def main() -> None:
    appearance = st.sidebar.radio("Appearance", ("Dark", "Light"), horizontal=True)
    palette = apply_theme(appearance)
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

    quality = data["quality"]

    st.sidebar.header("Filters")
    available_years = sorted({int(row["year"]) for row in data["country_year_rows"]})
    selected_period = st.sidebar.slider(
        "Analysis period",
        min_value=available_years[0],
        max_value=available_years[-1],
        value=(available_years[0], available_years[-1]),
        step=1,
        help="The dashboard recalculates descriptive changes and research-signal thresholds from the local country-year data. It does not call the API.",
    )
    try:
        progress_rows, definitions, metrics_summary = calculate_country_progress(
            data["run_directory"] / "country_year.csv", *selected_period
        )
    except MetricsError as exc:
        st.error(f"Metrics could not be calculated for this period: {exc}")
        return
    period = metrics_summary["period"]
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

    complete_filtered = sum(bool(row["core_metrics_available"]) for row in filtered_rows)
    life_signal_filtered = sum(
        HIGH_GDP_PER_CAPITA_CHANGE_LOW_LIFE_EXPECTANCY_GAIN in signal_options(row)
        for row in filtered_rows
    )
    unemployment_signal_filtered = sum(
        GDP_PER_CAPITA_INCREASE_WITH_UNEMPLOYMENT_INCREASE in signal_options(row)
        for row in filtered_rows
    )
    first, second, third, fourth = st.columns(4)
    first.metric("Countries / economies in scope", len(filtered_rows))
    second.metric("Complete core comparisons (filtered)", complete_filtered)
    third.metric("GDP / life-expectancy signal (filtered)", life_signal_filtered)
    fourth.metric("GDP / unemployment signal (filtered)", unemployment_signal_filtered)

    st.subheader(f"Country comparison, {period['start_year']}–{period['end_year']}")
    st.caption(
        "Start with research signals to see descriptive patterns worth follow-up. Missing core data is shown "
        "separately as a data-quality flag; switch to all comparisons for the complete reference table."
    )
    table_view = st.radio(
        "Table view",
        ("Research signals", "Missing core data", "All country comparisons"),
        horizontal=True,
        help="Research signals are descriptive prompts for further investigation. Missing core data is kept separate because it is a data-quality flag, not an analytical conclusion.",
    )
    if table_view == "Research signals":
        table_rows = [
            row
            for row in filtered_rows
            if any(
                signal not in {"none", INSUFFICIENT_CORE_DATA}
                for signal in signal_options(row)
            )
        ]
    elif table_view == "Missing core data":
        table_rows = [
            row for row in filtered_rows if INSUFFICIENT_CORE_DATA in signal_options(row)
        ]
    else:
        table_rows = filtered_rows
    st.write(
        f"{len(table_rows)} shown of {len(filtered_rows)} countries / economies matching the current filters."
    )
    render_table(display_summary_rows(table_rows))

    if not filtered_rows:
        st.warning("No countries match the selected filters.")
        return

    countries_by_label = {f"{row['country_name']} ({row['country_code']})": row for row in filtered_rows}
    country_labels = sorted(countries_by_label)
    default_country_index = next(
        (
            index
            for index, label in enumerate(country_labels)
            if countries_by_label[label]["country_code"] == "ISR"
        ),
        next(
            (
                index
                for index, label in enumerate(country_labels)
                if countries_by_label[label]["core_metrics_available"]
            ),
            0,
        ),
    )
    selected_label = st.selectbox(
        "Explore a country / economy", country_labels, index=default_country_index
    )
    selected = countries_by_label[selected_label]
    trend_rows = country_trend_rows(data["country_year_rows"], selected["country_code"])
    if selected["research_signals"] != "none":
        st.info(f"Research note for {selected['country_name']}: {selected['research_signal_explanation']}")
    else:
        st.caption(
            f"No descriptive research signal was triggered for {selected['country_name']} in this period."
        )

    grouping_options = {
        "Similar income level": "Income group",
        "World Bank regional classification": "Region",
    }
    grouping_label = st.selectbox(
        "Comparison group",
        tuple(grouping_options),
        help="Compare the selected country with the median of other countries in one meaningful group. This is context for research, not a ranking.",
    )
    peer_grouping = grouping_options[grouping_label]
    peer = peer_comparison(progress_rows, selected["country_code"], peer_grouping)
    st.subheader("Comparison group")
    st.info(
        f"**{selected['country_name']}** is compared with **{peer['peer_count']} other countries / economies** "
        f"in the selected **{grouping_label.lower()}**: **{peer['group_name']}**. "
        "Results use the median of the available observations; this is context for research, not a ranking."
    )
    if peer_grouping == "Region":
        st.caption(
            "This is the World Bank's own broad regional classification, not a custom geographic definition."
        )
    with st.expander(f"Show the {peer['peer_count']} other countries / economies in this comparison group"):
        st.markdown("\n".join(f"- {country_name}" for country_name in peer["member_names"]))
    st.subheader("Comparison results")
    peer_table_rows = [
        {
            "Metric": row["Metric"],
            "Selected country": row["Selected country"],
            "Comparison-group median": row["Peer median"],
            "Difference vs group median": row["Difference from peer median"],
            "Countries with data": row["Peer observations"],
        }
        for row in peer["metrics"]
    ]
    render_table(peer_table_rows, max_height=260)

    scatter_rows = [
        {
            "Country": row["country_name"],
            "GDP per capita change (%)": row["gdp_per_capita_change_pct"],
            "Life expectancy change (years)": row["life_expectancy_change_years"],
            "Highlight": "Selected country" if row["country_code"] == selected["country_code"] else "Other countries",
            "Research signals": "; ".join(
                SIGNAL_LABELS.get(signal, signal) for signal in signal_options(row)
            ),
        }
        for row in filtered_rows
        if row["gdp_per_capita_change_pct"] is not None
        and row["life_expectancy_change_years"] is not None
    ]
    st.subheader("GDP per capita and life expectancy comparison")
    st.caption(
        "Each point is a country / economy in the filtered comparison. Right means higher GDP-per-capita change; "
        "up means a larger life-expectancy change. The plot helps locate patterns and outliers; it does not prove causality."
    )
    if (
        selected["gdp_per_capita_change_pct"] is None
        or selected["life_expectancy_change_years"] is None
    ):
        missing_for_scatter = []
        if selected["gdp_per_capita_change_pct"] is None:
            missing_for_scatter.append("GDP per capita")
        if selected["life_expectancy_change_years"] is None:
            missing_for_scatter.append("life expectancy")
        st.info(
            f"{selected['country_name']} is not highlighted in this plot because its selected-period "
            f"{', '.join(missing_for_scatter)} comparison is unavailable. Missing data is not replaced with zero."
        )
    if scatter_rows:
        scatter = (
            alt.Chart(alt.Data(values=scatter_rows))
            .mark_circle(size=80, opacity=0.75)
            .encode(
                x=alt.X("GDP per capita change (%):Q", title="GDP per capita change (%)"),
                y=alt.Y("Life expectancy change (years):Q", title="Life expectancy change (years)"),
                color=alt.Color(
                    "Highlight:N",
                    scale=alt.Scale(
                        domain=["Other countries", "Selected country"],
                        range=[palette["other"], palette["selected"]],
                    ),
                ),
                tooltip=[
                    alt.Tooltip("Country:N"),
                    alt.Tooltip("GDP per capita change (%):Q", format=".2f"),
                    alt.Tooltip("Life expectancy change (years):Q", format=".2f"),
                    alt.Tooltip("Research signals:N"),
                ],
            )
            .properties(height=380)
            .configure(background=palette["background"])
            .configure_view(stroke=palette["grid"])
            .configure_axis(
                labelColor=palette["text"], titleColor=palette["text"], gridColor=palette["grid"]
            )
            .configure_legend(labelColor=palette["text"], titleColor=palette["text"])
        )
        st.altair_chart(scatter, use_container_width=True)
    else:
        st.info("The current filters contain no countries with both scatter-plot measures available.")

    st.subheader(f"Annual trend: {selected['country_name']}")
    left, right = st.columns(2)
    with left:
        render_trend_chart(
            "GDP per capita, constant 2015 US dollars",
            "Shows the inflation-adjusted annual level. An upward line means output per person increased in real terms.",
            trend_rows,
            "gdp_per_capita_constant_2015_usd",
            palette,
        )
        render_trend_chart(
            "Life expectancy at birth (years)",
            "Shows the average expected lifespan at birth. It is descriptive and does not identify a cause of change.",
            trend_rows,
            "life_expectancy_years",
            palette,
        )
    with right:
        render_trend_chart(
            "Unemployment, total (% of total labor force)",
            "Shows the share of the labor force without work. A change is measured in percentage points, not percent growth.",
            trend_rows,
            "unemployment_total_pct",
            palette,
        )
        render_trend_chart(
            "Population",
            "Shows total population. It provides context for the other country-level measures; it is not a research signal by itself.",
            trend_rows,
            "population_total",
            palette,
        )

    with st.expander("Supplementary indicators (not used for core research signals)"):
        st.caption(
            "These series add context but are not used to flag countries: annual GDP-per-capita growth is a year-to-year rate, "
            "and secondary enrolment has lower coverage (66.27% in this extract)."
        )
        supplementary_left, supplementary_right = st.columns(2)
        with supplementary_left:
            render_trend_chart(
                "GDP per capita growth (annual %)",
                "Shows the annual real growth rate rather than the endpoint change used in the core comparison.",
                trend_rows,
                "gdp_per_capita_growth_annual_pct",
                palette,
            )
        with supplementary_right:
            render_trend_chart(
                "Secondary enrolment, gross (%)",
                "Shows enrolled students of secondary-school age and may exceed 100%; missing observations are common in this series.",
                trend_rows,
                "secondary_enrollment_gross_pct",
                palette,
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
            f"status is **{quality['status']}**."
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
        render_table(coverage_rows, max_height=280)

        signal_definition = definitions[HIGH_GDP_PER_CAPITA_CHANGE_LOW_LIFE_EXPECTANCY_GAIN]
        st.markdown("#### Research signals")
        st.markdown(
            f"- **GDP-per-capita change + low life-expectancy gain:** GDP per capita changed by at "
            f"least {signal_definition['gdp_threshold']:.2f}% and life expectancy changed "
            f"by no more than {signal_definition['life_expectancy_threshold']:.2f} years. "
            "These are data-derived thresholds for the selected comparison period.\n"
            "- **GDP-per-capita increase + unemployment increase:** GDP per capita increased while the "
            "unemployment rate also increased.\n"
            "- **Missing core data:** one or more of the core endpoint comparisons is unavailable."
        )
        st.info(definitions["limitation"])


if __name__ == "__main__":
    main()
