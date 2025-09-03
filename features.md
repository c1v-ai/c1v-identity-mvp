# C1V Identity MVP Features

## Overview
C1V Identity MVP is a machine learning system for identity matching across multiple data sources. The system generates synthetic training data, trains identity matching models, and provides a REST API for real-time identity matching.

## Core Components

### 1. Synthetic Data Generation
The system includes a comprehensive synthetic data generator that creates realistic training datasets for identity matching models.

#### CLI Usage
```bash
# Generate development dataset (1k/1k/1k records)
python src/gen/synth_from_schemas.py --dev

# Generate custom dataset
python src/gen/synth_from_schemas.py \
  --n-leads 30000 \
  --n-sales 3000 \
  --n-financial 2100 \
  --dup-rate 0.1 \
  --overlap 0.4 \
  --seed 42 \
  --pii plain \
  --locale US

# Generate with hashed PII for security
python src/gen/synth_from_schemas.py --pii hashed --dev
```

#### Output Files
- **CSV Datasets**: `data/synth/leads.csv`, `data/synth/sales.csv`, `data/synth/financial.csv`
- **Training Pairs**: `data/pairs/train.parquet`, `data/pairs/validation.parquet`, `data/pairs/test.parquet`
- **Summary Report**: `reports/synth_summary.json`

#### Features
- **Realistic Data**: Generates automotive industry data with realistic names, addresses, and business information
- **Duplicate Injection**: Creates 5-15% within-source duplicates with realistic noise (case variations, nicknames, typos)
- **Cross-Source Overlap**: 30-60% of entities appear in multiple sources for training positive pairs
- **Hard Negatives**: Generates challenging negative pairs (similar names, same email local-part, geographic proximity)
- **PII Handling**: Supports both plain text and SHA256-hashed modes for security compliance
- **Locale Support**: US and Canadian address formats, phone numbers, and postal codes
- **Reproducibility**: Configurable random seed ensures consistent output across runs

### 2. Ask the Data (MVP)
Natural-language questions answered via templates → SQL → results + charts in Streamlit. Guardrails enforce safety and cost control.

#### Usage
```
PYTHONPATH=$PWD/src ASKDATA_SIMULATE=1 \
python -m streamlit run src/demo/streamlit_app.py --server.port 8501
```

In the UI, open the "Ask the Data" tab and try:
- Revenue by day for the last 30 days
- Duplicate rate trend over the last 90 days
- Match uplift week over week

#### How it works
- Router (templates) maps common questions → SQL (≥70% coverage target)
- Validator enforces: SELECT-only, no `*`, allowlisted views, partition window, LIMIT
- BigQuery client (optional) runs dry-run + execute; otherwise simulated data is shown

#### Guardrails
- Byte cap ≤ 1 GB (dry-run)
- Row cap ≤ 50k
- Default time window injected if missing (90 days)
- Allowlist: `dm.metrics_*`, `dm.dim_customer_masked`, `dm.fact_events_view`

#### Files
- `src/ask_data/router.py`
- `src/ask_data/validator.py`
- `src/ask_data/constants.py`
- `src/ask_data/bq_client.py` (optional)

### 3. Data Quality Gate (MVP)
Contract-based data quality validation with multi-environment policies, alerting, and event tracking.

#### Usage
```bash
# Generate contracts from CSV schemas
python -m src.dq_gate.contract_scaffold data/synth/financial.csv financial fin-owner@company.com
python -m src.dq_gate.contract_scaffold data/synth/leads.csv leads mkt-owner@company.com

# Run DQ checks programmatically
python -c "from src.dq_gate.runner import run; print(run('configs/contracts/financial.yaml', 'data/synth/financial.csv', 'staging'))"
```

#### Features
- **Contract-Based Validation**: YAML contracts define schema, quality rules, and severity mappings
- **Multi-Environment Policies**: Different actions for staging, prod_week1, and prod
- **Rule Types**:
  - Schema validation (required fields, type checking)
  - Quality checks (null percentage thresholds)
  - PII consent verification
- **Severity Levels**: GREEN (pass), AMBER (warning), RED (critical)
- **Actions**: PASS, WARN, BLOCK based on severity and environment
- **Alerting**: Slack and JIRA stubs for non-GREEN results
- **Event Logging**: Append-only CSV audit trail in `reports/dq_events.csv`

#### Guardrails
- Type inference: Rule-based (email, phone, postal, currency, timestamp patterns)
- Consent enforcement: PII fields must have consent_scope
- Configurable thresholds: Per-field null percentage limits
- Industry presets: Automotive, ecommerce, telehealth, generic schemas

#### Files
- `src/dq_gate/contract_scaffold.py` - Generate contracts from CSV
- `src/dq_gate/runner.py` - Execute DQ checks
- `src/dq_gate/gate.py` - Policy enforcement and event logging
- `configs/gate_policy.yaml` - Environment-specific actions
- `configs/contracts/*.yaml` - Per-source contracts

### 4. Identity Unify (MVP)
Deterministic identity resolution with blocking, scoring, and golden record creation.

#### Usage
```bash
# Run identity unification
python -m src.identity.run_unify

# Results in:
# - reports/golden_contacts.csv (deduplicated records)
# - reports/unify_events.csv (match decisions)
```

#### Features
- **Multi-Source Canonicalization**: Map diverse schemas to common fields
- **Deterministic Matching**:
  - Email normalization (Gmail dot removal, plus addressing)
  - Phone normalization (digit extraction, country code handling)
  - Name matching (first initial + last name)
  - Address normalization (basic standardization)
- **Blocking Strategies**: Reduce comparison space
  - Email domain + last 4 chars
  - Phone last 7 digits
  - Name + FSA (Forward Sortation Area)
  - Exact email match
- **Scoring**: Weighted similarity (email: 0.9, phone: 0.7, name: 0.5, postal: 0.2)
- **Decisions**: auto_merge (≥0.9), needs_review (≥0.7), no_match
- **Survivorship**: Configurable rules for golden record fields
- **PII Masking**: Role-based access control with pattern masking

#### Metrics
- Duplicate rate: 1 - (golden records / total records)
- Auto-merge rate: Percentage of pairs auto-merged
- Compression ratio: Total records / golden records

#### Files
- `src/identity/uid.py` - Normalization and UID generation
- `src/identity/block_and_match.py` - Blocking and scoring
- `src/identity/merge.py` - Clustering and survivorship
- `src/identity/run_unify.py` - Orchestration
- `src/common/mask.py` - PII masking utilities
- `configs/unify_policy.yaml` - Matching configuration

### 5. Identity Matching API
REST API for real-time identity matching between records.

#### Endpoints
- `POST /match` - Compare two records and return match probability

#### Request Format
```json
{
  "record1": {
    "email": "john.doe@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "phone": "(555) 123-4567"
  },
  "record2": {
    "email": "john.doe@example.com",
    "first_name": "JOHN",
    "last_name": "DOE",
    "phone": "555-123-4567"
  }
}
```

#### Response Format
```json
{
  "match": true,
  "confidence": 0.95,
  "reason": "exact-email-match"
}
```

### 6. Model Training Pipeline
Machine learning pipeline for training identity matching models on synthetic data.

#### Training Data
- **Positive Pairs**: Records representing the same real-world entity across sources
- **Negative Pairs**: Records representing different entities with similar characteristics
- **Features**: Email similarity, name similarity, phone similarity, address similarity, etc.

#### Model Types
- **Baseline Models**: Rule-based and simple similarity models
- **ML Models**: Gradient boosting, neural networks for advanced matching

## Configuration Options

### Data Generation
- **Record Volumes**: Configurable counts for leads, sales, and financial records
- **Duplicate Rates**: Adjustable within-source duplicate percentages
- **Overlap Rates**: Configurable cross-source entity overlap
- **Noise Profiles**: Customizable typo, case, and formatting variations
- **Geographic Locales**: US, Canadian, or mixed address formats

### PII Security
- **Plain Mode**: Human-readable data for development and testing
- **Hashed Mode**: SHA256-hashed PII for production and security reviews

### Reproducibility
- **Random Seeds**: Configurable seeds for consistent data generation
- **Version Control**: All generation parameters tracked in summary reports

## Development Workflow

1. **Generate Training Data**: Use CLI to create synthetic datasets
   ```bash
   python src/gen/synth_from_schemas.py --dev
   ```

2. **Setup Data Quality Gates**: Generate contracts and run checks
   ```bash
   # Generate contracts
   make scaffold-contracts
   
   # Run DQ checks via UI
   streamlit run src/demo/streamlit_app.py
   ```

3. **Run Identity Unification**: Deduplicate across sources
   ```bash
   make run-unify
   ```

4. **Train Models**: Use generated pairs to train identity matching models
   ```bash
   python src/id_matcher/train.py
   ```

5. **Deploy API**: Serve trained models via REST API
   ```bash
   python src/serve/api.py
   ```

6. **Monitor & Iterate**: 
   - Check DQ metrics in `reports/dq_events.csv`
   - Review unification results in `reports/golden_contacts.csv`
   - Continuously improve with new training data

## File Structure
```
src/
├── ask_data/              # Ask the Data (router, validator, optional BQ)
│   ├── __init__.py
│   ├── router.py
│   ├── validator.py
│   ├── constants.py
│   └── bq_client.py
├── common/                # Shared utilities
│   ├── __init__.py
│   └── mask.py           # PII masking
├── demo/                  # Streamlit demo app
│   └── streamlit_app.py  # Integrated UI for all modules
├── dq_gate/              # Data Quality Gate
│   ├── __init__.py
│   ├── contract_scaffold.py
│   ├── runner.py
│   ├── gate.py
│   ├── alerting/
│   │   └── slack.py
│   └── ticketing/
│       └── jira.py
├── gen/                   # Data generation
│   └── synth_from_schemas.py
├── id_matcher/           # Model training and inference
│   ├── features.py
│   └── train.py
├── identity/             # Identity Unify
│   ├── __init__.py
│   ├── uid.py           # UID normalization
│   ├── block_and_match.py
│   ├── merge.py
│   └── run_unify.py
├── serve/                # API serving
│   └── api.py
└── models.py             # Data models

configs/                  # Configuration files
├── alert_routes.yaml    # Alert routing config
├── contracts/           # DQ contracts
│   ├── financial.yaml
│   ├── leads.yaml
│   └── sales.yaml
├── gate_policy.yaml     # DQ gate policies
├── rbac.yaml           # Role-based access control
├── schemas/            # Industry schema templates
│   └── generic@1.0.0.json
└── unify_policy.yaml   # Identity unify config

data/                    # Generated datasets (gitignored)
├── synth/              # CSV datasets
└── pairs/              # Training pairs

reports/                # Reports and outputs (gitignored)
├── dq_events.csv      # DQ event log
├── golden_contacts.csv # Unified identities
├── unify_events.csv   # Match decisions
└── synth_summary.json # Generation summary

tests/                  # Test suite
├── dq_gate/           # DQ Gate tests
├── identity/          # Identity Unify tests
└── gen/               # Generation tests
```

## Getting Started

1. **Install Dependencies**: 
   ```bash
   pip install -r requirements.txt
   ```

2. **Generate Sample Data**: 
   ```bash
   python src/gen/synth_from_schemas.py --dev
   ```

3. **Setup DQ Contracts**:
   ```bash
   make scaffold-contracts
   ```

4. **Run Tests**: 
   ```bash
   make test-dq      # Test DQ Gate
   make test-identity # Test Identity Unify
   make test         # Run all tests
   ```

5. **Start Integrated Demo**: 
   ```bash
   export PYTHONPATH=src
   streamlit run src/demo/streamlit_app.py --server.port 8501
   ```
   
   This provides:
   - **Single Match**: Test individual record pairs
   - **CSV Upload**: Batch matching with ROI calculation
   - **Ask the Data**: Natural language queries
   - **DQ Gate**: Data quality validation and monitoring
   - **Identity Unify**: Deduplication and golden records

6. **Start API (optional)**: 
   ```bash
   python src/serve/api.py
   ```

## Key Commands

```bash
# Generate synthetic data
python -m src.gen.synth_from_schemas --dev

# Run DQ checks
python -m src.dq_gate.runner configs/contracts/financial.yaml data/synth/financial.csv staging

# Run identity unification
python -m src.identity.run_unify

# View metrics
make metrics-export

# Clean up
make clean
```
