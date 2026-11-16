import calendar
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="InsuranceIQ | Claims Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

BLUE = "#2563EB"
NAVY = "#17233B"
TEAL = "#0F9D92"
AMBER = "#F59E0B"
RED = "#E45C61"
GRAY = "#64748B"
COLORS = [BLUE, TEAL, AMBER, "#8B5CF6", "#0EA5E9", RED]
DATA_PATH = Path(__file__).parent / "data" / "insurance_claims.csv"

st.markdown("""
<style>
.stApp {background: #F7F9FC; color: #17233B;}
.block-container {padding-top: 2rem; padding-bottom: 3rem; max-width: 1500px;}
[data-testid="stSidebar"] {background: #FFFFFF; border-right: 1px solid #E5EAF2;}
[data-testid="stMetric"] {background: white; border: 1px solid #E3E9F2;
    border-radius: 14px; padding: 18px 20px; box-shadow: 0 3px 12px rgba(15,23,42,.035);}
[data-testid="stMetricLabel"] {font-size: .95rem; color: #55657B;}
[data-testid="stMetricValue"] {font-size: clamp(1.45rem, 2.2vw, 2rem); color: #17233B;}
h1, h2, h3 {color: #17233B; letter-spacing: -.025em;}
[data-testid="stPlotlyChart"] {background: white; border: 1px solid #E3E9F2;
    border-radius: 14px; padding: 6px;}
.hero-title {font-size: 2.2rem; font-weight: 750; letter-spacing: -.04em; margin-bottom: 2px;}
.hero-subtitle {color: #64748B; font-size: 1rem; margin-bottom: 22px;}
.section-label {font-size: 1.25rem; font-weight: 700; padding-top: 10px; margin-bottom: 10px;}
.note {font-size: .85rem; color: #64748B;}
</style>
""", unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def load_data():
    data = pd.read_csv(DATA_PATH, low_memory=False)
    data.columns = data.columns.str.strip()
    required = ["incident_date", "incident_type", "incident_state",
                "total_claim_amount", "fraud_reported"]
    missing = [col for col in required if col not in data.columns]
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing))
    data["incident_date"] = pd.to_datetime(data["incident_date"], errors="coerce")
    data["total_claim_amount"] = pd.to_numeric(
        data["total_claim_amount"], errors="coerce"
    )
    fraud = data["fraud_reported"].astype("string").str.strip().str.upper()
    data["fraud_status"] = fraud.map({"Y": "Flagged", "N": "Not flagged"}).fillna("Unknown")
    return data


def apply_filters(data, types, states, start, end):
    mask = data["incident_type"].isin(types) & data["incident_state"].isin(states)
    if start is not None and end is not None:
        mask &= data["incident_date"].between(pd.Timestamp(start), pd.Timestamp(end))
    return data.loc[mask].copy()


def fig_style(fig, height=370, horizontal=False):
    fig.update_layout(
        template="plotly_white", height=height,
        margin=dict(l=20, r=20, t=65, b=35),
        font=dict(family="Arial, sans-serif", size=14, color=NAVY),
        title_font=dict(size=17, color=NAVY),
        paper_bgcolor="white", plot_bgcolor="white",
        showlegend=False,
    )
    fig.update_xaxes(showgrid=not horizontal, gridcolor="#EDF1F7", tickfont_size=12)
    fig.update_yaxes(showgrid=horizontal, gridcolor="#EDF1F7", tickfont_size=12)
    return fig


def money(value, decimals=1):
    if pd.isna(value):
        return "—"
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:,.{decimals}f}M"
    if abs(value) >= 1_000:
        return f"${value / 1_000:,.{decimals}f}K"
    return f"${value:,.0f}"


# Business glossary for the public automobile insurance sample.
# Definitions reflect column labels, not independently verified source metadata.
FIELD_DEFINITIONS = {
    "months_as_customer": ("Length of the customer relationship in months", "Nonnegative whole number", "Warning"),
    "age": ("Age of the insured individual in years", "Plausible nonnegative integer", "Warning"),
    "policy_number": ("Source policy identifier; treated as an identifier, not a quantity", "Nonblank; preserve leading zeros if present", "Critical"),
    "policy_bind_date": ("Date the insurance policy became effective", "Parseable date", "Warning"),
    "policy_state": ("State associated with the issued policy", "State abbreviation or source category", "Warning"),
    "policy_csl": ("Combined single limit coverage category recorded for the policy", "Source coverage limit category", "Informational"),
    "policy_deductable": ("Policy deductible amount (source spelling retained)", "Nonnegative number", "Warning"),
    "policy_annual_premium": ("Annual premium recorded for the policy", "Nonnegative number", "Warning"),
    "umbrella_limit": ("Additional umbrella liability coverage limit", "Source numeric amount; review exceptional values", "Informational"),
    "insured_zip": ("Postal ZIP code associated with the insured", "Identifier, typically five digits", "Informational"),
    "insured_sex": ("Source recorded sex category for the insured", "Source categorical value", "Informational"),
    "insured_education_level": ("Recorded education-level category", "Source categorical value", "Informational"),
    "insured_occupation": ("Recorded occupation category", "Source categorical value", "Informational"),
    "insured_hobbies": ("Recorded hobby category", "Source categorical value", "Informational"),
    "insured_relationship": ("Recorded relationship category in policy records", "Source categorical value", "Informational"),
    "capital-gains": ("Capital-gains variable supplied by the source dataset", "Numeric value; may be zero", "Informational"),
    "capital-loss": ("Capital-loss variable supplied by the source dataset", "Numeric value; source sign convention", "Informational"),
    "incident_date": ("Date on which the reported incident occurred", "Parseable date", "Critical"),
    "incident_type": ("Incident classification, such as collision or theft", "Nonblank category", "Critical"),
    "collision_type": ("Collision subtype, when the incident involves a collision", "Category or not applicable", "Informational"),
    "incident_severity": ("Severity classification attached to the incident", "Nonblank source category", "Warning"),
    "authorities_contacted": ("Authorities recorded as contacted about the incident", "Category; None may be valid", "Informational"),
    "incident_state": ("State in which the incident occurred", "Nonblank state category", "Critical"),
    "incident_city": ("City in which the incident occurred", "Text or source category", "Informational"),
    "incident_location": ("Reported street or location description of the incident", "Text; potentially sensitive", "Informational"),
    "incident_hour_of_the_day": ("Hour of day the incident occurred", "Whole number from 0 through 23", "Warning"),
    "number_of_vehicles_involved": ("Count of vehicles involved in the incident", "Nonnegative whole number", "Warning"),
    "property_damage": ("Whether property damage was reported", "YES, NO, or unknown", "Informational"),
    "bodily_injuries": ("Count of bodily injuries recorded for the incident", "Nonnegative whole number", "Warning"),
    "witnesses": ("Number of witnesses reported", "Nonnegative whole number", "Informational"),
    "police_report_available": ("Whether a police report was recorded as available", "YES, NO, or unknown", "Informational"),
    "total_claim_amount": ("Total claim amount recorded; not verified paid amount", "Numeric amount greater than or equal to zero", "Critical"),
    "injury_claim": ("Recorded injury-related component of the claim", "Nonnegative numeric amount", "Warning"),
    "property_claim": ("Recorded property-related component of the claim", "Nonnegative numeric amount", "Warning"),
    "vehicle_claim": ("Recorded vehicle-related component of the claim", "Nonnegative numeric amount", "Warning"),
    "auto_make": ("Make or manufacturer of the insured vehicle", "Text/category", "Informational"),
    "auto_model": ("Model of the insured vehicle", "Text/category", "Informational"),
    "auto_year": ("Model year of the insured vehicle", "Plausible four-digit year", "Informational"),
    "fraud_reported": ("Source label indicating a reported fraud flag", "Y, N, or unknown; not verified outcome", "Critical"),
    "fraud_status": ("Derived human-readable label from fraud_reported", "Flagged, Not flagged, or Unknown", "Derived"),
}


def data_dictionary(data):
    records = []
    for column in data.columns:
        description, expected, severity = FIELD_DEFINITIONS.get(
            column, ("Unmapped source column; definition requires review",
                     "Not documented", "Informational")
        )
        records.append({"Field": column, "Description": description,
                        "Data type (loaded)": str(data[column].dtype),
                        "Expected values / guidance": expected,
                        "Missing-value review priority": severity})
    return pd.DataFrame(records)


def quality_report(data):
    checks = []
    for column in data.columns:
        if column == "fraud_status":
            continue
        series = data[column]
        if pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series):
            missing = int((series.isna() | series.astype("string").str.strip().isin(["", "?", "NA", "N/A"])).sum())
        else:
            missing = int(series.isna().sum())
        checks.append({"Column": column, "Missing / placeholders": missing,
                       "Completeness (%)": round(100 * (len(data) - missing) / max(len(data), 1), 1)})
    return pd.DataFrame(checks)


if not DATA_PATH.exists():
    st.error("Dataset not found: `data/insurance_claims.csv`")
    st.info("Place the public insurance claims CSV inside an InsuranceIQ/data folder, then rerun the app.")
    st.stop()

try:
    original_df = load_data()
except Exception as exc:
    st.error(f"Could not load the dataset: {exc}")
    st.stop()

# SIDEBAR / NAVIGATION
with st.sidebar:
    st.markdown("### 🛡️ InsuranceIQ")
    st.caption("Claims Intelligence Platform")
    st.divider()
    page = st.radio(
        "Workspace",
        ["Overview", "Claims Analytics", "Fraud Analytics", "Data Quality", "Documentation"],
        label_visibility="collapsed",
    )
    st.divider()
    st.markdown("**Explore the data**")
    type_options = sorted(original_df["incident_type"].dropna().astype(str).unique())
    state_options = sorted(original_df["incident_state"].dropna().astype(str).unique())
    selected_types = st.multiselect("Incident type", type_options, default=type_options)
    selected_states = st.multiselect("Incident state", state_options, default=state_options)

    valid_dates = original_df["incident_date"].dropna()
    if not valid_dates.empty:
        min_date, max_date = valid_dates.min().date(), valid_dates.max().date()
        dates = st.date_input("Incident date range", value=(min_date, max_date),
                              min_value=min_date, max_value=max_date)
        if len(dates) == 2:
            start_date, end_date = dates
        else:
            start_date, end_date = min_date, max_date
            st.caption("Select both dates to change the range.")
    else:
        start_date = end_date = None

    st.divider()
    st.caption(f"{len(original_df):,} records in source dataset")
    st.caption("Public sample data • Not company data")

filtered = apply_filters(original_df, selected_types, selected_states, start_date, end_date)
valid_claims = filtered["total_claim_amount"].dropna()
claim_count = len(filtered)
claim_total = valid_claims.sum()
claim_avg = valid_claims.mean() if len(valid_claims) else 0
known_fraud = filtered[filtered["fraud_status"].isin(["Flagged", "Not flagged"])]
fraud_pct = (known_fraud["fraud_status"].eq("Flagged").mean() * 100
             if not known_fraud.empty else None)

st.markdown('<div class="hero-title">InsuranceIQ</div>', unsafe_allow_html=True)
st.markdown(
    f'<div class="hero-subtitle">{page} · Interactive insurance claims intelligence</div>',
    unsafe_allow_html=True,
)

if page != "Documentation" and filtered.empty:
    st.warning("No records match these filters. Try selecting more incident types, states, or dates.")
    st.stop()

if page == "Overview":
    st.markdown('<div class="section-label">Portfolio snapshot</div>', unsafe_allow_html=True)
    a, b, c, d = st.columns(4)
    a.metric("Claims in view", f"{claim_count:,}")
    b.metric("Total claim amount", money(claim_total, 2))
    c.metric("Average claim", money(claim_avg, 1))
    d.metric("Fraud flag rate", f"{fraud_pct:.1f}%" if fraud_pct is not None else "—")
    st.caption("Values respond to filters. Claim amounts are recorded amounts, not confirmed payouts.")

    left, right = st.columns(2, gap="medium")
    with left:
        by_type = filtered.groupby("incident_type", as_index=False).agg(
            amount=("total_claim_amount", "sum"), count=("incident_type", "size")
        ).sort_values("amount", ascending=False)
        fig = px.bar(by_type, x="incident_type", y="amount",
                     title="Claim amount by incident type", color_discrete_sequence=[BLUE],
                     custom_data=["count"])
        fig.update_traces(hovertemplate="%{x}<br>Amount: $%{y:,.0f}<br>Records: %{customdata[0]:,}<extra></extra>")
        fig.update_layout(xaxis_title=None, yaxis_title=None)
        fig.update_yaxes(tickformat="~s", tickprefix="$")
        st.plotly_chart(fig_style(fig), use_container_width=True)

    with right:
        timeline = filtered.dropna(subset=["incident_date"]).copy()
        if not timeline.empty:
            monthly = (timeline.assign(month=timeline["incident_date"].dt.to_period("M").dt.to_timestamp())
                       .groupby("month", as_index=False).agg(amount=("total_claim_amount", "sum"), count=("month", "size")))
            monthly["month_label"] = monthly["month"].dt.strftime("%b %Y")
            fig = px.bar(monthly, x="month_label", y="amount", title="Claim amount by incident month",
                         color_discrete_sequence=[TEAL], custom_data=["count"])
            fig.update_traces(hovertemplate="%{x}<br>Amount: $%{y:,.0f}<br>Records: %{customdata[0]:,}<extra></extra>")
            fig.update_layout(xaxis_title=None, yaxis_title=None)
            fig.update_yaxes(tickformat="~s", tickprefix="$")
            st.plotly_chart(fig_style(fig), use_container_width=True)
            st.caption("First/last months may be incomplete; do not infer a decline from partial months.")
        else:
            st.info("No valid incident dates for the current selection.")

    left, right = st.columns(2, gap="medium")
    with left:
        regional = filtered.groupby("incident_state", as_index=False).agg(
            amount=("total_claim_amount", "sum"), count=("incident_state", "size")
        ).sort_values("amount")
        fig = px.bar(regional, x="amount", y="incident_state", orientation="h",
                     title="Claim amount by incident state", color_discrete_sequence=[BLUE],
                     custom_data=["count"])
        fig.update_traces(hovertemplate="%{y}<br>Amount: $%{x:,.0f}<br>Records: %{customdata[0]:,}<extra></extra>")
        fig.update_layout(xaxis_title=None, yaxis_title=None)
        fig.update_xaxes(tickformat="~s", tickprefix="$")
        st.plotly_chart(fig_style(fig, horizontal=True), use_container_width=True)

    with right:
        counts = (filtered["fraud_status"].value_counts()
                  .rename_axis("Fraud status").reset_index(name="Claims"))
        fig = px.pie(counts, values="Claims", names="Fraud status", hole=.64,
                     title="Reported fraud flags", color="Fraud status",
                     color_discrete_map={"Flagged": AMBER, "Not flagged": BLUE, "Unknown": GRAY})
        fig.update_traces(textinfo="percent+label", hovertemplate="%{label}: %{value:,} (%{percent})<extra></extra>")
        st.plotly_chart(fig_style(fig), use_container_width=True)
        st.caption("Flag status is a dataset field, not independent verification of fraud.")

elif page == "Claims Analytics":
    st.markdown('<div class="section-label">Claims deep dive</div>', unsafe_allow_html=True)
    a, b, c = st.columns(3)
    a.metric("Claims", f"{claim_count:,}")
    b.metric("Total amount", money(claim_total, 2))
    c.metric("Average amount", money(claim_avg, 1))

    dimensions = {"Incident type": "incident_type", "Incident state": "incident_state"}
    for label, col in [("Incident type", "incident_type"), ("Incident state", "incident_state")]:
        summary = filtered.groupby(col, as_index=False).agg(
            amount=("total_claim_amount", "sum"), records=(col, "size"),
            average=("total_claim_amount", "mean")
        ).sort_values("amount", ascending=False)
        fig = px.bar(summary, x=col, y="amount", color_discrete_sequence=[BLUE if col == "incident_type" else TEAL],
                     title=f"Total amount by {label.lower()}", custom_data=["records", "average"])
        fig.update_traces(hovertemplate="%{x}<br>Amount: $%{y:,.0f}<br>Records: %{customdata[0]:,}<br>Avg: $%{customdata[1]:,.0f}<extra></extra>")
        fig.update_layout(xaxis_title=None, yaxis_title=None)
        fig.update_yaxes(tickformat="~s", tickprefix="$")
        st.plotly_chart(fig_style(fig), use_container_width=True)

    st.markdown("#### Explore claims")
    show_cols = [c for c in ["policy_number", "incident_date", "incident_type", "incident_state",
                             "incident_severity", "total_claim_amount", "fraud_status"] if c in filtered.columns]
    st.dataframe(filtered[show_cols], hide_index=True, use_container_width=True)
    st.download_button("Download filtered claims (CSV)", filtered.to_csv(index=False).encode("utf-8"),
                       file_name="insuranceiq_filtered_claims.csv", mime="text/csv")

elif page == "Fraud Analytics":
    st.markdown('<div class="section-label">Fraud indicator analysis</div>', unsafe_allow_html=True)
    st.info("A reported fraud flag is a dataset indicator, not proof that a claim was fraudulent.")
    a, b, c = st.columns(3)
    a.metric("Flagged claims", f"{int(filtered['fraud_status'].eq('Flagged').sum()):,}")
    b.metric("Flag rate (known status)", f"{fraud_pct:.1f}%" if fraud_pct is not None else "—")
    c.metric("Unknown status", f"{int(filtered['fraud_status'].eq('Unknown').sum()):,}")
    left, right = st.columns(2, gap="medium")
    with left:
        dist = filtered["fraud_status"].value_counts().rename_axis("Status").reset_index(name="Claims")
        fig = px.pie(dist, names="Status", values="Claims", hole=.60,
                     title="Claims by fraud flag", color="Status",
                     color_discrete_map={"Flagged": AMBER, "Not flagged": BLUE, "Unknown": GRAY})
        fig.update_traces(textinfo="percent+label")
        st.plotly_chart(fig_style(fig), use_container_width=True)
    with right:
        amounts = filtered.groupby("fraud_status", as_index=False).agg(
            average=("total_claim_amount", "mean"), count=("fraud_status", "size")
        )
        fig = px.bar(amounts, x="fraud_status", y="average", color="fraud_status",
                     color_discrete_map={"Flagged": AMBER, "Not flagged": BLUE, "Unknown": GRAY},
                     title="Average claim amount by flag", custom_data=["count"])
        fig.update_traces(hovertemplate="%{x}<br>Average: $%{y:,.0f}<br>Records: %{customdata[0]:,}<extra></extra>")
        fig.update_layout(xaxis_title=None, yaxis_title=None)
        fig.update_yaxes(tickformat="~s", tickprefix="$")
        st.plotly_chart(fig_style(fig), use_container_width=True)
    if "incident_type" in filtered.columns:
        by_type = filtered[filtered["fraud_status"].isin(["Flagged", "Not flagged"])].groupby(
            ["incident_type", "fraud_status"], as_index=False
        ).size().rename(columns={"size": "records"})
        fig = px.bar(by_type, x="incident_type", y="records", color="fraud_status",
                     barmode="group", title="Fraud flags across incident types",
                     color_discrete_map={"Flagged": AMBER, "Not flagged": BLUE})
        fig.update_layout(showlegend=True, legend_title=None, xaxis_title=None, yaxis_title="Record count")
        st.plotly_chart(fig_style(fig), use_container_width=True)

elif page == "Data Quality":
    st.markdown('<div class="section-label">Data quality monitoring</div>', unsafe_allow_html=True)
    st.caption("Quality checks below evaluate the full source dataset, independent of dashboard filters.")
    quality = quality_report(original_df)
    missing_total = int(quality["Missing / placeholders"].sum())
    duplicate_rows = int(original_df.duplicated().sum())
    bad_amount = int((original_df["total_claim_amount"].isna() |
                      (original_df["total_claim_amount"] < 0)).sum())
    invalid_dates = int(original_df["incident_date"].isna().sum())
    a, b, c, d = st.columns(4)
    a.metric("Source records", f"{len(original_df):,}")
    b.metric("Missing / placeholders", f"{missing_total:,}")
    c.metric("Exact duplicates", f"{duplicate_rows:,}")
    d.metric("Invalid amounts", f"{bad_amount:,}")
    st.caption(f"Unparseable or missing incident dates: {invalid_dates:,}. Counts can overlap across checks.")

    issues = quality.sort_values("Missing / placeholders", ascending=False)
    issues = issues[issues["Missing / placeholders"] > 0].head(12)
    if issues.empty:
        st.success("No missing values or placeholder markers found in the inspected columns.")
    else:
        fig = px.bar(issues.sort_values("Missing / placeholders"), x="Missing / placeholders", y="Column",
                     orientation="h", title="Fields with missing or placeholder values",
                     color_discrete_sequence=[AMBER])
        fig.update_layout(xaxis_title="Affected cells", yaxis_title=None)
        st.plotly_chart(fig_style(fig, 400, horizontal=True), use_container_width=True)
    st.markdown("#### Field-level completeness")
    st.dataframe(quality, hide_index=True, use_container_width=True)
    st.download_button("Download data quality report (CSV)", quality.to_csv(index=False).encode("utf-8"),
                       file_name="insuranceiq_quality_report.csv", mime="text/csv")
    st.caption("This is a validation summary, not an automated repair or full ETL integration.")

elif page == "Documentation":
    st.markdown('<div class="section-label">Data documentation hub</div>', unsafe_allow_html=True)
    st.caption("Technical reference for the public insurance sample and this Streamlit application.")

    st.markdown("### Project purpose and scope")
    st.write(
        "InsuranceIQ is a portfolio demonstration for exploring a public automobile insurance "
        "claims dataset. It provides interactive claim analysis, a fraud-flag breakdown, "
        "and source-level data quality reporting. It does not use private insurer data."
    )

    st.markdown("### Data flow and lineage")
    st.markdown(
        "**1. Extract** — Read `data/insurance_claims.csv` using Pandas.\n\n"
        "**2. Validate schema** — Check for five columns required by the dashboard.\n\n"
        "**3. Transform** — Parse incident dates, coerce claim amounts to numeric, "
        "and standardize `fraud_reported` into `fraud_status`.\n\n"
        "**4. Analyze** — Apply user filters, calculate metrics, and aggregate by month, state, and incident type.\n\n"
        "**5. Present** — Render Plotly charts and Streamlit tables; export CSV reports on demand."
    )
    st.markdown(
        "`Public CSV` → `Schema checks` → `Pandas transformations` "
        "→ `Filtered aggregations` → `Streamlit / Plotly`"
    )
    st.info(
        "Current architecture: the CSV is read into memory; no database is created and no "
        "persistent ETL load is performed. Informatica and SharePoint are not integrated."
    )

    st.markdown("### Transformation and validation standards")
    rules = pd.DataFrame([
        {"Field / check": "incident_date", "Rule": "Parse as date; invalid parses become missing", "Why": "Enables time-based analysis"},
        {"Field / check": "total_claim_amount", "Rule": "Coerce to numeric; flag missing or negative amounts", "Why": "Protects claim-value calculations"},
        {"Field / check": "fraud_reported", "Rule": "Trim + uppercase; Y → Flagged, N → Not flagged, else Unknown", "Why": "Consistent categorical analytics"},
        {"Field / check": "Exact duplicate rows", "Rule": "Count fully identical rows, without removing them", "Why": "Surface potential duplicate ingestion"},
        {"Field / check": "Missing / placeholder", "Rule": "Count null, blank, ?, NA and N/A markers per field", "Why": "Measure completeness for review"},
        {"Field / check": "Date completeness", "Rule": "Report missing or unparseable incident dates", "Why": "Avoid misleading temporal charts"},
    ])
    st.dataframe(rules, hide_index=True, use_container_width=True)
    st.caption(
        "Validation results are diagnostic. Unknown and not-applicable categories can be valid "
        "business states; severity labels are review priorities, not proven errors."
    )

    st.markdown("### Data dictionary")
    dictionary = data_dictionary(original_df)
    term = st.text_input("Search dictionary fields and definitions", placeholder="e.g. premium, incident, fraud")
    show_dict = dictionary
    if term.strip():
        match = dictionary.astype(str).apply(
            lambda col: col.str.contains(term.strip(), case=False, regex=False)
        ).any(axis=1)
        show_dict = dictionary.loc[match]
    st.dataframe(show_dict, hide_index=True, use_container_width=True, height=430)
    st.caption(
        "Definitions are inferred from the published column labels and intended as a working "
        "glossary; confirm them against an official source schema before production use."
    )
    st.download_button(
        "Download complete data dictionary (CSV)",
        dictionary.to_csv(index=False).encode("utf-8"),
        file_name="insuranceiq_data_dictionary.csv", mime="text/csv"
    )

    st.markdown("### Data governance and reporting caveats")
    st.markdown(
        "- **Source:** a public sample claims CSV; it is not company operational data.\n"
        "- **Privacy:** treat identifying fields as sensitive if using real-world data in future.\n"
        "- **Claim amount:** reflects recorded claims, not confirmed payments or losses.\n"
        "- **Fraud flag:** reported classification only; not an independent fraud determination.\n"
        "- **Time series:** first and last observed months may have partial coverage.\n"
        "- **Field completeness:** placeholder values may mean unknown or not applicable, "
        "rather than an ingestion failure."
    )

    with st.expander("How to run InsuranceIQ"):
        st.code(
            "python -m pip install streamlit pandas plotly\n"
            "python -m streamlit run app.py", language="bash"
        )
        st.write("Keep `app.py` beside `data/insurance_claims.csv`.")
    with st.expander("Recommended next engineering steps"):
        st.write(
            "Add a separate reproducible ETL script and SQLite tables, schema/unit tests, "
            "a source attribution and license record, a field-level lineage map, and "
            "a SharePoint-ready documentation export. These are future improvements, "
            "not current app capabilities."
        )

st.divider()
st.caption("InsuranceIQ • Portfolio demonstration using public sample data • Built with Python, Pandas, Plotly & Streamlit")
