"""Streamlit dashboard for the Development Gap Explorer."""

from __future__ import annotations

import altair as alt
import streamlit as st
from base64 import b64encode
from html import escape
from pathlib import Path
from typing import Any

from src.dashboard_data import (
    DashboardDataError,
    country_trend_rows,
    display_all_comparison_rows,
    display_missing_core_rows,
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


st.set_page_config(
    page_title="Development Gap Explorer",
    page_icon="assets/development-gap-explorer-icon.png",
    layout="wide",
)


SIGNAL_LABELS = {
    HIGH_GDP_PER_CAPITA_CHANGE_LOW_LIFE_EXPECTANCY_GAIN: "High GDP-per-capita change + low life-expectancy gain",
    GDP_PER_CAPITA_INCREASE_WITH_UNEMPLOYMENT_INCREASE: "GDP-per-capita increase + unemployment increase",
    INSUFFICIENT_CORE_DATA: "Some core data unavailable",
    "none": "No research signal",
}

SIGNAL_PLAIN_LANGUAGE = {
    HIGH_GDP_PER_CAPITA_CHANGE_LOW_LIFE_EXPECTANCY_GAIN: "GDP per capita rose strongly while life expectancy gained relatively little.",
    GDP_PER_CAPITA_INCREASE_WITH_UNEMPLOYMENT_INCREASE: "GDP per capita and unemployment both increased.",
}

INDICATOR_LABELS = {
    "NY.GDP.PCAP.KD": "GDP per capita (constant 2015 USD)",
    "NY.GDP.PCAP.KD.ZG": "GDP per capita growth (annual %)",
    "SL.UEM.TOTL.ZS": "Unemployment, total (% of labor force)",
    "SP.DYN.LE00.IN": "Life expectancy at birth (years)",
    "SP.POP.TOTL": "Population, total",
    "SE.SEC.ENRR": "Secondary enrollment, gross (%)",
}

COVERAGE_CHART_LABELS = {
    "GDP per capita (constant 2015 USD)": "GDP per capita (constant USD)",
    "GDP per capita growth (annual %)": "GDP per capita growth (%)",
    "Unemployment, total (% of labor force)": "Unemployment rate (%)",
    "Life expectancy at birth (years)": "Life expectancy (years)",
    "Population, total": "Population",
    "Secondary enrollment, gross (%)": "Secondary enrolment (%)",
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
        .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
        .stApp p, .stApp label {{ color: {palette['text']} !important; }}
        .stApp h1 {{ letter-spacing: -0.025em; }}
        .stApp [data-testid="stCaptionContainer"] * {{ color: {palette['muted']}; }}
        [data-baseweb="select"], [data-baseweb="select"] > div,
        [data-baseweb="select"] > div > div, [data-baseweb="base-input"] > div,
        [data-baseweb="input"] > div {{
          background-color: {palette['input']} !important;
          border-color: {palette['border']} !important;
        }}
        [data-baseweb="select"] > div, [data-baseweb="base-input"] > div,
        [data-baseweb="input"] > div {{
          border: 1px solid {palette['border']} !important;
          border-radius: 0.45rem !important;
          box-shadow: 0 1px 2px rgba(15, 23, 42, 0.08) !important;
        }}
        [data-baseweb="select"] *, [data-baseweb="base-input"] input,
        [data-baseweb="input"] input {{ color: {palette['text']} !important; }}
        [data-baseweb="select"] svg {{ fill: {palette['muted']} !important; }}
        [data-baseweb="popover"], [data-baseweb="menu"], [role="listbox"] {{
          background: {palette['input']} !important; color: {palette['text']} !important;
          border: 1px solid {palette['border']} !important;
        }}
        [role="option"] {{ background: {palette['input']} !important; color: {palette['text']} !important; }}
        [role="option"]:hover, [role="option"][aria-selected="true"] {{ background: {palette['surface']} !important; }}
        header, header[data-testid="stHeader"], [data-testid="stHeader"],
        header > div, [data-testid="stHeader"] > div {{
          background: {palette['background']} !important;
          border-bottom: 1px solid {palette['border']} !important;
        }}
        [data-testid="stHeader"] *, [data-testid="stToolbar"] * {{ color: {palette['text']} !important; }}
        [data-testid="stExpander"], div[data-testid="stExpander"] details {{
          border: 1px solid {palette['border']} !important;
          border-radius: 0.55rem !important;
          background: {palette['input']} !important;
          overflow: hidden;
          box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05) !important;
        }}
        [data-testid="stExpander"] summary, div[data-testid="stExpander"] summary {{
          background: {palette['surface']} !important;
          color: {palette['text']} !important;
          font-weight: 650 !important;
          padding: 0.1rem 0.2rem;
        }}
        [data-testid="stExpander"] summary:hover, div[data-testid="stExpander"] summary:hover {{
          background: {palette['header']} !important;
        }}
        [data-testid="stExpanderDetails"] {{
          background: {palette['input']} !important;
          border-top: 1px solid {palette['border']} !important;
        }}
        [data-testid="stVegaLiteChart"] {{
          border: 1px solid {palette['border']} !important;
          border-radius: 0.55rem !important;
          background: {palette['input']} !important;
          padding: 0.3rem !important;
          overflow: hidden;
        }}
        .welcome-card {{
          background: {palette['surface']}; border: 1px solid {palette['border']};
          border-left: 4px solid {palette['selected']}; border-radius: 0.55rem;
          padding: 0.85rem 1rem; margin: 0.6rem 0 1rem;
        }}
        .welcome-card strong {{ color: {palette['text']}; display: block; margin-bottom: 0.18rem; }}
        .welcome-card span {{ color: {palette['muted']}; font-size: 0.92rem; }}
        .stApp h2 {{ margin-top: 1.55rem !important; margin-bottom: 0.7rem !important; }}
        .stApp h3 {{ margin-top: 1.25rem !important; margin-bottom: 0.55rem !important; }}
        .chart-title {{
          color: {palette['text']}; font-size: 1rem; font-weight: 700;
          text-align: center; margin: 0.35rem 0 0.2rem;
        }}
        .period-pill {{
          display: inline-block; color: {palette['line']}; background: rgba(40, 119, 168, 0.10);
          border: 0; border-radius: 0.4rem; padding: 0.25rem 0.55rem;
          font-size: 1.02rem; font-weight: 800; letter-spacing: 0.015em;
          line-height: 1.25; margin: 0 0 0.72rem;
        }}
        .dynamic-number {{ color: {palette['line']}; font-weight: 800; text-decoration: none; }}
        .selected-name {{ color: {palette['selected']}; font-weight: 800; }}
        .comparison-basis {{ color: {palette['text']}; font-size: 1rem; font-weight: 650;
          border-left: 3px solid {palette['line']}; padding: 0.38rem 0 0.38rem 0.65rem;
          margin: 0.45rem 0 0.7rem; }}
        .comparison-basis strong {{ color: {palette['line']}; font-weight: 850; }}
        .research-signal-note {{ background: {palette['surface']}; color: {palette['text']};
          border: 1px solid {palette['border']}; border-left: 4px solid {palette['selected']};
          border-radius: 0.45rem; padding: 0.68rem 0.8rem; margin: 0.6rem 0 0.8rem; }}
        .research-signal-note .label {{ color: {palette['selected']}; font-size: 0.77rem;
          font-weight: 850; letter-spacing: 0.07em; text-transform: uppercase; display: block; margin-bottom: 0.18rem; }}
        .research-signal-note strong {{ color: {palette['text']}; font-weight: 850; }}
        .table-context-note {{ background: {palette['surface']}; color: {palette['text']};
          border-left: 3px solid {palette['line']}; border-radius: 0.35rem;
          padding: 0.48rem 0.65rem; margin: 0.65rem 0; font-size: 0.91rem; white-space: pre-line; }}
        .disclaimer-star {{ color: #d64545; font-weight: 900; margin-right: 0.22rem; }}
        .country-flag-preview {{ margin-top: 1.6rem; text-align: center; }}
        .country-flag-preview img {{ width: 34px; height: 25px; object-fit: cover; border: 1px solid {palette['border']};
          border-radius: 0.18rem; box-shadow: 0 1px 2px rgba(15, 23, 42, 0.14); }}
        .country-flag-list {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(185px, 1fr));
          gap: 0.35rem 0.75rem; padding: 0.1rem 0; }}
        .country-flag-item {{ color: {palette['text']}; display: flex; align-items: center; gap: 0.38rem; }}
        .country-flag-item img {{ width: 22px; height: 16px; object-fit: cover; border: 1px solid {palette['border']};
          border-radius: 0.14rem; flex: 0 0 auto; }}
        .visual-heading {{ color: {palette['text']}; font-size: 1.12rem; font-weight: 800;
          margin: 1.25rem 0 0.7rem; }}
        .supplementary-note {{ color: {palette['muted']}; font-size: 0.9rem; margin: 0.15rem 0 0.75rem; }}
        .supplementary-note span {{ color: #d64545; font-size: 1.1rem; font-weight: 800; margin-right: 0.28rem; }}
        .stTabs [data-baseweb="tab-list"] {{
          gap: 0.45rem; border-bottom: 1px solid {palette['border']}; padding-bottom: 0.45rem;
        }}
        .stTabs [data-baseweb="tab"] {{
          color: {palette['muted']} !important; background: {palette['surface']} !important;
          border: 1px solid {palette['border']} !important; border-radius: 0.45rem !important;
          padding: 0.5rem 0.85rem !important;
        }}
        .stTabs [aria-selected="true"] {{
          color: {palette['text']} !important; background: {palette['input']} !important;
          border-color: {palette['selected']} !important; box-shadow: inset 0 -2px 0 {palette['selected']};
        }}
        .stTabs [data-baseweb="tab-highlight"] {{ background-color: {palette['selected']} !important; }}
        [data-testid="stMetric"] {{
          background: {palette['surface']}; border: 1px solid {palette['border']};
          border-radius: 0.55rem; border-top: 3px solid {palette['selected']};
          padding: 0.65rem 0.8rem; text-align: center;
        }}
        [data-testid="stMetricLabel"], [data-testid="stMetricValue"] {{
          justify-content: center !important; text-align: center !important;
        }}
        [data-testid="stMetricLabel"] > div, [data-testid="stMetricValue"] > div {{
          justify-content: center !important; text-align: center !important;
        }}
        .dashboard-table-wrap {{ max-height: 410px; overflow: auto; border: 1px solid {palette['border']};
          border-radius: 0.55rem; background: {palette['input']}; }}
        table.dashboard-table {{ width: 100%; border-collapse: collapse; font-size: 0.88rem; }}
        .dashboard-table th {{ position: sticky; top: 0; background: {palette['header']}; color: {palette['text']};
          text-align: center; font-weight: 650; padding: 0.7rem 0.75rem; border-bottom: 1px solid {palette['border']}; }}
        .dashboard-table td {{ color: {palette['text']}; padding: 0.62rem 0.75rem;
          border-bottom: 1px solid {palette['border']}; vertical-align: top; text-align: center; }}
        .dashboard-table th:first-child, .dashboard-table td:first-child {{ text-align: left; }}
        .dashboard-table tbody tr:nth-child(even) {{ background: {palette['surface']}; }}
        .dashboard-table tbody tr:hover {{ background: {palette['header']}; }}
        .dashboard-table td.number {{ text-align: center; font-variant-numeric: tabular-nums; }}
        .dashboard-table td.selected-cell {{ color: {palette['selected']}; font-weight: 850;
          background: rgba(201, 86, 40, 0.09); }}
        .dashboard-table td.difference-cell {{ color: {palette['line']}; font-weight: 800;
          background: rgba(40, 119, 168, 0.07); }}
        .dashboard-table td.signal-cell {{ color: {palette['selected']}; font-weight: 700; }}
        .dashboard-table-wrap {{ scrollbar-color: {palette['muted']} {palette['surface']}; scrollbar-width: auto; }}
        .dashboard-table-wrap::-webkit-scrollbar {{ width: 13px; height: 13px; }}
        .dashboard-table-wrap::-webkit-scrollbar-track {{ background: {palette['surface']}; }}
        .dashboard-table-wrap::-webkit-scrollbar-thumb {{ background: {palette['muted']}; border: 3px solid {palette['surface']}; border-radius: 999px; }}
        .dashboard-table-wrap::-webkit-scrollbar-corner {{ background: {palette['surface']}; }}
        .section-kicker {{ color: {palette['selected']}; font-weight: 700; font-size: 0.8rem;
          letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 0.15rem; }}
        </style>
        """,
        unsafe_allow_html=True,
    )
    return palette


def signal_options(row: dict[str, object]) -> list[str]:
    return str(row["research_signals"]).split(";")


def country_flag_path(country_code: str, iso2_codes: dict[str, str]) -> Path | None:
    """Locate a bundled SVG flag from World Bank's stored ISO-2 metadata."""
    iso2_code = iso2_codes.get(country_code, "")
    if len(iso2_code) != 2 or not iso2_code.isalpha():
        return None
    path = Path("assets") / "flags" / f"{iso2_code.lower()}.svg"
    return path if path.exists() else None


def country_flag_html(country_code: str, country_name: str, iso2_codes: dict[str, str]) -> str:
    """Render a real local SVG flag next to an escaped country name."""
    image_html = country_flag_image_html(country_code, iso2_codes)
    return f'<span class="country-flag-item">{image_html}<span>{escape(country_name)}</span></span>'


def country_flag_image_html(country_code: str, iso2_codes: dict[str, str]) -> str:
    """Render a real local SVG flag with no text fallback."""
    path = country_flag_path(country_code, iso2_codes)
    if path is None:
        return ""
    encoded_svg = b64encode(path.read_bytes()).decode("ascii")
    return f'<img alt="" src="data:image/svg+xml;base64,{encoded_svg}">'


def country_option_label(row: dict[str, Any], iso2_codes: dict[str, str]) -> str:
    """Keep the native selectbox searchable while retaining the stable World Bank code."""
    del iso2_codes
    return f"{row['country_name']} ({row['country_code']})"


def render_trend_chart(
    title: str,
    explanation: str,
    trend_rows: list[dict[str, object]],
    measure: str,
    palette: dict[str, str],
) -> None:
    """Show an annual trend or a clear availability message, never a blank chart."""
    st.markdown(f'<div class="chart-title">{escape(title)}</div>', unsafe_allow_html=True)
    st.caption(explanation)
    available_rows = [row for row in trend_rows if row[measure] is not None]
    if not available_rows:
        st.info("No annual observation is available for this measure in the selected country or economy.")
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
        return "Not available", False
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
            classes = ["number"] if is_number else []
            if column == "Selected country":
                classes.append("selected-cell")
            if column == "Difference vs group median":
                classes.append("difference-cell")
            if column == "Research signal(s)":
                classes.append("signal-cell")
            css_class = f' class="{" ".join(classes)}"' if classes else ""
            cells.append(f"<td{css_class}>{escape(value)}</td>")
        body_html.append(f"<tr>{''.join(cells)}</tr>")
    st.markdown(
        f'<div class="dashboard-table-wrap" style="max-height: {max_height}px;"><table class="dashboard-table">'
        f"<thead><tr>{header_html}</tr></thead><tbody>{''.join(body_html)}</tbody></table></div>",
        unsafe_allow_html=True,
    )


def render_group_comparison_chart(
    peer_metrics: list[dict[str, Any]],
    palette: dict[str, str],
    selected_country_name: str,
    group_name: str,
) -> None:
    """Show each metric as an explicit country-versus-group-median comparison."""
    available_metrics = [
        row
        for row in peer_metrics
        if row["Selected country"] is not None or row["Peer median"] is not None
    ]
    if not available_metrics:
        st.info("No selected-period values are available for this country/group comparison.")
        return

    country_label = selected_country_name
    group_label = f"Median: {group_name}"
    for left, right in zip(available_metrics[::2], available_metrics[1::2] + [None] * (len(available_metrics) % 2)):
        columns = st.columns(2)
        for column, metric in zip(columns, (left, right)):
            if metric is None:
                continue
            rows = []
            if metric["Selected country"] is not None:
                rows.append({"Comparison": country_label, "Value": metric["Selected country"], "Kind": "Country"})
            if metric["Peer median"] is not None:
                rows.append({"Comparison": group_label, "Value": metric["Peer median"], "Kind": "Group median"})
            with column:
                st.markdown(
                    f'<div class="chart-title">{escape(metric["Metric"])}</div>',
                    unsafe_allow_html=True,
                )
                chart = (
                    alt.Chart(alt.Data(values=rows))
                    .mark_circle(size=130, opacity=0.95)
                    .encode(
                        x=alt.X("Value:Q", title=None),
                        y=alt.Y(
                            "Comparison:N",
                            title=None,
                            sort=[country_label, group_label],
                            axis=alt.Axis(labelLimit=240, labelFontSize=11),
                        ),
                        color=alt.Color(
                            "Kind:N",
                            scale=alt.Scale(
                                domain=["Country", "Group median"],
                                range=[palette["selected"], palette["other"]],
                            ),
                            legend=None,
                        ),
                        tooltip=[
                            alt.Tooltip("Comparison:N", title="Comparison"),
                            alt.Tooltip("Value:Q", title=metric["Metric"], format=".2f"),
                        ],
                    )
                    .properties(height=115)
                    .configure(background=palette["background"])
                    .configure_view(stroke=palette["grid"])
                    .configure_axis(
                        labelColor=palette["text"], titleColor=palette["text"], gridColor=palette["grid"]
                    )
                )
                st.altair_chart(chart, use_container_width=True)


def render_coverage_chart(coverage_rows: list[dict[str, Any]], palette: dict[str, str]) -> None:
    """Provide a fast visual scan of data coverage while retaining the exact table."""
    chart_rows = [
        {**row, "Chart label": COVERAGE_CHART_LABELS.get(row["Indicator"], row["Indicator"])}
        for row in coverage_rows
    ]
    chart = (
        alt.Chart(alt.Data(values=chart_rows))
        .mark_bar(cornerRadiusEnd=4)
        .encode(
            x=alt.X("Coverage (%):Q", title="Coverage (%)", scale=alt.Scale(domain=[0, 100])),
            y=alt.Y(
                "Chart label:N",
                title=None,
                sort="-x",
                axis=alt.Axis(labelLimit=260, labelFontSize=12, labelPadding=10),
            ),
            color=alt.Color(
                "Coverage (%):Q",
                scale=alt.Scale(domain=[0, 100], range=[palette["other"], palette["selected"]]),
                legend=None,
            ),
            tooltip=[
                alt.Tooltip("Indicator:N"),
                alt.Tooltip("Available observations:Q", format=","),
                alt.Tooltip("Coverage (%):Q", format=".2f"),
            ],
        )
        .properties(height=220)
        .configure(background=palette["background"])
        .configure_view(stroke=palette["grid"])
        .configure_axis(labelColor=palette["text"], titleColor=palette["text"], gridColor=palette["grid"])
    )
    st.altair_chart(chart, use_container_width=True)


def main() -> None:
    appearance = st.sidebar.radio("Appearance", ("Light", "Dark"), index=0, horizontal=True)
    palette = apply_theme(appearance)
    brand_icon, brand_text = st.columns([1, 12])
    with brand_icon:
        st.image("assets/development-gap-explorer-icon.png", width=58)
    with brand_text:
        st.title("Development Gap Explorer")
        st.caption("Compare economic and social progress across countries over time.")
        st.markdown(
            '<div class="supplementary-note"><span class="disclaimer-star">✱</span>'
            'Not investment advice, forecasting, causal analysis, or country ratings.</div>',
            unsafe_allow_html=True,
        )
    try:
        data = load_dashboard_data()
    except (DashboardDataError, OSError, ValueError) as exc:
        st.error(f"Dashboard data is unavailable: {exc}")
        st.info("Run `python etl.py` first, then refresh this page.")
        return

    quality = data["quality"]
    st.sidebar.divider()
    st.sidebar.markdown("**Explore**")
    active_view = st.sidebar.radio(
        "Open section",
        ("Country shortlist", "Country explorer", "About this data"),
        label_visibility="collapsed",
    )
    if active_view != "About this data":
        st.markdown(
            '<div class="welcome-card"><strong>Find countries worth a closer look.</strong>'
            '<span>Filter the comparison, then explore one country in context.</span></div>',
            unsafe_allow_html=True,
        )

    available_years = sorted({int(row["year"]) for row in data["country_year_rows"]})
    if active_view != "About this data":
        st.sidebar.divider()
        st.sidebar.header("Dashboard filters")
        st.sidebar.caption("These filters update every result. Leave optional filters blank to keep all countries and economies.")
        selected_period = st.sidebar.slider(
            "Analysis period",
            min_value=available_years[0],
            max_value=available_years[-1],
            value=(available_years[0], available_years[-1]),
            step=1,
            help="The dashboard recalculates descriptive changes and research-signal thresholds from the local country-year data. It does not call the API.",
        )
    else:
        selected_period = (available_years[0], available_years[-1])
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
    if active_view != "About this data":
        st.sidebar.markdown("**Refine comparison population**")
        chosen_regions = st.sidebar.multiselect("Region", regions)
        chosen_income_groups = st.sidebar.multiselect("Income group", income_groups)
    else:
        chosen_regions = []
        chosen_income_groups = []

    filtered_rows = [
        row
        for row in progress_rows
        if (not chosen_regions or row["region_name"].strip() in chosen_regions)
        and (not chosen_income_groups or row["income_level_name"] in chosen_income_groups)
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
    if active_view != "About this data":
        first, second, third, fourth = st.columns(4)
        first.metric("Countries and economies in scope", len(filtered_rows))
        second.metric("Complete core comparisons", complete_filtered)
        third.metric("GDP / life-expectancy signals", life_signal_filtered)
        fourth.metric("GDP / unemployment signals", unemployment_signal_filtered)

    if active_view == "Country shortlist":
        st.markdown('<div class="section-kicker">Start here</div>', unsafe_allow_html=True)
        st.subheader("Country shortlist")
        st.markdown(
            f'<div class="period-pill">Selected period: {period["start_year"]}-{period["end_year"]}</div>',
            unsafe_allow_html=True,
        )
        table_view = st.radio(
            "Shortlist view",
            ("All country comparisons", "Research signals", "Some core data unavailable"),
            horizontal=True,
            help="Research signals are descriptive prompts for further investigation. Missing core data is a data-quality flag, not an analytical conclusion.",
        )
        if table_view == "Research signals":
            table_rows = [
                row
                for row in filtered_rows
                if any(signal not in {"none", INSUFFICIENT_CORE_DATA} for signal in signal_options(row))
            ]
        elif table_view == "Some core data unavailable":
            table_rows = [row for row in filtered_rows if INSUFFICIENT_CORE_DATA in signal_options(row)]
        else:
            table_rows = filtered_rows
        view_explanations = {
            "Research signals": "Countries flagged by one or more transparent research rules. The “Research signal(s)” column tells you which rule applies.",
            "Some core data unavailable": "An endpoint is unavailable for at least one core measure. This is a data-quality flag, not a finding.",
            "All country comparisons": "Full reference list with all six selected-period changes.\nGDP growth and secondary enrolment add context only. They do not trigger a research signal.",
        }
        st.markdown(
            f'<div><span class="dynamic-number">{len(table_rows)}</span> shown of '
            f'<span class="dynamic-number">{len(filtered_rows)}</span> countries and economies matching the current filters.</div>',
            unsafe_allow_html=True,
        )
        if table_view == "Some core data unavailable":
            render_table(display_missing_core_rows(table_rows))
        else:
            render_table(display_all_comparison_rows(table_rows))
        st.markdown(
            f'<div class="table-context-note">{escape(view_explanations[table_view])}</div>',
            unsafe_allow_html=True,
        )
        with st.expander("How are research signals defined?", expanded=False):
            signal_definition = definitions[HIGH_GDP_PER_CAPITA_CHANGE_LOW_LIFE_EXPECTANCY_GAIN]
            st.markdown(
                f"- **High GDP change + low life gain:** GDP per capita changed by at least "
                f"{signal_definition['gdp_threshold']:.2f}% while life expectancy changed by no more than "
                f"{signal_definition['life_expectancy_threshold']:.2f} years.\n"
                "- **GDP up + unemployment up:** GDP per capita increased while the unemployment rate also increased.\n"
                "- **Core-data status:** core measures are GDP per capita, life expectancy, unemployment, and population. "
                "A missing endpoint remains missing. It is not treated as zero."
            )
        st.caption("Scroll inside the table to see more rows. A horizontal scrollbar appears only when the screen is too narrow for every column.")

    if active_view == "Country explorer":
        st.markdown('<div class="section-kicker">Investigate</div>', unsafe_allow_html=True)
        st.subheader("Explore one country or economy")
        st.caption("Choose a country and comparison basis.")
        if not filtered_rows:
            st.warning("No countries match the selected filters. Adjust the filters to use the country explorer.")
        else:
            iso2_codes = data["country_iso2_codes"]
            countries_by_label = {
                country_option_label(row, iso2_codes): row for row in filtered_rows
            }
            country_labels = sorted(countries_by_label)
            default_country_index = next(
                (index for index, label in enumerate(country_labels) if countries_by_label[label]["country_code"] == "ISR"),
                next((index for index, label in enumerate(country_labels) if countries_by_label[label]["core_metrics_available"]), 0),
            )
            country_column, flag_column, group_column = st.columns([10, 1, 10])
            with country_column:
                selected_label = st.selectbox("Country or economy", country_labels, index=default_country_index)
            selected = countries_by_label[selected_label]
            with flag_column:
                st.markdown(
                    '<div class="country-flag-preview">'
                    + country_flag_image_html(selected["country_code"], iso2_codes)
                    + "</div>",
                    unsafe_allow_html=True,
                )
            with group_column:
                grouping_options = {
                    "Similar-income countries": "Income group",
                    "Same World Bank region": "Region",
                }
                grouping_label = st.radio(
                    "Compare selected country with", tuple(grouping_options),
                    horizontal=True,
                    help="Compare the selected country with the median of other countries in one meaningful group. This is context for research, not a ranking.",
                )
            trend_rows = country_trend_rows(data["country_year_rows"], selected["country_code"])
            selected_signals = signal_options(selected)
            descriptive_signals = [signal for signal in selected_signals if signal not in {"none", INSUFFICIENT_CORE_DATA}]
            if descriptive_signals:
                signal_summary = " ".join(SIGNAL_PLAIN_LANGUAGE[signal] for signal in descriptive_signals)
                st.markdown(
                    '<div class="research-signal-note"><span class="label">Research signal</span>'
                    f'<strong>{escape(selected["country_name"])}</strong>: {escape(signal_summary)}</div>',
                    unsafe_allow_html=True,
                )
            elif INSUFFICIENT_CORE_DATA in selected_signals:
                st.info(
                    f"Data note for {selected['country_name']}: one or more core endpoint comparisons are unavailable "
                    f"({selected.get('missing_core_metrics', '').replace(';', ', ')}). Missing data is not replaced with zero."
                )
            else:
                st.markdown(
                    "<div class=\"supplementary-note\">No descriptive research signal was triggered for "
                    f"<span class=\"selected-name\">{escape(selected['country_name'])}</span> in this period.</div>",
                    unsafe_allow_html=True,
                )

            peer_grouping = grouping_options[grouping_label]
            peer = peer_comparison(progress_rows, selected["country_code"], peer_grouping)
            trends_tab, comparison_tab = st.tabs(["Annual trends", "Comparison"])
            with comparison_tab:
                st.markdown(
                    '<div class="comparison-basis">Comparison basis · '
                    f'<strong>{escape(selected["country_name"])}</strong> vs the median of '
                    f'<strong>{peer["peer_count"]}</strong> countries and economies in '
                    f'<strong>{escape(peer["group_name"])}</strong>.</div>',
                    unsafe_allow_html=True,
                )
                if peer_grouping == "Region":
                    st.caption("World Bank regional classification.")
                with st.expander(f"View countries in this comparison group ({peer['peer_count']})"):
                    st.markdown(
                        '<div class="country-flag-list">'
                        + "".join(
                            country_flag_html(member["country_code"], member["country_name"], iso2_codes)
                            for member in peer["members"]
                        )
                        + "</div>",
                        unsafe_allow_html=True,
                    )
                st.subheader("Comparison results")
                peer_table_rows = [
                    {
                        "Metric": row["Metric"],
                        "Selected country": row["Selected country"] if row["Selected country"] is not None else "Not available",
                        "Comparison-group median": row["Peer median"] if row["Peer median"] is not None else "Not available",
                        "Difference vs group median": row["Difference from peer median"] if row["Difference from peer median"] is not None else "Not calculated",
                        "Countries with data": row["Peer observations"],
                    }
                    for row in peer["metrics"]
                ]
                render_table(peer_table_rows, max_height=260)
                st.caption("✱ “Not available” means a selected-period value is missing. Differences need both values.")
                st.markdown('<div class="visual-heading">Visual comparison</div>', unsafe_allow_html=True)
                render_group_comparison_chart(peer["metrics"], palette, selected["country_name"], peer["group_name"])
                st.caption(f"Each chart compares **{selected['country_name']}** with the median for **{peer['group_name']}**. Each metric keeps its own unit and scale.")
                scatter_rows = [
                    {
                        "Country": row["country_name"],
                        "GDP per capita change (%)": row["gdp_per_capita_change_pct"],
                        "Life expectancy change (years)": row["life_expectancy_change_years"],
                        "Highlight": "Selected country" if row["country_code"] == selected["country_code"] else "Other countries",
                        "Research signals": ", ".join(SIGNAL_LABELS.get(signal, signal) for signal in signal_options(row)),
                    }
                    for row in filtered_rows
                    if row["gdp_per_capita_change_pct"] is not None and row["life_expectancy_change_years"] is not None
                ]
                st.subheader("GDP per capita and life expectancy comparison")
                if selected["gdp_per_capita_change_pct"] is None or selected["life_expectancy_change_years"] is None:
                    missing_for_scatter = []
                    if selected["gdp_per_capita_change_pct"] is None:
                        missing_for_scatter.append("GDP per capita")
                    if selected["life_expectancy_change_years"] is None:
                        missing_for_scatter.append("life expectancy")
                    st.info(f"{selected['country_name']} is not highlighted because its selected-period {', '.join(missing_for_scatter)} comparison is unavailable. Missing data is not replaced with zero.")
                if scatter_rows:
                    scatter = (
                        alt.Chart(alt.Data(values=scatter_rows)).mark_circle(size=80, opacity=0.75).encode(
                            x=alt.X("GDP per capita change (%):Q", title="GDP per capita change (%)"),
                            y=alt.Y("Life expectancy change (years):Q", title="Life expectancy change (years)"),
                            color=alt.Color("Highlight:N", scale=alt.Scale(domain=["Other countries", "Selected country"], range=[palette["other"], palette["selected"]])),
                            tooltip=[alt.Tooltip("Country:N"), alt.Tooltip("GDP per capita change (%):Q", format=".2f"), alt.Tooltip("Life expectancy change (years):Q", format=".2f"), alt.Tooltip("Research signals:N")],
                        ).properties(height=380).configure(background=palette["background"]).configure_view(stroke=palette["grid"]).configure_axis(labelColor=palette["text"], titleColor=palette["text"], gridColor=palette["grid"]).configure_legend(labelColor=palette["text"], titleColor=palette["text"])
                    )
                    st.altair_chart(scatter, use_container_width=True)
                    st.caption("GDP-per-capita change → · Life-expectancy change ↑")
                else:
                    st.info("The current filters contain no countries with both scatter-plot measures available.")
            with trends_tab:
                st.markdown(
                    f'### Annual trends: <span class="selected-name">{escape(selected["country_name"])}</span>',
                    unsafe_allow_html=True,
                )
                left, right = st.columns(2)
                with left:
                    render_trend_chart("GDP per capita, constant 2015 US dollars", "Inflation-adjusted annual output per person.", trend_rows, "gdp_per_capita_constant_2015_usd", palette)
                    render_trend_chart("Life expectancy at birth (years)", "Average expected lifespan at birth.", trend_rows, "life_expectancy_years", palette)
                with right:
                    render_trend_chart("Unemployment, total (% of total labor force)", "Labor-force share without work. Change uses percentage points.", trend_rows, "unemployment_total_pct", palette)
                    render_trend_chart("Population", "Context for other measures. It is not a research signal by itself.", trend_rows, "population_total", palette)
                st.divider()
                st.subheader("Supplementary indicators")
                st.markdown(
                    '<div class="supplementary-note"><span>✱</span>Context only. Annual GDP growth shows year-to-year pace. Secondary enrolment adds education context but has lower coverage. Neither changes a research signal.</div>',
                    unsafe_allow_html=True,
                )
                supplementary_left, supplementary_right = st.columns(2)
                with supplementary_left:
                    render_trend_chart("GDP per capita growth (annual %)", "Year-to-year real growth.", trend_rows, "gdp_per_capita_growth_annual_pct", palette)
                with supplementary_right:
                    render_trend_chart("Secondary enrolment, gross (%)", "Enrolled secondary-school students. The rate can exceed 100%, and missing observations are common.", trend_rows, "secondary_enrollment_gross_pct", palette)

    if active_view == "About this data":
        st.markdown('<div class="section-kicker">Trust the data</div>', unsafe_allow_html=True)
        st.subheader("Method, data quality, and limits")
        expected_rows = quality["expected_country_year_rows"]
        coverage_rows = [
            {"Indicator": INDICATOR_LABELS.get(code, code), "Available observations": expected_rows - missing_count, "Coverage (%)": round((expected_rows - missing_count) / expected_rows * 100, 2)}
            for code, missing_count in quality["missing_observations_by_indicator"].items()
        ]
        st.markdown("#### Coverage at a glance")
        st.caption("Hover for exact observations. Use the table for precise values.")
        render_coverage_chart(coverage_rows, palette)
        st.caption(
            f"Snapshot: {quality['expected_country_year_rows']:,} country-year rows across "
            f"{quality['country_count']} countries and economies. Missing values are unavailable, not zero."
        )
        st.markdown("#### Coverage details")
        render_table(coverage_rows, max_height=280)
        with st.expander("Research-signal definitions and limits", expanded=False):
            signal_definition = definitions[HIGH_GDP_PER_CAPITA_CHANGE_LOW_LIFE_EXPECTANCY_GAIN]
            st.markdown(
                f"- **GDP-per-capita change + low life-expectancy gain:** GDP per capita changed by at least {signal_definition['gdp_threshold']:.2f}% and life expectancy changed by no more than {signal_definition['life_expectancy_threshold']:.2f} years. These are data-derived thresholds for the selected period.\n"
                "- **GDP-per-capita increase + unemployment increase:** GDP per capita increased while unemployment also increased.\n"
                "- **Missing core data:** one or more core endpoint comparisons is unavailable."
            )
            st.info(definitions["limitation"])


if __name__ == "__main__":
    main()
