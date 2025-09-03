import pytest
import yaml
from pathlib import Path
from src.dq_gate.runner import run, check_consent

def test_missing_consent_is_red(tmp_path):
    """PII without consent should be RED"""
    contract = tmp_path / "contract.yaml"
    contract.write_text(yaml.dump({
        "source": "test_source",
        "owner": "test@example.com",
        "required_fields": ["id"],
        "schema": {
            "id": {"type": "string", "pii": False},
            "email": {"type": "email", "pii": True}  # No consent_scope
        },
        "severity_map": {
            "schema_mismatch": "RED",
            "missing_consent": "RED",
            "null_pct_exceeded": "AMBER"
        }
    }))
    
    result = run(str(contract), None, "staging")
    assert result["severity"] == "RED"
    assert any(i["rule"] == "missing_consent" for i in result["issues"])

def test_null_pct_exceeded_is_amber(tmp_path):
    """Null percentage breach should be AMBER"""
    import pandas as pd
    
    # Create test CSV
    csv_path = tmp_path / "test.csv"
    df = pd.DataFrame({
        "id": ["1", "2", "3", "4", None],  # 20% null
        "email": ["a@b.com", None, None, None, None]  # 80% null
    })
    df.to_csv(csv_path, index=False)
    
    # Create contract
    contract = tmp_path / "contract.yaml"
    contract.write_text(yaml.dump({
        "source": "test_source",
        "owner": "test@example.com",
        "required_fields": ["id"],
        "schema": {
            "id": {"type": "string"},
            "email": {"type": "email", "pii": True, "consent_scope": "marketing"}
        },
        "quality_rules": {
            "max_null_pct": {
                "id": 10.0,  # Will fail
                "email": 50.0  # Will fail
            }
        },
        "severity_map": {
            "schema_mismatch": "RED",
            "missing_consent": "RED",
            "null_pct_exceeded": "AMBER"
        }
    }))
    
    result = run(str(contract), str(csv_path), "staging")
    assert result["severity"] == "AMBER"
    assert len([i for i in result["issues"] if i["rule"] == "null_pct_exceeded"]) == 2

def test_green_when_no_issues(tmp_path):
    """Should be GREEN when all checks pass"""
    contract = tmp_path / "contract.yaml"
    contract.write_text(yaml.dump({
        "source": "test_source",
        "owner": "test@example.com",
        "required_fields": [],
        "schema": {
            "id": {"type": "string", "pii": False},
            "email": {"type": "email", "pii": True, "consent_scope": "marketing"}
        },
        "severity_map": {
            "schema_mismatch": "RED",
            "missing_consent": "RED",
            "null_pct_exceeded": "AMBER"
        }
    }))
    
    result = run(str(contract), None, "staging")
    assert result["severity"] == "GREEN"
    assert len(result["issues"]) == 0
