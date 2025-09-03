import json, time, yaml, pandas as pd
from pathlib import Path
from typing import Dict, List, Any

def load_yaml(path: str) -> dict:
    return yaml.safe_load(Path(path).read_text())

def check_schema(contract: dict, df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Check schema compliance"""
    issues = []
    severity_map = contract["severity_map"]
    
    # Check required fields
    for field in contract.get("required_fields", []):
        if field not in df.columns:
            issues.append({
                "rule": "schema_mismatch",
                "field": field,
                "detail": "required field missing",
                "severity": severity_map["schema_mismatch"]
            })
    
    # Check type compliance
    for field, meta in contract.get("schema", {}).items():
        if field in df.columns and "type" in meta:
            actual_type = infer_type(df[field])
            expected_type = meta["type"]
            
            if actual_type != expected_type and expected_type != "string":
                issues.append({
                    "rule": "type_mismatch",
                    "field": field,
                    "detail": f"expected {expected_type}, got {actual_type}",
                    "severity": severity_map.get("type_mismatch", "RED")
                })
    
    return issues

def check_quality(contract: dict, df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Check data quality rules"""
    issues = []
    severity_map = contract["severity_map"]
    
    # Null percentage checks
    max_null_rules = contract.get("quality_rules", {}).get("max_null_pct", {})
    for field, max_pct in max_null_rules.items():
        if field in df.columns:
            null_pct = df[field].isna().mean() * 100
            if null_pct > max_pct:
                issues.append({
                    "rule": "null_pct_exceeded",
                    "field": field,
                    "detail": f"null% {null_pct:.1f} > {max_pct}",
                    "severity": severity_map["null_pct_exceeded"]
                })
    
    return issues

def check_consent(contract: dict) -> List[Dict[str, Any]]:
    """Check PII consent compliance"""
    issues = []
    severity_map = contract["severity_map"]
    
    for field, meta in contract.get("schema", {}).items():
        if meta.get("pii") and not meta.get("consent_scope"):
            issues.append({
                "rule": "missing_consent",
                "field": field,
                "detail": "PII field without consent_scope",
                "severity": severity_map["missing_consent"]
            })
    
    return issues

def infer_type(series: pd.Series) -> str:
    """Infer column type from data"""
    col_name = str(series.name).lower()
    
    # Pattern matching
    if "email" in col_name:
        return "email"
    if any(p in col_name for p in ["phone", "mobile"]):
        return "phone"
    if any(p in col_name for p in ["postal", "zip"]):
        return "postal"
    
    # Type checking
    if pd.api.types.is_integer_dtype(series):
        return "integer"
    if pd.api.types.is_float_dtype(series):
        return "number"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "timestamp"
    
    return "string"

def aggregate_severity(issues: List[Dict[str, Any]]) -> str:
    """Determine overall severity"""
    if any(i["severity"] == "RED" for i in issues):
        return "RED"
    if any(i["severity"] == "AMBER" for i in issues):
        return "AMBER"
    return "GREEN"

def run(contract_path: str, csv_path: str = None, env: str = "staging") -> Dict[str, Any]:
    """Run DQ checks"""
    contract = load_yaml(contract_path)
    
    issues = []
    
    # Schema and quality checks if CSV provided
    if csv_path:
        df = pd.read_csv(csv_path)
        issues.extend(check_schema(contract, df))
        issues.extend(check_quality(contract, df))
    
    # Always check consent
    issues.extend(check_consent(contract))
    
    return {
        "ts": int(time.time()),
        "env": env,
        "source": contract["source"],
        "owner": contract.get("owner", "unknown"),
        "severity": aggregate_severity(issues),
        "issues": issues,
        "contract_version": contract.get("version", "1.0.0")
    }
