import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from pathlib import Path
# Ensure "src" is importable when running on Streamlit Cloud
sys.path.append(str(Path(__file__).resolve().parents[1]))
import json, time
import pandas as pd
import requests
import streamlit as st
import altair as alt
import yaml
from pathlib import Path
from datetime import datetime

# Ask the Data imports
from ask_data.router import QuestionRouter
from ask_data.validator import SQLValidator
try:
    from ask_data.bq_client import BigQueryClient
    HAS_BQ = True
except Exception:
    BigQueryClient = None  # type: ignore
    HAS_BQ = False

# DQ Gate imports
from dq_gate.runner import run as dq_run
from dq_gate.gate import decide_action, append_event, get_metrics
from dq_gate.alerting.slack import send as slack_send
from dq_gate.ticketing.jira import create as jira_create

# Identity Unify imports
from identity.run_unify import run as unify_run
from common.mask import mask_dataframe

st.set_page_config(page_title="C1V Identity – Demo", layout="wide")
st.title("C1V Identity – Matching Demo")

def default_api_url() -> str:
    # Prefer ENV first; fall back to secrets; then local default
    env_val = os.environ.get("API_URL")
    if env_val:
        return env_val
    try:
        return st.secrets["API_URL"]
    except Exception:
        return "http://localhost:8000/match"

api_url = st.text_input("API URL", value=default_api_url(), help="Override if your API is deployed elsewhere")

# Get current user role from session state or default
if "user_role" not in st.session_state:
    st.session_state.user_role = "viewer"

tab1, tab2, tab3, tab4, tab5 = st.tabs(["Single Match", "CSV Upload", "Ask the Data", "DQ Gate", "Identity Unify"])

# -------- Single Match --------
with tab1:
    col1, col2 = st.columns(2)
    with col1:
        r1_txt = st.text_area("Record 1 (JSON)", value='{"email":"a@x.com","first_name":"Alex","zip":"94107"}', height=220)
    with col2:
        r2_txt = st.text_area("Record 2 (JSON)", value='{"email":"a@x.com","first_name":"ALEX","zip":"94107"}', height=220)

    if st.button("Match Records", type="primary"):
        try:
            payload = {"record1": json.loads(r1_txt), "record2": json.loads(r2_txt)}
            resp = requests.post(api_url, json=payload, timeout=10)
            resp.raise_for_status()
            st.subheader("Result")
            st.code(resp.json(), language="json")
        except Exception as e:
            st.error(f"Error: {e}")

# -------- CSV Upload --------
with tab2:
    st.write("Upload two CSV files. We’ll prefilter by **case-insensitive** email and call the API for each candidate.")
    left, right = st.columns(2)
    with left:
        f1 = st.file_uploader("CSV A (e.g., leads)", type=["csv"], key="csv_a")
    with right:
        f2 = st.file_uploader("CSV B (e.g., sales)", type=["csv"], key="csv_b")

    max_rows = st.slider("Row cap per file", min_value=50, max_value=1000, value=200, step=50)
    cost_per_dupe = st.number_input("Cost per duplicate (USD)", min_value=0.0, value=5.0, step=0.5)

    if st.button("Find Matches", type="primary") and f1 and f2:
        try:
            df1 = pd.read_csv(f1).head(max_rows)
            df2 = pd.read_csv(f2).head(max_rows)
            if "email" not in df1.columns or "email" not in df2.columns:
                st.warning("Both files must contain an 'email' column for this demo.")
            else:
                # Case-insensitive prefilter by email
                df1["email_norm"] = df1["email"].astype(str).str.strip().str.lower()
                df2["email_norm"] = df2["email"].astype(str).str.strip().str.lower()
                candidates = df1.merge(df2, on="email_norm", suffixes=("_a", "_b"))

                if candidates.empty:
                    st.info("No overlapping emails between the two files.")
                else:
                    st.caption(f"Prefiltered candidate pairs: {len(candidates)}")

                    # Build records from side-specific columns, stripping suffixes; include email in both
                    a_cols = [c for c in candidates.columns if c.endswith("_a")]
                    b_cols = [c for c in candidates.columns if c.endswith("_b")]

                    results = []
                    start = time.time()
                    for _, row in candidates.iterrows():
                        rec1 = {"email": row["email_norm"], **{c[:-2]: row[c] for c in a_cols}}
                        rec2 = {"email": row["email_norm"], **{c[:-2]: row[c] for c in b_cols}}
                        payload = {"record1": rec1, "record2": rec2}
                        try:
                            j = requests.post(api_url, json=payload, timeout=5).json()
                            results.append({
                                "email": row["email_norm"],
                                "match": j.get("match", False),
                                "confidence": j.get("confidence", 0.0),
                                "reason": j.get("reason", ""),
                            })
                        except Exception as e:
                            results.append({"email": row.get("email_norm",""), "match": False, "confidence": 0.0, "reason": f"error: {e}"})
                    dur = time.time() - start

                    out = pd.DataFrame(results).sort_values("confidence", ascending=False)
                    st.subheader("Matches")
                    st.dataframe(out, use_container_width=True)

                    dupes = int(out["match"].sum()) if not out.empty else 0
                    roi = dupes * cost_per_dupe
                    st.subheader("ROI (Simple)")
                    st.write(f"Duplicates found: **{dupes}** → Estimated savings: **${roi:,.2f}**  (at ${cost_per_dupe:.2f}/dupe)")
                    st.caption(f"Processed in {dur:.2f}s on {len(candidates)} candidates.")

                    if not out.empty:
                        st.download_button(
                            "Download matches (CSV)",
                            data=out.to_csv(index=False),
                            file_name="matches.csv",
                            mime="text/csv",
                        )
        except Exception as e:
            st.error(f"Error: {e}")

with tab3:
    st.subheader("Ask the Data")

    router = QuestionRouter()
    validator = SQLValidator()

    def simulate_data(view: str, days: int, columns: list) -> pd.DataFrame:
        import numpy as np
        rng = np.random.default_rng(42)
        dates = pd.date_range(
            start=pd.Timestamp.now().normalize() - pd.Timedelta(days=days - 1),
            end=pd.Timestamp.now().normalize(),
            freq="D",
        )
        if "metrics_revenue_daily" in view:
            vals = np.maximum(1000, 10000 + rng.normal(0, 2000, len(dates)))
            return pd.DataFrame({"date": dates, "revenue": vals.round(2)})
        if "metrics_dup_rate" in view:
            vals = np.clip(0.15 + rng.normal(0, 0.05, len(dates)), 0.05, 0.30)
            return pd.DataFrame({"date": dates, "dup_rate": (vals * 100).round(2)})
        if "metrics_match_uplift" in view:
            vals = np.clip(0.25 + rng.normal(0, 0.08, len(dates)), 0.10, 0.40)
            return pd.DataFrame({"date": dates, "uplift": (vals * 100).round(2)})
        if "metrics_active_customers" in view:
            vals = np.maximum(1000, 5000 + rng.normal(0, 500, len(dates)))
            return pd.DataFrame({"date": dates, "active_customers": vals.round().astype(int)})
        vals = np.maximum(10, 100 + rng.normal(0, 20, len(dates)))
        return pd.DataFrame({"date": dates, "value": vals.round(2)})

    examples = [
        "Revenue by day for the last 30 days",
        "Duplicate rate trend over the last 90 days",
        "Match uplift week over week",
        "Active customers last 60 days",
        "Orders by channel last quarter",
    ]
    with st.expander("Examples"):
        st.write(", ".join(examples))

    q = st.text_input("Ask a question", value="")
    run = st.button("Run", type="primary")

    if run and q.strip():
        routed = router.route(q)
        if not routed["routed"]:
            st.warning("Template not matched (LLM fallback not wired in MVP).")
            st.code(routed.get("question", ""), language="text")
        else:
            st.success("Template matched (no LLM call).")
            st.caption(f"View: `{routed['view']}`  |  Window: {routed['days']} days")
            with st.expander("Generated SQL"):
                st.code(routed["sql"], language="sql")

            ok, sql_or_msg = validator.validate_and_sanitize(routed["sql"])
            if not ok:
                st.error(sql_or_msg)
            else:
                sql = sql_or_msg
                simulate = bool(os.environ.get("ASKDATA_SIMULATE")) or not HAS_BQ or BigQueryClient is None

                if simulate:
                    st.info("Simulating results (set ASKDATA_SIMULATE= to use BigQuery).")
                    df = simulate_data(routed["view"], routed["days"], routed["columns"])
                else:
                    client = BigQueryClient()
                    dr = client.dry_run(sql)
                    if not dr.get("success") or not dr.get("within_limits", False):
                        st.warning(f"Dry-run failed or too large: {dr}")
                        df = simulate_data(routed["view"], routed["days"], routed["columns"])
                    else:
                        res = client.execute(sql, dry_run_first=False)
                        if not res.get("success"):
                            st.warning(f"Execution failed: {res.get('error')}. Showing simulated data.")
                            df = simulate_data(routed["view"], routed["days"], routed["columns"])
                        else:
                            df = res["dataframe"]
                            st.caption(f"Rows: {res.get('rows_returned', len(df)):,} | Bytes: {res.get('bytes_processed', 0):,} | Time: {res.get('execution_time_ms', 0):,.0f} ms")

                st.dataframe(df.head(500), use_container_width=True)
                if "date" in df.columns and len(df.columns) > 1:
                    y = [c for c in df.columns if c != "date"][0]
                    chart = alt.Chart(df).mark_line(point=True).encode(x="date:T", y=f"{y}:Q", tooltip=["date", y])
                    st.altair_chart(chart, use_container_width=True)

# -------- DQ Gate Tab --------
with tab4:
    st.subheader("Data Quality Gate")
    
    col1, col2 = st.columns([3, 1])
    with col2:
        st.metric("Coverage", f"{get_metrics()['coverage_pct']}%")
        st.metric("Prevented Defects", get_metrics()['prevented_defects'])
        st.metric("MTTR (hours)", get_metrics()['mttr_hours'])
    
    with col1:
        # Contract selection
        contracts_dir = Path("configs/contracts")
        contracts = list(contracts_dir.glob("*.yaml")) if contracts_dir.exists() else []
        
        if not contracts:
            st.warning("No contracts found in configs/contracts/")
            if st.button("Generate Sample Contracts"):
                for source in ["financial", "leads", "sales"]:
                    os.system(f"python -m src.dq_gate.contract_scaffold data/synth/{source}.csv {source} {source}-owner@company.com")
                st.rerun()
        else:
            contract_file = st.selectbox(
                "Select Contract",
                contracts,
                format_func=lambda p: p.stem.title()
            )
            
            # Environment selection
            col1, col2 = st.columns(2)
            with col1:
                env_options = ["staging", "prod_week1", "prod"]
                env_default = None
                try:
                    env_default = st.secrets.get("APP_ENV") if hasattr(st, "secrets") else None
                except Exception:
                    env_default = None
                try:
                    env_index = env_options.index(env_default) if env_default in env_options else 1
                except Exception:
                    env_index = 1
                env = st.selectbox("Environment", env_options, index=env_index)
            
            with col2:
                csv_path = st.text_input(
                    "CSV Path (optional)",
                    value=f"data/synth/{contract_file.stem}.csv"
                )
            
            # Run checks button
            if st.button("Run DQ Checks", type="primary"):
                result = dq_run(str(contract_file), csv_path if csv_path else None, env)
                action = decide_action(result["severity"], env)
                
                # Display results
                col1, col2 = st.columns(2)
                with col1:
                    severity_color = {
                        "GREEN": "🟢",
                        "AMBER": "🟡", 
                        "RED": "🔴"
                    }
                    st.subheader(f"{severity_color.get(result['severity'], '')} Severity: {result['severity']}")
                
                with col2:
                    action_icon = {
                        "PASS": "✅",
                        "WARN": "⚠️",
                        "BLOCK": "🚫"
                    }
                    st.subheader(f"{action_icon.get(action, '')} Action: {action}")
                
                # Show issues
                if result["issues"]:
                    st.warning(f"Found {len(result['issues'])} issues:")
                    issues_df = pd.DataFrame(result["issues"])
                    st.dataframe(issues_df, use_container_width=True)
                    
                    # Trigger alerts for non-GREEN
                    if result["severity"] in ["AMBER", "RED"]:
                        alerts = yaml.safe_load(Path("configs/alert_routes.yaml").read_text())
                        route = alerts["routes"].get(result["source"], {})
                        
                        slack_send(
                            alerts["slack_webhook"],
                            route.get("slack_channel", "#data-quality"),
                            f"DQ Alert: {result['source']} - {result['severity']} in {env}",
                            result["severity"]
                        )
                        
                        if result["severity"] == "RED":
                            jira_create(
                                route.get("jira_project", "DQ"),
                                f"DQ Violation: {result['source']} - {env}",
                                json.dumps(result["issues"], indent=2),
                                route.get("pager_primary", "data-team@company.com")
                            )
                else:
                    st.success("All checks passed!")
                
                # Log event
                append_event(result, action)
            
            # Show recent events
            st.subheader("Recent DQ Events")
            events_file = Path("reports/dq_events.csv")
            if events_file.exists():
                events_df = pd.read_csv(events_file)
                # Show last 20 events
                st.dataframe(
                    events_df.tail(20).sort_values("ts", ascending=False),
                    use_container_width=True
                )

# -------- Identity Unify Tab --------
with tab5:
    st.subheader("Identity Unify")
    
    col1, col2 = st.columns([3, 1])
    
    # Check if we have results to display
    golden_file = Path("reports/golden_contacts.csv")
    unify_events_file = Path("reports/unify_events.csv")
    
    with col2:
        if golden_file.exists() and unify_events_file.exists():
            golden_df = pd.read_csv(golden_file)
            events_df = pd.read_csv(unify_events_file)
            
            total_sources = 0
            for source in ["leads", "sales", "financial"]:
                if Path(f"data/synth/{source}.csv").exists():
                    total_sources += len(pd.read_csv(f"data/synth/{source}.csv"))
            
            dup_rate = 1 - (len(golden_df) / total_sources) if total_sources > 0 else 0
            auto_merge_rate = len(events_df[events_df["decision"] == "auto_merge"]) / len(events_df) if len(events_df) > 0 else 0
            
            st.metric("Golden Records", f"{len(golden_df):,}")
            st.metric("Duplicate Rate", f"{dup_rate:.1%}")
            st.metric("Auto-merge Rate", f"{auto_merge_rate:.1%}")
    
    with col1:
        # Run unification button
        if st.button("Run Identity Unification", type="primary"):
            with st.spinner("Running unification..."):
                result = unify_run()
                
                st.success(f"""
                ✅ Identity Unification Complete!
                - Total records: {result['total_records']:,}
                - Golden records: {result['golden_records']:,}
                - Duplicate rate: {result['dup_rate']:.1%}
                - Auto-merge rate: {result.get('auto_merge_rate', 0):.1%}
                """)
                
                st.balloons()
        
        # Display controls
        role = st.selectbox(
            "View as role",
            ["viewer", "analyst", "engineer", "admin"],
            key="unify_role"
        )
        st.session_state.user_role = role
        
        # Display golden records
        if golden_file.exists():
            st.subheader("Golden Contacts")
            golden_df = pd.read_csv(golden_file)
            
            # Apply masking based on role
            if role != "admin":
                display_df = mask_dataframe(golden_df.head(100), role)
            else:
                display_df = golden_df.head(100)
            
            st.dataframe(display_df, use_container_width=True)
            
            # Download button (admin only)
            if role == "admin":
                st.download_button(
                    "Download Golden Records",
                    data=golden_df.to_csv(index=False),
                    file_name="golden_contacts.csv",
                    mime="text/csv"
                )
        
        # Show match events
        if unify_events_file.exists():
            st.subheader("Match Events")
            events_df = pd.read_csv(unify_events_file)
            
            # Summary by decision
            decision_counts = events_df["decision"].value_counts()
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Auto-merged", decision_counts.get("auto_merge", 0))
            with col2:
                st.metric("Needs Review", decision_counts.get("needs_review", 0))
            with col3:
                st.metric("No Match", decision_counts.get("no_match", 0))
            
            # Show recent events
            st.dataframe(
                events_df.tail(50).sort_values("score", ascending=False),
                use_container_width=True
            )
