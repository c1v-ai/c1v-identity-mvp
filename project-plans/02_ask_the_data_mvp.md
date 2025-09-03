# Ask the Data — MVP Project Plan (Cursor-ready)

> Goal: Add "Ask the Data" to C1V with near‑zero surface area growth. Streamlit tab, router‑first (≥70% template coverage), strict guardrails, optional BigQuery. Ship in ~5 days with tests and docs.

---

## 0) Working Rules

* Plan-first; small atomic edits; tests and docs updated with every change.
* Enforce guardrails: SELECT-only, no `*`, partition window, byte/row caps.
* Router-first to minimize LLM/token use; fallback later.

---

## 1) Scope (MVP)

* Add a third tab ("Ask the Data") to existing `src/demo/streamlit_app.py`.
* New module `src/ask_data/` with:
  * `router.py` — regex templates → SQL (≥70% coverage)
  * `validator.py` — allowlist + caps + sanitization
  * `constants.py` — limits, allowlist, patterns
  * `bq_client.py` — optional BigQuery (safe if not installed)
* Simulated data path (no creds needed); BigQuery optional via env.

Out of scope (MVP): multi-tenant auth, dashboarding, production infra.

---

## 2) Deliverables

* Working Streamlit tab that answers canonical questions with charts.
* Template router with date parsing (days/weeks/months/quarter).
* Validator that blocks DML/`*`, enforces allowlist, adds time window & LIMIT.
* Optional BigQuery execution with dry-run byte check.
* Tests: router + validator + basic integration.
* Docs: master guideline + features updated.

---

## 3) Repo Changes

```
src/
  ask_data/
    __init__.py
    router.py
    validator.py
    constants.py
    bq_client.py           # optional; safe if GCP not configured
  demo/streamlit_app.py    # add "Ask the Data" tab

project-plans/
  02_ask_the_data_mvp.md   # THIS PLAN
```

---

## 4) Implementation Steps (5 days)

Day 1 — Foundation & Router
1. Scaffold `src/ask_data/` and implement `router.py` (templates + time parsing).
2. Add unit tests for routing and coverage.

Day 2 — Validation & Guardrails
3. Implement `validator.py` (DML/`*` blocks, allowlist, default window, LIMIT).
4. Add tests for validator rules and sanitization.

Day 3 — Streamlit Tab & Simulated Data
5. Add third tab to `src/demo/streamlit_app.py` using router + validator.
6. Simulate results in absence of BigQuery; render table + line chart.

Day 4 — Optional BigQuery & Integration
7. Add `bq_client.py` with dry-run; execute when creds present.
8. Integration tests for end-to-end (simulated path always green).

Day 5 — Polish & Docs
9. Expand patterns to hit ≥70% coverage; verify with test script.
10. Update docs (`project-master-guideline.md`, `features.md`) and CHANGELOG.

---

## 5) Quality Gates

* Routing coverage ≥70% on canonical set (no LLM calls for covered cases).
* 100% of queries pass validator (no DML, no `*`, allowlisted views only).
* Default partition window injected if missing; LIMIT always present.
* Tests pass locally; simulated path works without GCP creds.

---

## 6) Canonical Questions (MVP)

1. Revenue by day (last 30/60/90 days)
2. Duplicate rate trend (30/60/90 days)
3. Match uplift (week over week)
4. Active customers (last 30/60/90 days)
5. Orders by channel (last quarter / last N days)

Target: ≥4/5 routed by templates initially; ≥70% coverage overall.

---

## 7) Commands

Local (simulate):
```
export ASKDATA_SIMULATE=1
export PYTHONPATH=$PWD/src
python -m streamlit run src/demo/streamlit_app.py --server.port 8501
```

With BigQuery (optional):
```
pip install google-cloud-bigquery
unset ASKDATA_SIMULATE
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/sa.json
export PYTHONPATH=$PWD/src
python -m streamlit run src/demo/streamlit_app.py --server.port 8501
```

Tests:
```
python test_router.py
python test_validator.py
```

---

## 8) Risks & Mitigations

* Router under-covers → add 2–3 more patterns; improve normalization.
* Cost spikes on BQ → dry-run byte cap; default date window injected.
* PII exposure → masked/approved views only; validator allowlist.
* Path/package issues → run with `PYTHONPATH=$PWD/src` or add path shim in app.

---

## 9) PR Checklist

* Code + tests added or updated
* Docs updated (`project-master-guideline.md`, `features.md`, CHANGELOG)
* Router coverage check recorded
* Simulate path verified; BQ path optional
* Small, reviewable diffs

---

## 10) Acceptance

* Streamlit tab renders; 3 example questions return charts in simulate mode
* Router coverage ≥70%; validator blocks SELECT * and DML
* Optional BQ executes when creds present; otherwise simulates gracefully
* Docs reflect new module, commands, guardrails, and acceptance gates


