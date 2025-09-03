# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Data Quality Gate** (`src/dq_gate/`)
  - Contract-based validation with YAML configuration
  - Multi-environment policies (staging, prod_week1, prod)
  - Schema validation, quality checks, PII consent verification
  - Severity levels: GREEN/AMBER/RED with PASS/WARN/BLOCK actions
  - Slack and JIRA alerting stubs for non-GREEN results
  - Event logging to `reports/dq_events.csv` for audit trail
  - Metrics: coverage percentage, prevented defects, MTTR
  - Contract scaffolding from CSV schemas with type inference

- **Identity Unify** (`src/identity/`)
  - Deterministic identity resolution across multiple sources
  - Email normalization (Gmail dots, plus addressing)
  - Phone normalization (digit extraction, country codes)
  - Name matching (first initial + last name)
  - Blocking strategies to reduce comparison space
  - Weighted scoring (email: 0.9, phone: 0.7, name: 0.5, postal: 0.2)
  - Auto-merge (≥0.9), needs review (≥0.7), no match decisions
  - Golden record creation with survivorship rules
  - PII masking with role-based access control
  - Outputs: `reports/golden_contacts.csv`, `reports/unify_events.csv`
  - Metrics: duplicate rate, auto-merge rate, compression ratio

- **Integrated Streamlit Demo** (`src/demo/streamlit_app.py`)
  - Unified UI with 5 tabs: Single Match, CSV Upload, Ask the Data, DQ Gate, Identity Unify
  - DQ Gate tab: contract selection, environment choice, real-time validation
  - Identity Unify tab: one-click deduplication, role-based viewing, metrics dashboard
  - Live metrics display for both modules
  - PII masking based on user role (viewer, analyst, engineer, admin)

- **Ask the Data MVP** (Router-first natural language to SQL)
  - Template-based routing for common questions (≥70% coverage)
  - SQL validation with strict guardrails (SELECT-only, no *, allowlisted views)
  - BigQuery integration with dry-run and cost controls
  - Simulated data fallback for demo purposes
  - Integrated into main Streamlit app

- **Synthetic Data Generator CLI** (`src/gen/synth_from_schemas.py`)
  - Generate realistic automotive industry datasets (leads, sales, financial)
  - Support for 1k/1k/1k development mode and production volumes
  - Configurable duplicate rates (5-15%) and cross-source overlap (30-60%)
  - PII handling modes: plain text (default) and SHA256 hashed
  - US and Canadian locale support with realistic address/phone formats
  - Reproducible generation with configurable random seeds
  - Noise injection: case variations, nicknames, typos, whitespace changes

- **Training Data Generation**
  - Automatic creation of labeled training pairs (positive/negative)
  - Positive pairs: same entity across multiple data sources
  - Hard negative pairs: similar names, same email local-part, geographic proximity
  - Train/validation/test splits (70/15/15 ratio)
  - Parquet format output for efficient storage and loading

- **Data Validation & Quality Gates**
  - Schema validation: required columns present and correct types
  - Data quality checks: no NaN values in key fields
  - Pairs quality validation: minimum 100 positives, 500 negatives
  - Class balance enforcement: 1:3 to 1:5 positive:negative ratio
  - Comprehensive validation reporting with PASS/FAIL status

- **Output Files & Reports**
  - CSV datasets: `data/synth/leads.csv`, `sales.csv`, `financial.csv`
  - Training pairs: `data/pairs/train.parquet`, `validation.parquet`, `test.parquet`
  - Summary report: `reports/synth_summary.json` with generation metrics
  - All generated files properly gitignored for security

- **CLI Interface**
  - `--dev` flag for quick development mode (1k/1k/1k records)
  - `--pii hashed|plain` for PII security compliance
  - `--seed` for reproducible data generation
  - `--locale US|CA` for geographic formatting
  - `--dup-rate` and `--overlap` for data characteristics
  - Non-zero exit codes on validation failures

- **Configuration Files**
  - `configs/gate_policy.yaml`: Environment-specific DQ actions
  - `configs/alert_routes.yaml`: Slack/JIRA routing configuration
  - `configs/rbac.yaml`: Role-based access control and PII masking patterns
  - `configs/unify_policy.yaml`: Identity matching rules and thresholds
  - `configs/contracts/`: Per-source DQ contracts
  - `configs/schemas/`: Industry-specific schema templates

- **Makefile Commands**
  - `make test-dq`: Run DQ Gate tests
  - `make test-identity`: Run Identity Unify tests
  - `make scaffold-contracts`: Generate DQ contracts from CSVs
  - `make run-unify`: Execute identity unification
  - `make metrics-export`: Export DQ metrics snapshot
  - `make clean`: Remove cache and temporary files

### Changed
- **Project Structure**
  - Added `src/dq_gate/` for Data Quality Gate components
  - Added `src/identity/` for Identity Unify components
  - Added `src/common/` for shared utilities (PII masking)
  - Added `src/ask_data/` for natural language to SQL
  - Added `configs/` directory for all configuration files
  - Added `tests/dq_gate/` and `tests/identity/` for module tests
  - Updated `.gitignore` to exclude `data/` and `reports/` directories

### Fixed
- **API Contract Documentation**
  - Added Swagger request examples for /match endpoint
  - Documented response format and validation requirements

## [0.1.0] - 2024-01-XX

### Added
- Initial project structure and basic API framework
- Identity matching API endpoint (`POST /match`)
- Basic response models and data structures
- Swagger/OpenAPI documentation

### Technical Details

#### Data Generation Pipeline
The synthetic data generator creates realistic automotive industry data with:
- **Leads Dataset**: Customer prospects with contact and company information
- **Sales Dataset**: Completed transactions with order details
- **Financial Dataset**: Billing and invoice records

#### Quality Assurance
- **Validation Gates**: Automatic checks ensure data meets quality standards
- **Reproducibility**: Fixed seeds guarantee consistent output across runs
- **Security**: PII hashing option for production environments
- **Performance**: Efficient generation with configurable volumes

#### Testing Strategy
- **Unit Tests**: Individual component testing with mocked dependencies
- **Integration Tests**: End-to-end pipeline validation
- **Property Tests**: Data quality constraint verification
- **Performance Tests**: Generation time and memory usage validation

#### CLI Usage Examples
```bash
# Quick development setup
python src/gen/synth_from_schemas.py --dev

# Production dataset with hashed PII
python src/gen/synth_from_schemas.py \
  --n-leads 30000 \
  --n-sales 3000 \
  --n-financial 2100 \
  --pii hashed \
  --seed 42

# Custom configuration
python src/gen/synth_from_schemas.py \
  --dup-rate 0.15 \
  --overlap 0.5 \
  --locale CA
```

#### Output Validation
The system automatically validates:
- Schema compliance (all required fields present)
- Data quality (no missing values in key fields)
- Training set requirements (sufficient positive/negative pairs)
- Class balance (appropriate positive:negative ratios)
- Split integrity (correct train/validation/test proportions)

#### Security Features
- **PII Hashing**: SHA256-based hashing with customer-specific salts
- **Configurable Modes**: Plain text for development, hashed for production
- **Audit Trail**: All generation parameters logged in summary reports
- **Access Control**: Generated data properly excluded from version control