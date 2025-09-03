# Stage 1 Plan — Data Generation & Pairing (Cursor-ready)

> **Goal:** Produce realistic synthetic datasets (leads, sales, financial) + labeled pairs for model training & evaluation. Ship with tests, CLI, docs, and reproducibility.

---

## 0) Working Rules for Claude (Cursor)

* **Ask clarifying questions until 95% understanding** before writing code.
* **Plan-first, then code:** show proposed file diffs first; do not apply until approved.
* **Doc-code parity:** update `features.md`, `testing.md`, `CHANGELOG.md`, and **this plan’s status** with every code change.
* Prefer **small atomic PRs** for each subtask below.

### Clarifications Claude must ask (if unknown)

1. **Record volumes** for Stage 1 (default if not specified: leads=30k, sales=3k, financial=2.1k; also allow a smaller dev mode: 1k/1k/1k).
2. **PII mode:** plain vs. **hashed** (`sha256(customer_salt + value)`); default = plain for local dev.
3. **Duplicate rate targets** per source (default: 5–15% duplicates; cross-source overlap 30–60%).
4. **Field availability** per entity (if `automotive_schemas.json` lacks a field, skip or synthesize with Faker).
5. **Noise profile** (typos, case, nicknames, formatting) and geographic locale (default: US + CA blend).

---

## 1) Scope

* Parse `automotive_schemas.json` and synthesize tabular data for **leads, sales, financial**.
* Inject realistic duplicates + noise.
* Build **labeled pairs**:

  * **Positives:** same real-world entity across sources.
  * **Hard negatives:** near-confusers within/between sources (similar email/name/phone/address/company).
* Emit train/validation/test splits and quick summary metrics.

**Out of scope (Stage 1):** model training beyond basic smoke; advanced clustering; production pipelines.

---

## 2) Deliverables

* `src/gen/synth_from_schemas.py` — generator CLI.
* `data/synth/{leads,sales,financial}.csv` — generated datasets (gitignored).
* `data/pairs/{train,valid,test}.parquet` — labeled pairs with `y ∈ {0,1}`.
* `reports/synth_summary.json` — counts, dup rates, overlap, nulls, uniqueness.
* Tests under `tests/gen/` (unit + property-based for constraints).
* Docs: `features.md`, `testing.md`, `CHANGELOG.md` updated.

---

## 3) Target File Changes (show diffs before apply)

```
src/
  gen/
    synth_from_schemas.py        # main generator + CLI
  id_matcher/
    features.py                  # create file with 6–10 sims (stubs usable by Stage 2)
    __init__.py
  serve/api.py                   # (no change in Stage 1)
  models.py                      # (no change in Stage 1)

tests/
  gen/
    test_synth_happy_path.py
    test_pairs_quality.py

.dataignore or .gitignore updates for data/ and reports/
```

---

## 4) Data Generation Spec

### 4.1 Entities & Required Fields (minimum)

* **leads**: `id,email,phone,first_name,last_name,company,address,city,state,zip,country,source,created_at`
* **sales**: `id,email,phone,first_name,last_name,account,address,city,state,zip,country,order_id,order_date,order_value`
* **financial**: `id,email,phone,first_name,last_name,account,billing_address,city,state,zip,country,invoice_id,invoice_date,amount`

> If a field is missing from `automotive_schemas.json`, generate best-effort with **Faker** and keep types consistent.

### 4.2 Duplicates & Noise

* **Within-source duplicates**: 5–15%; create by copying a base record and applying:

  * Case variants (ALEX vs Alex), nickname mapping (Alex↔Alexander), whitespace & punctuation, phone formats, address abbreviations, email aliases (`+tag`), domain swaps (`gmail.com`↔`googlemail.com`).
* **Cross-source overlap**: 30–60% of entities appear in ≥2 sources.
* **Typos**: Damerau-edit 1–2 char on names and emails with small probability.
* **Address**: USPS-style normalization differences (St↔Street, Apt→#); optional slight geo mismatches.

### 4.3 Pair Construction

* **Positives**: take entity IDs linked during synthesis to produce pairs across sources; include a few within-source matches.
* **Hard negatives**: pair records with:

  * Same email **local-part** but different **domain** (e.g., [alex@x.com](mailto:alex@x.com) vs [alex@y.com](mailto:alex@y.com)),
  * Similar names (Jaro-Winkler > 0.9) but different emails/phones,
  * Same zip + address number but different names.
* **Label**: `y=1` for positive, `y=0` for negative; keep class balance ≈ 1:3 to 1:5.

### 4.4 Output Schemas

* **Pairs parquet**: columns `src_a, id_a, src_b, id_b, y` + **optionally** cached lightweight features (`email_domain_equal`, `name_jw`, etc.) to accelerate Stage 2.

### 4.5 Reproducibility

* Set `random_seed` (default 42) controlling Faker and sampling; persist in summary.

---

## 5) CLI & Usage

`src/gen/synth_from_schemas.py` should support:

```
usage: synth_from_schemas.py --schema automotive_schemas.json \
  --outdir data/synth --pairs-out data/pairs \
  --n-leads 30000 --n-sales 3000 --n-financial 2100 \
  --dup-rate 0.1 --overlap 0.4 --seed 42 [--pii hashed|plain] [--locale US|CA]
```

* Writes CSVs and parquet; prints a summary table. Exit **non‑zero** on validation failure.

---

## 6) Validation & Tests

* **Schema validation**: ensure required columns exist and types are plausible (emails contain `@`, phones numeric after strip, zips length 5/6/7 depending on locale).
* **Uniqueness**: base IDs unique; report duplicate counts by strategy.
* **Pairs quality**: at least 100 positives and 500 hard negatives; no leakage (no positive with empty email+phone+name).

### Tests to implement

1. `test_synth_happy_path.py`: generator runs on a tiny config (100/50/50) and emits files & summary with expected keys.
2. `test_pairs_quality.py`: class balance within limits; all `y` ∈ {0,1}; no NaNs in key fields.

---

## 7) Acceptance Gates (Stage 1)

* `automotive_schemas.json` parsed without error.
* ≥ **1,000 records** per entity (dev mode acceptable locally).
* **Positives ≥ 100**, **hard negatives ≥ 500**.
* **Schema validation 100% pass**.
* Outputs written to `data/synth` and `data/pairs` (gitignored) + `reports/synth_summary.json`.

---

## 8) Risks & Mitigations

* **Schema drift**: tolerant generator (warn & fill with Faker if fields absent). Log warnings into summary.
* **PII handling**: add `--pii hashed` mode immediately to unblock security reviews.
* **Class imbalance**: enforce ratio by sampling negatives.
* **Performance**: vectorize where possible; for large N use chunked writes.

---

## 9) Implementation Tasks (sequenced)

1. **Scaffold generator** (`src/gen/synth_from_schemas.py`):

   * Args parsing (argparse/typer), load JSON schema, Faker instance, seed handling.
   * Emit leads/sales/financial dataframes with noise/dupes.
   * Write CSVs, return summary dict.
2. **Pairs builder** (inside same module or helper):

   * Build entity map to create positives; build hard negatives.
   * Write train/valid/test parquet with split ratio 70/15/15.
3. **Validation layer**:

   * Add simple checks (emails, phones, zips); ensure required columns present.
   * Raise on failure with clear message; include counts in summary.
4. **Tests** under `tests/gen/` (two tests above).
5. **Docs updates** (`features.md`, `testing.md`, `CHANGELOG.md`):

   * Document CLI and outputs; paste sample command.
6. **Make small data sample** in repo (`/samples`) for docs/CI (10–20 rows per entity) if needed.

---

## 10) Example: Minimal API for Generator (pseudo‑code)

```python
# src/gen/synth_from_schemas.py
if __name__ == "__main__":
    args = parse_args()
    rng, faker = seed_everything(args.seed)
    schemas = load_json(args.schema)
    leads = make_leads(schemas['leads'], n=args.n_leads, rng=rng, faker=faker, dup_rate=args.dup_rate, locale=args.locale)
    sales = make_sales(...)
    financial = make_financial(...)
    write_csv(leads, f"{args.outdir}/leads.csv")
    # build pairs
    pairs = build_pairs(leads, sales, financial, overlap=args.overlap, rng=rng)
    write_parquet_splits(pairs, args.pairs_out)
    summary = summarize(leads, sales, financial, pairs)
    write_json(summary, "reports/synth_summary.json")
    print_summary(summary)
```

---

## 11) PR Checklist (for each sub-PR)

* [ ] Code changes (small diffs) + **tests** added.
* [ ] `features.md`, `testing.md`, `CHANGELOG.md` updated.
* [ ] Plan status updated here (checked items below).

### Plan Status

* [ ] Generator scaffold implemented
* [ ] Pairs builder implemented
* [ ] Validation checks implemented
* [ ] Tests passing in CI
* [ ] Docs updated (CLI, outputs, gates)
* [ ] Summary report emitted

---

