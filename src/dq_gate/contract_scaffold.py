import sys, yaml, pandas as pd
from pathlib import Path

SEVERITY = {
    "schema_mismatch": "RED",
    "missing_consent": "RED", 
    "null_pct_exceeded": "AMBER",
    "duplicate_id": "RED",
    "type_mismatch": "RED"
}

PII_PATTERNS = {"email", "phone", "ssn", "first_name", "last_name", "address", "dob", "postal", "zip"}

def infer_type(series: pd.Series) -> str:
    """Rule-based type inference"""
    col_name = series.name.lower() if hasattr(series, 'name') else ""
    
    # Check patterns first
    if any(p in col_name for p in ["email", "mail"]):
        return "email"
    if any(p in col_name for p in ["phone", "mobile", "cell"]):
        return "phone"
    if any(p in col_name for p in ["postal", "zip"]):
        return "postal"
    if any(p in col_name for p in ["date", "time", "_at", "_on"]):
        return "timestamp"
    if any(p in col_name for p in ["amount", "price", "cost", "revenue"]):
        return "currency"
    
    # Pandas dtype inference
    if pd.api.types.is_integer_dtype(series):
        return "integer"
    if pd.api.types.is_float_dtype(series):
        return "number"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "timestamp"
    
    return "string"

def build_contract(csv_path: Path, source_name: str, owner_email: str, industry="generic"):
    df = pd.read_csv(csv_path, nrows=5000)
    
    schema = {}
    for col in df.columns:
        col_type = infer_type(df[col])
        is_pii = any(tok in col.lower() for tok in PII_PATTERNS)
        
        schema[col] = {
            "type": col_type,
            "pii": is_pii,
            "nullable": bool(df[col].isna().any())
        }
        
        if is_pii and col_type in ["email", "phone", "string"]:
            schema[col]["consent_scope"] = "marketing"
    
    # First non-null column as required by default
    required_fields = [df.columns[0]]
    
    contract = {
        "version": "1.0.0",
        "source": source_name,
        "owner": owner_email,
        "industry": industry,
        "schema_ref": f"{industry}@1.0.0",
        "freshness_slo_minutes": 60,
        "required_fields": required_fields,
        "schema": schema,
        "quality_rules": {
            "max_null_pct": {
                col: 5.0 for col in required_fields
            }
        },
        "severity_map": SEVERITY
    }
    
    return contract

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python -m src.dq_gate.contract_scaffold <csv_path> <source_name> <owner_email> [industry]")
        sys.exit(1)
    
    csv_path = Path(sys.argv[1])
    source_name = sys.argv[2]
    owner_email = sys.argv[3]
    industry = sys.argv[4] if len(sys.argv) > 4 else "generic"
    
    out_path = Path(f"configs/contracts/{source_name}.yaml")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    contract = build_contract(csv_path, source_name, owner_email, industry)
    out_path.write_text(yaml.safe_dump(contract, sort_keys=False))
    print(f"Contract written to {out_path}")
