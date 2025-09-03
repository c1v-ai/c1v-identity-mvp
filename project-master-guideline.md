## Purpose
Single source of truth for how we build, test, document, and ship the C1V Identity MVP.

## Vision (MVP)
Identity resolution across Leads/Sales/Financial with: synthetic data gen, baseline model, `/match` API, Streamlit demo with integrated DQ Gate + Identity Unify, and "Gold Zone" outputs (reports/golden_contacts.csv).

## Repo Structure
src/
  models.py
  serve/api.py
  demo/streamlit_app.py            # 5 tabs: Single Match, CSV Upload, Ask the Data, DQ Gate, Identity Unify
  ask_data/{router.py,validator.py,constants.py,bq_client.py}
  common/{mask.py}                 # PII masking utilities
  dq_gate/{contract_scaffold.py,runner.py,gate.py,alerting/,ticketing/}
  identity/{uid.py,block_and_match.py,merge.py,run_unify.py}
  id_matcher/{features.py,train.py} # Stage 2–3
  gen/synth_from_schemas.py        # Stage 1
configs/
  gate_policy.yaml, alert_routes.yaml, rbac.yaml, unify_policy.yaml
  contracts/{financial.yaml,leads.yaml,sales.yaml}
  schemas/generic@1.0.0.json
tests/
  dq_gate/, identity/, gen/
reports/
  dq_events.csv, golden_contacts.csv, unify_events.csv
style/front-end.md


## Branching & PR Rules
- `main` is protected; **all changes via PR**.
- One feature per branch, atomic commits, descriptive messages.
- **Doc-code parity:** every code change updates `cursor-requirements.md`, `features.md`, `testing.md`, `CHANGELOG.md`.
- CI required: `check-docs`, `test` (pytest), `lint` (when enabled).

## Versioning
- Semantic-ish until GA. Tag `v0.x.y`. First tag will be `v0.1.0` when Stage 1–5 MVP is complete.

## Stage Gates (must pass before merging)
- **Stage 1 (Data)**: schema validation 100%; ≥1k rows/entity; pos/neg pairs produced.
- **Stage 2 (Features)**: ≥15 similarity dims; unit test coverage ≥90% for features; feature time <100ms/pair.
- **Stage 3 (Model)**: ROC AUC ≥0.85, PR AUC ≥0.80; threshold documented.
- **Stage 4 (API)**: <500ms P50; full OpenAPI; request ID logging; error models.
- **Stage 5 (Demo)**: CSV flow + ROI; Puppeteer screenshot test stub ready.
- **Stage 6 (Ask the Data)**: Router coverage ≥70%; validator blocks DML/*; Streamlit tab functional.
- **Stage 7 (DQ Gate)**: Contracts generate from CSV; RED blocks in staging; event logging works; tests pass.
- **Stage 8 (Identity Unify)**: Deterministic matching; golden_contacts.csv produced; dup rate <10%; tests pass.

## Environments & Commands
- Local dev:
  - API: `uvicorn src.serve.api:app --reload --port 8000`
  - UI (simulate):  `PYTHONPATH=$PWD/src ASKDATA_SIMULATE=1 python -m streamlit run src/demo/streamlit_app.py --server.port 8501`
  - UI (BigQuery):  `PYTHONPATH=$PWD/src GOOGLE_APPLICATION_CREDENTIALS=/path/to/sa.json python -m streamlit run src/demo/streamlit_app.py --server.port 8501`
  - Tests: `make test` (all), `make test-dq` (DQ Gate), `make test-identity` (Identity Unify)
  - DQ contracts: `make scaffold-contracts`
  - Identity unify: `make run-unify`
  - Metrics: `make metrics-export`
- Deployment (later): Cloud Run for API/UI; secrets via env; CORS restricted.

## Security & Data
- TLS in transit, encrypted at rest (GCP). PII hashing option (SHA-256 + customer salt). Raw uploads retained ≤30 days in POC. Purge on request.

## Decision Log
Create `/docs/decisions/<yyyy-mm-dd>-<topic>.md` for any non-trivial decision; link it in PRs.
MD

# 2) CURSOR REQUIREMENTS
cat > cursor-requirements.md <<'MD'
# Cursor Requirements — C1V Identity MVP

## What this project is
Identity resolution MVP: generate synthetic data → engineer features → train baseline model → expose `/match` → Streamlit demo with ROI.

## Files Claude/Cursor must know
- Source: `src/serve/api.py`, `src/models.py`, `src/demo/streamlit_app.py`
- Stage 1: `src/gen/synth_from_schemas.py`, `automotive_schemas.json`
- Stage 2–3: `src/id_matcher/features.py`, `src/id_matcher/train.py`
- Docs to always update with code: `features.md`, `testing.md`, `CHANGELOG.md`, this file.

## Working Rules (enforced)
1) **Ask clarifying questions until 95% confidence** before writing code.
2) **Plan-first:** write `project-plans/<stage>.md` with tasks, risks, acceptance criteria.
3) **Show diffs first**; do not apply until approved.
4) **Doc-code parity or PR fails**: update docs with any code change.
5) **Tests first mindset** when feasible; at least add/update unit tests per feature.

## MCP Servers (Cursor Settings → .cursor/mcp.json)
- Puppeteer: UI screenshots & flows (later)
- Context7: always prefix with `use context7` for official docs

## Command Patterns for Claude
- **FastAPI:**  
  `use context7` → “Add CORS middleware and 422 error model; show diff first.”
- **sklearn:**  
  `use context7` → “Build pipeline with scaling + classifier; persist with joblib; show diff.”
- **Streamlit:**  
  `use context7` → “Add download button; show diff.”

## Success Metrics (gates)
- Code coverage ≥85% (unit + feature modules once implemented)
- Model gates: ROC AUC ≥0.85, PR AUC ≥0.80
- API: <500ms P50; request ID logging
- Demo: Puppeteer flow passes (later)

## Glossary
- **POC** — Proof of Concept (30 days), limited scope to prove accuracy/ROI.
MD

# 3) CLAUDE OPERATING GUIDE
cat > CLAUDE.md <<'MD'
# CLAUDE.md — C1V Identity MVP

## Context
Stack: Python (FastAPI, sklearn, Streamlit). Scope: Identity MVP for leads/sales/financial matching + demo. MCP: Puppeteer (testing), Context7 (docs), GitHub (PR review).

## Workflow
**Planning (MUST)**  
- Ask clarifying questions until 95% understanding.  
- Create `project-plans/<stage>.md` with tasks, risks, acceptance criteria.

**Implementation (MUST)**  
- **Show diffs first**.  
- Write small, atomic changes.  
- Add/update tests.  
- Keep types & error handling.

**Documentation (MUST)**  
- **Update** `cursor-requirements.md`, `features.md`, `testing.md`, `CHANGELOG.md` with every change.  
- Refuse merges without docs.

## MCP Commands
- `use context7` then the technical request (FastAPI/sklearn/Streamlit).  
- Puppeteer examples (later):  
  - “Navigate to http://localhost:8501, submit Single Match, take screenshot.”

## Code Quality Gates
- Type hints everywhere.
- Proper HTTP errors & models.
- Request ID logging.
- Lint (ruff) and tests pass in CI.

## Stages & Gates
1) **Data & Pairs**: synth_from_schemas; schema validation 100%.
2) **Features**: ≥15 sims; unit tests ≥90% for features.
3) **Train**: ROC AUC ≥0.85; PR AUC ≥0.80; threshold documented.
4) **API**: `/match` implemented; <500ms P50.
5) **Demo**: CSV flow + ROI; Puppeteer test stub.
6) **Ask the Data (MVP)**: Router coverage ≥70%; validator blocks DML/`*`; default date window + LIMIT present; Streamlit tab returns charts in simulate mode; optional BQ dry-run + execute when creds present.

## Prohibited
- Merging without docs/tests.
- Large diffs without plan.
- Guessing API without `use context7`.
MD

# 4) BACK-END GUIDE
cat > back-end-guide.md <<'MD'
# Back-End Guide — C1V Identity MVP

## Stack & Local Dev
- FastAPI + Pydantic + Uvicorn (ORJSON responses)
- Run API: `uvicorn src.serve.api:app --reload --port 8000`
- Health: `GET /healthz` → `{"status":"ok"}`
- Match: `POST /match` with body:
```json
{"record1": {...}, "record2": {...}}

Response: {"match": true, "confidence": 0.93, "reason": "naive-baseline"}


Project Layout
src/models.py                 # Pydantic models
src/serve/api.py              # FastAPI app (CORS, request-id middleware)
src/demo/streamlit_app.py     # Streamlit front-end
src/gen/synth_from_schemas.py # Stage 1
src/id_matcher/{features.py,train.py}  # Stage 2–3
tests/                        # pytest

##Environment
Local: .venv + requirements.txt
optional .streamlit/secrets.toml with API_URL=...
API_URL also read from ENV by Streamlit app.

##Logging & Error Handling
Add UUID request IDs via middleware; include X-Request-ID in responses.
Use structured logs where possible (later: structlog).
On errors, return FastAPI HTTPException with clear detail.

## Key References
- API endpoints & examples: see **back-end-guide.md → Endpoints**.
- Test expectations for API contracts: see **testing.md → API Contract**.
MD