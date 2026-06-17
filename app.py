# file: starter/app.py
"""
SAR Sentinel
Run with: streamlit run app.py
Expects two files produced by the notebook export cell:
  starter/outputs/live_dashboard/sar_history.parquet      (historical filed SARs)
  starter/outputs/live_dashboard/sar_history_meta.json     (load/failure stats)
  starter/outputs/live_dashboard/live_session.json         (current notebook run)
"""

import os
import json
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ──────────────────────────────────────────────────────────────────────────
# CONFIG / PATHS
# ──────────────────────────────────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SAR Sentinel", page_icon="🛡️")

st.markdown(
    """
    <style>
    .synthetic-watermark {
        position: fixed;
        bottom: 16px;
        right: 16px;
        z-index: 9999;
        background: rgba(220, 38, 38, 0.16);
        border: 1px solid rgba(255, 255, 255, 0.2);
        color: #dc2626;
        padding: 8px 16px;
        border-radius: 14px;
        font-size: 12px;
        font-weight: 600;
        letter-spacing: 0.5px;
        pointer-events: none;
        -webkit-backdrop-filter: blur(20px) saturate(180%);
        backdrop-filter: blur(20px) saturate(180%);
        box-shadow: 0 4px 18px rgba(0, 0, 0, 0.18);
    }
    </style>
    <div class="synthetic-watermark">SYNTHETIC DATA · DEMO ONLY</div>
    """,
    unsafe_allow_html=True,
)

_STARTER_DIR  = os.path.dirname(os.path.abspath(__file__))   # starter/
DATA_DIR      = os.path.join(_STARTER_DIR, "outputs", "live_dashboard")
HISTORY_PATH  = os.path.join(DATA_DIR, "sar_history.csv")
META_PATH     = os.path.join(DATA_DIR, "sar_history_meta.json")
LIVE_PATH     = os.path.join(DATA_DIR, "live_session.json")


# ──────────────────────────────────────────────────────────────────────────
# DATA LOADING
# ──────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=30)
def load_history():
    if not os.path.exists(HISTORY_PATH):
        return pd.DataFrame()
    df = pd.read_csv(HISTORY_PATH)
    # parse list columns back from string (CSV flattens lists to strings)
    import ast
    for col in ["key_indicators", "ai_agents_used", "citations"]:
        df[col] = df[col].apply(
            lambda x: ast.literal_eval(x) if isinstance(x, str) and x.startswith("[") else x
        )
    df["filing_date"] = pd.to_datetime(df["filing_date"], errors="coerce")
    df["processing_date"] = pd.to_datetime(df["processing_date"], errors="coerce")
    df["is_legacy_format"] = df["classification"].eq("High Risk") | df["risk_level"].eq("Level 3")
    df["is_zero_confidence"] = df["confidence_score"].eq(0)
    df["is_duplicate_case"] = df.duplicated(subset="case_id", keep=False)
    return df


@st.cache_data(ttl=30)
def load_meta():
    if not os.path.exists(META_PATH):
        return None
    with open(META_PATH) as f:
        return json.load(f)


@st.cache_data(ttl=10)
def load_live():
    if not os.path.exists(LIVE_PATH):
        return None
    with open(LIVE_PATH) as f:
        return json.load(f)


df_raw = load_history()
meta = load_meta()
live = load_live()

if df_raw.empty:
    st.error(
        f"No historical data found at `{HISTORY_PATH}`. Run the export cell in your "
        "notebook first, then refresh this page."
    )
    st.stop()


# ──────────────────────────────────────────────────────────────────────────
# SIDEBAR — GLOBAL FILTERS (apply to historical tabs)
# ──────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🛡️ SAR Sentinel")
    st.markdown("---")
    st.markdown(
        """
        <div style="display:flex; align-items:center; gap:10px; margin-bottom:0.4rem;">
            <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                 stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="4" y1="21" x2="4" y2="14"></line>
                <line x1="4" y1="10" x2="4" y2="3"></line>
                <line x1="12" y1="21" x2="12" y2="12"></line>
                <line x1="12" y1="8" x2="12" y2="3"></line>
                <line x1="20" y1="21" x2="20" y2="16"></line>
                <line x1="20" y1="12" x2="20" y2="3"></line>
                <line x1="1" y1="14" x2="7" y2="14"></line>
                <line x1="9" y1="8" x2="15" y2="8"></line>
                <line x1="17" y1="16" x2="23" y2="16"></line>
            </svg>
            <span style="font-size:1.75rem; font-weight:700; line-height:1;">Filters</span>
        </div>
        """,
        unsafe_allow_html=True,
    )    
    st.caption("Apply to Overview, Classification, Economics, and Case Explorer tabs.")

    min_date = df_raw["filing_date"].min().date()
    max_date = df_raw["filing_date"].max().date()
    date_range = st.date_input("Filing date range", value=(min_date, max_date),
                                min_value=min_date, max_value=max_date)

    classifications = sorted(df_raw["classification"].dropna().unique())
    sel_classifications = st.multiselect("Classification", classifications, default=classifications)

    risk_levels = sorted(df_raw["risk_level"].dropna().unique())
    sel_risk_levels = st.multiselect("SAR Risk Level", risk_levels, default=risk_levels)

    risk_ratings = sorted(df_raw["risk_rating"].dropna().unique())
    sel_risk_ratings = st.multiselect("Customer Risk Rating", risk_ratings, default=risk_ratings)

    conf_range = st.slider("AI Confidence Range", 0.0, 1.0, (0.0, 1.0), step=0.01)

    st.markdown("---")
    st.caption("Data quality toggles")
    include_legacy = st.checkbox(
        f"Include legacy-format records ({int(df_raw['is_legacy_format'].sum())})", value=True
    )
    include_zero_conf = st.checkbox(
        f"Include zero-confidence outliers ({int(df_raw['is_zero_confidence'].sum())})", value=True
    )
    dedupe_cases = st.checkbox(
        "Show unique cases only (dedupe by case_id, keep most recent filing)", value=False
    )


def apply_filters(df):
    out = df.copy()
    if len(date_range) == 2:
        start, end = date_range
        out = out[(out["filing_date"].dt.date >= start) & (out["filing_date"].dt.date <= end)]
    out = out[out["classification"].isin(sel_classifications)]
    out = out[out["risk_level"].isin(sel_risk_levels)]
    out = out[out["risk_rating"].isin(sel_risk_ratings)]
    out = out[out["confidence_score"].between(conf_range[0], conf_range[1])]
    if not include_legacy:
        out = out[~out["is_legacy_format"]]
    if not include_zero_conf:
        out = out[~out["is_zero_confidence"]]
    if dedupe_cases:
        out = out.sort_values("filing_date").drop_duplicates(subset="case_id", keep="last")
    return out


df = apply_filters(df_raw)

st.title("SAR Sentinel")
st.caption(
    f"{len(df):,} filings shown (of {len(df_raw):,} total) · "
    f"{df['customer_id'].nunique():,} unique customers · "
    f"{df['case_id'].nunique():,} unique cases"
)

tab_overview, tab_class, tab_econ, tab_ai, tab_explore, tab_live = st.tabs(
    ["📊 Overview", "🏷️ Classification & Confidence", "💰 Workflow Economics",
     "🤖 AI Decision Analytics", "🔎 Case Explorer", "🟢 Latest Run"]
)


# ──────────────────────────────────────────────────────────────────────────
# TAB 1 — OVERVIEW
# ──────────────────────────────────────────────────────────────────────────
with tab_overview:
    if df.empty:
        st.warning("No records match the current filters.")
    else:
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Total Filing Events", f"{len(df):,}")
        c2.metric("Unique Cases", f"{df['case_id'].nunique():,}")
        c3.metric("Unique Customers Flagged", f"{df['customer_id'].nunique():,}")
        c4.metric("Avg AI Confidence", f"{df['confidence_score'].mean():.1%}")
        crit_pct = (df["risk_level"].isin(["Critical"]).mean()) if len(df) else 0
        c5.metric("Critical Risk Share", f"{crit_pct:.1%}")

        col_a, col_b = st.columns([2, 1])
        with col_a:
            timeline = df.set_index("filing_date").resample("3h").size().reset_index(name="filings")
            fig = px.line(timeline, x="filing_date", y="filings", markers=True,
                          title="Filing Volume Over Time (3-hour buckets)")
            fig.update_layout(margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(fig, use_container_width=True)
        with col_b:
            class_counts = df["classification"].value_counts().reset_index()
            class_counts.columns = ["classification", "count"]
            fig = px.pie(class_counts, names="classification", values="count", hole=0.45,
                        title="Classification Mix")
            fig.update_layout(margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(fig, use_container_width=True)

        with st.expander("⚠️ Data quality notes"):
            dup_count = int(df_raw["case_id"].duplicated().sum())
            st.markdown(
                f"- **Repeated runs, not distinct incidents**: {len(df_raw):,} filing events map to only "
                f"{df_raw['case_id'].nunique():,} unique case IDs across {df_raw['customer_id'].nunique()} "
                f"customers ({dup_count} duplicate filings) — this archive reflects repeated pipeline "
                f"test runs over a small synthetic customer set, not 1000+ distinct real investigations.\n"
                f"- **Approved-only archive**: every record here has `review_status = human_approved`. "
                f"Rejected/dismissed cases aren't persisted to disk in this version of the pipeline, so "
                f"historical rejection-rate KPIs aren't available — only the *Latest Run* tab can show that.\n"
                f"- **Legacy label format**: {int(df_raw['is_legacy_format'].sum())} records use an older "
                f"`classification='High Risk'` / `risk_level='Level 3'` labeling scheme. Toggle this off in "
                f"the sidebar to exclude them from analysis.\n"
                f"- **Zero-confidence outliers**: {int(df_raw['is_zero_confidence'].sum())} records have "
                f"`confidence_score = 0`, likely a fallback default rather than a real model score.\n"
                + (f"- **Parse failures**: {meta['failed']} of {meta['total_files']} files failed to load "
                   f"(corrupted/empty JSON)." if meta else "")
            )


# ──────────────────────────────────────────────────────────────────────────
# TAB 2 — CLASSIFICATION & CONFIDENCE
# ──────────────────────────────────────────────────────────────────────────
with tab_class:
    if df.empty:
        st.warning("No records match the current filters.")
    else:
        col_a, col_b = st.columns(2)
        with col_a:
            cc = df["classification"].value_counts().reset_index()
            cc.columns = ["classification", "count"]
            fig = px.bar(cc, x="classification", y="count", color="classification",
                        title="Filings by Classification")
            st.plotly_chart(fig, use_container_width=True)
        with col_b:
            rl = df["risk_level"].value_counts().reset_index()
            rl.columns = ["risk_level", "count"]
            fig = px.bar(rl, x="risk_level", y="count", color="risk_level",
                        title="Filings by Risk Level")
            st.plotly_chart(fig, use_container_width=True)

        fig = px.histogram(df, x="confidence_score", color="classification", nbins=30,
                           title="AI Confidence Distribution by Classification", barmode="overlay",
                           opacity=0.7)
        st.plotly_chart(fig, use_container_width=True)

        col_c, col_d = st.columns(2)
        with col_c:
            fig = px.box(df, x="classification", y="confidence_score", color="classification",
                        title="Confidence Spread by Classification", points="outliers")
            st.plotly_chart(fig, use_container_width=True)
        with col_d:
            cross = pd.crosstab(df["classification"], df["risk_level"])
            fig = px.imshow(cross, text_auto=True, aspect="auto",
                            title="Classification × Risk Level", color_continuous_scale="Blues")
            st.plotly_chart(fig, use_container_width=True)


# ──────────────────────────────────────────────────────────────────────────
# TAB 3 — WORKFLOW ECONOMICS (live what-if calculator)
# ──────────────────────────────────────────────────────────────────────────
with tab_econ:
    st.caption(
        "Recreates your pipeline's cost/ROI model (analyze_workflow_efficiency) against the "
        "currently filtered subset. Adjust the assumptions below to run your own what-if scenarios."
    )
    wc1, wc2, wc3, wc4 = st.columns(4)
    ai_cost_per_case = wc1.number_input("AI cost / case ($)", value=0.50, step=0.10, format="%.2f")
    ai_cost_compliance = wc2.number_input("AI compliance cost / filing ($)", value=5.00, step=0.50, format="%.2f")
    human_cost_per_case = wc3.number_input("Human cost / case ($)", value=85.00, step=5.00, format="%.2f")
    human_cost_compliance = wc4.number_input("Human compliance cost / filing ($)", value=150.00, step=10.00, format="%.2f")

    total_cases = len(df)
    approved_count = len(df)  # archive is approved-only
    ai_total = total_cases * ai_cost_per_case + approved_count * ai_cost_compliance
    human_total = total_cases * human_cost_per_case + approved_count * human_cost_compliance
    cost_savings = human_total - ai_total
    roi_pct = (cost_savings / human_total * 100) if human_total else 0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("AI Pipeline Cost", f"${ai_total:,.2f}")
    m2.metric("Human-Equivalent Cost", f"${human_total:,.2f}")
    m3.metric("Cost Savings", f"${cost_savings:,.2f}")
    m4.metric("ROI", f"{roi_pct:.1f}% reduction")

    fig = go.Figure(data=[
        go.Bar(name="AI Pipeline", x=["Total Cost"], y=[ai_total], marker_color="#2563eb"),
        go.Bar(name="Human Equivalent", x=["Total Cost"], y=[human_total], marker_color="#94a3b8"),
    ])
    fig.update_layout(title="AI vs Human-Equivalent Cost", barmode="group", height=350)
    st.plotly_chart(fig, use_container_width=True)

    st.info(
        "⏱️ Time-savings (~99.9% vs a 30 min/case manual baseline) is an estimate carried over from your "
        "pipeline code — no actual per-case processing-time data is currently logged, so this can't be "
        "computed from real timestamps yet.",
        icon="ℹ️",
    )


# ──────────────────────────────────────────────────────────────────────────
# TAB 4 — AI DECISION ANALYTICS
# ──────────────────────────────────────────────────────────────────────────
with tab_ai:
    if df.empty:
        st.warning("No records match the current filters.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Avg Confidence", f"{df['confidence_score'].mean():.1%}")
        c2.metric("Median Confidence", f"{df['confidence_score'].median():.1%}")
        high_conf_pct = (df["confidence_score"] >= 0.80).mean()
        c3.metric("High-Confidence Rate (≥80%)", f"{high_conf_pct:.1%}")

        st.markdown("##### Manual Human Overrides (current notebook session)")
        if live and live.get("cases"):
            overrides = [c for c in live["cases"] if c.get("decision") == "REJECT"]
            if overrides:
                st.dataframe(pd.DataFrame(overrides)[["customer_name", "case_id", "ai_classification",
                                                       "ai_confidence"]], use_container_width=True)
            else:
                st.caption("0 overrides in the current live session — every AI-flagged case was accepted.")
        else:
            st.caption("No live session data loaded yet.")

        st.markdown("##### Agent Roster")
        agent_counts = df["ai_agents_used"].explode().value_counts().reset_index()
        agent_counts.columns = ["agent", "filings_involved_in"]
        fig = px.bar(agent_counts, x="agent", y="filings_involved_in", title="Filings per Agent")
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("##### Most Frequently Flagged Customers")
        top_customers = (
            df.groupby("customer_id")
            .agg(customer_name=("customer_name", "first"),
                 filings=("sar_id", "count"),
                 avg_confidence=("confidence_score", "mean"))
            .sort_values("filings", ascending=False)
            .head(15)
            .reset_index()
        )
        fig = px.bar(top_customers, x="customer_name", y="filings", color="avg_confidence",
                    title="Top 15 Customers by Filing Count", color_continuous_scale="Reds")
        st.plotly_chart(fig, use_container_width=True)


# ──────────────────────────────────────────────────────────────────────────
# TAB 5 — CASE EXPLORER (search + full narrative drill-down)
# ──────────────────────────────────────────────────────────────────────────
with tab_explore:
    search = st.text_input("Search by customer name, SAR ID, or case ID")
    table = df.copy()
    if search:
        mask = (
            table["customer_name"].str.contains(search, case=False, na=False)
            | table["sar_id"].str.contains(search, case=False, na=False)
            | table["case_id"].str.contains(search, case=False, na=False)
        )
        table = table[mask]

    display_cols = ["sar_id", "filing_date", "customer_name", "classification", "risk_level",
                     "confidence_score", "risk_rating", "case_id"]
    st.dataframe(table[display_cols].sort_values("filing_date", ascending=False),
                 use_container_width=True, height=320)

    csv = table[display_cols].to_csv(index=False).encode("utf-8")
    st.download_button("Download filtered results as CSV", csv, "sar_case_export.csv", "text/csv")

    st.markdown("---")
    st.markdown("##### Inspect a filing")
    if not table.empty:
        options = table.apply(lambda r: f"{r['sar_id']} — {r['customer_name']}", axis=1).tolist()
        choice = st.selectbox("Select a filing to view full detail", options)
        chosen_sar_id = choice.split(" — ")[0]
        record = table[table["sar_id"] == chosen_sar_id].iloc[0]

        d1, d2 = st.columns([2, 1])
        with d1:
            st.markdown(f"**Narrative**")
            st.write(record["narrative"])
            st.markdown(f"**AI Reasoning**")
            st.write(record["ai_reasoning"])
            indicators = record["key_indicators"]
            if indicators is not None and len(indicators) > 0:
                st.markdown("**Key Indicators**")
                for ind in indicators:
                    st.markdown(f"- {ind}")
        with d2:
            st.metric("Confidence", f"{record['confidence_score']:.0%}")
            st.metric("Risk Level", record["risk_level"])
            st.write(f"**Classification:** {record['classification']}")
            st.write(f"**Customer:** {record['customer_name']} ({record['customer_id']})")
            st.write(f"**Filed:** {record['filing_date']}")
            citations = record["citations"]
            if citations is not None and len(citations) > 0:
                st.write(f"**Citations:** {', '.join(citations)}")
    else:
        st.caption("No filings match your search/filters.")


# ──────────────────────────────────────────────────────────────────────────
# TAB 6 — LATEST RUN (live notebook session)
# ──────────────────────────────────────────────────────────────────────────
with tab_live:
    if not live:
        st.warning(
            f"No live session data found at `{LIVE_PATH}`. Re-run the export cell in your notebook "
            "after processing a batch."
        )
    else:
        s = live["summary"]
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Cases This Batch", s["total_cases_this_batch"])
        c2.metric("Reviewed", s["reviewed"])
        c3.metric("Pending Review", s["pending_review"])
        c4.metric("Approved SARs", s["approved_sars"])
        c5.metric("Rejected", s["rejected"])
        st.caption(f"Exported at {live['generated_at']} · Total flagged amount this batch: "
                   f"${s['total_flagged_amount']:,.2f}")

        cases_df = pd.DataFrame(live["cases"])
        st.dataframe(
            cases_df[["customer_name", "status", "decision", "ai_classification", "ai_confidence",
                      "risk_rating", "total_amount", "transaction_count", "has_rapid_wire_activity"]],
            use_container_width=True,
        )

        st.markdown("##### Drill into a case's transactions")
        names = cases_df["customer_name"].tolist()
        if names:
            pick = st.selectbox("Customer", names)
            case_row = next(c for c in live["cases"] if c["customer_name"] == pick)
            st.write(f"**Risk flags:** {', '.join(case_row['risk_flags']) if case_row['risk_flags'] else 'none'}")
            if case_row.get("has_rapid_wire_activity"):
                st.warning("⚠️ Rapid wire transfer activity detected on this account.")
            st.markdown("**Top 5 transactions by amount:**")
            st.dataframe(pd.DataFrame(case_row["top_transactions"]), use_container_width=True)