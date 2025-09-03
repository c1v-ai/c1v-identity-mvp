1. SITUATION ANALYSIS - **Core problem statement** You want “Ask the Data” added to **C1V** with **near-zero surface area growth**: a Streamlit module, router-first (template SQL for 70% of queries), minimal LLM fallback (Claude), and no new infra for V1. Your hand pain + time pressure demand a 5-day delivery, not a 10-day platform.

What you just proposed (Cursor advice)

Keep Streamlit; add src/ask_data/ (router, validator, BQ client, app).

Reuse existing C1V src/serve/api.py, data pipeline, identity artifacts.

V1 = single tenant, no Firebase, no multi-service.

V2 = upgrade to Vertex + BigQuery Connection if/when needed.

Token policy = router handles most, schema card <200 tokens, ≤2 few-shots, session cache.

Judgment (ruthless)

Your 5-day plan is the correct trade-off: it maximizes reuse, minimizes new code, and directly addresses the two biggest risks (PII leaks and cost blow-ups) with guardrails and date/byte caps.

The only “must-fix” in your outline: do not skip validation. Even a light allowlist validator (no DML, no *, approved views only, enforced partition predicates, byte cap) is non-negotiable.

Constraints & leverage

Constraints: single tenant, Streamlit, minimal typing, 5 days.

Leverage: C1V identity normalization, masked dims, existing demo shell, doc auto-updater, synth data.

Uncertainties

None that block V1 if you enforce strict allowlist and pre-aggregate views. Hallucinations and cost are controllable with router + caps.

</contemplator> 

SOLUTION ARCHITECTURE
Below are the most congruent product-requirement rules tailored to your repo and the 5-day plan.

#0 Non-negotiables (V1)

No new services. Everything inside src/ as a Streamlit app + thin helpers.

Single-tenant. No auth provider. Local secrets only.

Read-only. SELECT against allowlisted views only.

Guardrails ON: block DML, block SELECT *, require partition predicate, dry-run byte cap, row cap, PII masked.

Router-first: templates must handle ≥70% of canonical questions. LLM only for non-matches.

#1 Minimal repo layout (additive, no refactor)
src/
  demo/                         # existing
  serve/                        # existing API; do not touch for V1
  ask_data/                     # NEW (≈ 430 LoC target)
    streamlit_app.py            # UI + wiring (≈200)
    router.py                   # template matching (≈50)
    validator.py                # allowlist + caps (≈100)
    bq_client.py                # dry-run + execute (≈80)

#2 Reuse map (C1V → Ask-Data)

Normalization & hashing → reuse from identity package to build dim_customer_masked.

Masked dims + stitch map → source for identity-aware metrics (dup rate, match uplift).

Synth data → seed demo tenant quickly.

Doc auto-updater → write run summaries to docs/runs/.

#3 Semantic layer (the only BQ you need for V1)

Create 3–5 views, partitioned by date, no PII:

-- metrics_revenue_daily
CREATE OR REPLACE VIEW dm.metrics_revenue_daily AS
SELECT DATE(event_date) AS date, SUM(amount) AS revenue
FROM dm.fact_events_view
WHERE event_name = 'order'
GROUP BY date;

-- metrics_dup_rate
CREATE OR REPLACE VIEW dm.metrics_dup_rate AS
SELECT DATE(calc_date) AS date, AVG(dup_rate) AS dup_rate
FROM dm.identity_metrics
GROUP BY date;

-- metrics_match_uplift
CREATE OR REPLACE VIEW dm.metrics_match_uplift AS
SELECT DATE(calc_date) AS date, AVG(match_uplift_pct) AS uplift
FROM dm.identity_metrics
GROUP BY date;

-- dim_customer_masked
CREATE OR REPLACE VIEW dm.dim_customer_masked AS
SELECT customer_token, created_at, segment, region
FROM dm.dim_customer            -- built via identity normalization
-- exclude raw email/phone entirely

-- fact_events_view (partitioned, masked)
CREATE OR REPLACE VIEW dm.fact_events_view AS
SELECT event_timestamp AS event_date, customer_token, event_name, channel, amount
FROM raw.fact_events
-- masked/derived fields only

#4 Router (70% coverage, zero LLM)
# src/ask_data/router.py
import re
from datetime import timedelta

TEMPLATES = [
  # (pattern, view, select_cols, default_window_days)
  (re.compile(r"\brevenue\b.*\blast\s+(\d+)\s+days", re.I), "dm.metrics_revenue_daily", ["date","revenue"], None),
  (re.compile(r"\bdup(licate)?\b.*\brate\b.*\btrend\b", re.I), "dm.metrics_dup_rate", ["date","dup_rate"], 90),
  (re.compile(r"\bmatch\b.*\buplift\b", re.I), "dm.metrics_match_uplift", ["date","uplift"], 90),
  (re.compile(r"\bactive customers\b.*\blast\s+(\d+)\s+days", re.I), "dm.metrics_active_customers", ["date","active_customers"], None),
]

def route_question(q: str):
  q = q.strip().lower()
  for pat, view, cols, default_days in TEMPLATES:
    m = pat.search(q)
    if m:
      days = int(m.group(1)) if m.groups() and m.group(1) else default_days or 90
      sql = f"""
        SELECT {", ".join(cols)}
        FROM `{view}`
        WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL {days} DAY)
        ORDER BY date
        LIMIT 50000
      """
      return {"sql": sql, "routed": True, "view": view, "days": days}
  return {"routed": False}

#5 Validator (allowlist + caps, tiny but strict)
# src/ask_data/validator.py
import re

ALLOW_VIEWS = {
  "dm.metrics_revenue_daily", "dm.metrics_dup_rate", "dm.metrics_match_uplift",
  "dm.metrics_active_customers", "dm.dim_customer_masked", "dm.fact_events_view"
}
DRY_RUN_MAX_BYTES = 1_000_000_000  # 1 GB
ROW_CAP = 50_000
DEFAULT_WINDOW_DAYS = 90

def sanitize_and_validate(sql: str):
  s = " ".join(sql.split())  # collapse whitespace
  # Hard blocks
  if re.search(r"\b(insert|update|delete|merge|drop|alter|create)\b", s, re.I):
    return (False, "DML not allowed")
  if "*" in s:
    return (False, "SELECT * not allowed")
  # Allowlist FROM/JOIN targets
  tables = re.findall(r"(?:from|join)\s+`?([a-z0-9_.]+)`?", s, re.I)
  if not tables or not all(t in ALLOW_VIEWS for t in tables):
    return (False, "Only approved views may be queried")
  # Require a date predicate on 'date' or 'event_date'
  if not re.search(r"\b(date|event_date)\s*>=\s*date_", s, re.I):
    s = s.replace("ORDER BY", f"WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL {DEFAULT_WINDOW_DAYS} DAY) ORDER BY")
  # Enforce LIMIT
  if not re.search(r"\blimit\b", s, re.I):
    s = s + f" LIMIT {ROW_CAP}"
  return (True, s)

#6 BigQuery adapter (dry-run then execute)
# src/ask_data/bq_client.py
from google.cloud import bigquery

def dry_run_bytes(sql: str) -> int:
  client = bigquery.Client()
  job = client.query(sql, job_config=bigquery.QueryJobConfig(dry_run=True, use_query_cache=False))
  return job.total_bytes_processed

def run(sql: str):
  client = bigquery.Client()
  return client.query(sql).result().to_dataframe()

#7 Streamlit app (wire-up; minimal UI)
# src/ask_data/streamlit_app.py
import streamlit as st
from ask_data.router import route_question
from ask_data.validator import sanitize_and_validate, DRY_RUN_MAX_BYTES
from ask_data import bq_client
import altair as alt

st.set_page_config(page_title="Ask the Data", layout="wide")
st.title("Ask the Data — C1V")

q = st.text_input("Ask a question (e.g., 'revenue last 30 days')", "")
if st.button("Run") and q:
    routed = route_question(q)
    if routed.get("routed"):
        ok, sql = sanitize_and_validate(routed["sql"])
    else:
        # LLM fallback (supply tiny schema card + ≤2 few-shots; return JSON {sql: "..."} )
        model_sql = st.session_state.get("llm_sql") or ""  # replace with real call
        ok, sql = sanitize_and_validate(model_sql)

    if not ok:
        st.error(sql); st.stop()

    bytes_est = bq_client.dry_run_bytes(sql)
    if bytes_est > DRY_RUN_MAX_BYTES:
        st.warning(f"Query too large ({bytes_est:,} bytes). Refine filters."); st.stop()

    df = bq_client.run(sql)
    st.dataframe(df.head(500))
    # naive chart guess
    cols = df.columns.tolist()
    if "date" in cols and len(cols) > 1:
        y = [c for c in cols if c != "date"][0]
        chart = alt.Chart(df).mark_line().encode(x="date:T", y=f"{y}:Q")
        st.altair_chart(chart, use_container_width=True)

#8 Canonical questions (acceptance)

Revenue by day (30/60/90d)

Duplicate rate trend (30/60/90d)

Match uplift (WoW)

Active customers last 30 vs prior 30

Orders & AOV by channel (90d)
(LLM fallback handles the rest.)

#9 Token policy (hard limits)

Router answers ≥70% → 0 tokens.

Schema card ≤ 200 tokens (view names, 3–5 columns each, one-liners).

Few-shots ≤ 2 (short).

JSON-only output from LLM; low max_tokens (e.g., 200).

Session cache: never resend schema/few-shots in same session.

#10 Cost rule (decide plan vs BYOK)

Measure # model calls/day during the first week.

If consistently >100/day, a flat plan is likely simpler. If <50/day, BYOK is fine.

Either way, router coverage and cache will dominate savings more than plan choice.

#11 Risks (and minimal mitigation)

PII leakage → Use masked views only; never project email/phone.

Cost blow-ups → Enforce partition predicate + dry-run byte cap + pre-aggregates.

Hallucinated SQL → Tiny schema card + strict allowlist; return refinement prompt on reject.

Scope creep → Lock V1 to 3–5 views and 5 canonical questions.

EXECUTION FRAMEWORK

Day 1–2 (Core Integration)

Create src/ask_data/ with the four files above.

Build the three metric views + dim_customer_masked + fact_events_view.

Router templates for revenue/dup rate/match uplift; wire BigQuery client and validator; charts render.

Day 3–4 (LLM Fallback)
4) Add LLM fallback with schema card (<200 tokens) + ≤2 few-shots; JSON output only.
5) Session cache schema/few-shots + normalized questions; add simple audit log (CSV or BQ table).

Day 5 (Polish & Test)
6) Run canonical question suite; hit ≥3/5 routed and ≥4/5 pass overall.
7) Document for handoff (readme + runbook + limits), and record a 2-minute demo.

Success metrics (V1)

Router answers ≥70% of demo questions.

p95 latency <5s.

Dry-run byte cap respected; row cap enforced.

Zero PII returned.

Token calls/day measured and logged.

Course-correction triggers

Router coverage <50% → add 2 more templates (active customers, orders by channel).

Bytes/query median >200MB → shorten default window to 30–60 days or add a pre-agg.

Frequent validation rejects → expand allowlist views judiciously.

Accountability

PR checklist: tests, guardrails, doc update.

Daily stand-up: router coverage %, # LLM calls, p95 latency, rejects count.