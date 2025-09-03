import pytest
import pandas as pd
import yaml
from pathlib import Path
from src.identity.run_unify import run
from src.identity.block_and_match import score_pair, email_domain_last4, phone_last7

def test_blocking_functions():
    """Test blocking key generation"""
    # Note: john.doe@example.com is not a gmail address, so dots remain
    assert email_domain_last4("john.doe@example.com") == "example.com|.doe"
    assert email_domain_last4("john.doe@gmail.com") == "gmail.com|ndoe"  # Gmail removes dots
    assert email_domain_last4("ab@test.com") == "test.com|ab"  # Short local part
    assert phone_last7("555-123-4567") == "1234567"
    assert phone_last7("123") is None  # Too short

def test_score_pair():
    """Test pair scoring"""
    weights = {
        "email_exact": 0.9,
        "phone_exact": 0.7,
        "name_address": 0.5,
        "postal_match": 0.2
    }
    
    # Exact email match
    a = {"email": "test@example.com", "phone": "555-1234"}
    b = {"email": "test@example.com", "phone": "555-5678"}
    assert score_pair(a, b, weights) == 0.9
    
    # Multiple matches
    a = {"email": "test@example.com", "phone": "555-1234", "last": "Smith", "first": "John"}
    b = {"email": "test@example.com", "phone": "555-1234", "last": "Smith", "first": "J"}
    score = score_pair(a, b, weights)
    assert score == min(0.9 + 0.7 + 0.5, 1.0)  # Capped at 1.0

def test_unify_runs(tmp_path):
    """Test full unification process"""
    # Create test data directories
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    
    # Create test CSVs
    leads_path = data_dir / "leads.csv"
    sales_path = data_dir / "sales.csv"
    financial_path = data_dir / "financial.csv"
    
    # Leads data
    pd.DataFrame([
        {"lead_id": "L1", "email": "ann@example.com", "phone": "555-1111", 
         "first_name": "Ann", "last_name": "Lee", "postal_code": "M5V1A1"},
        {"lead_id": "L2", "email": "bob@test.com", "phone": "555-2222",
         "first_name": "Bob", "last_name": "Kay", "postal_code": "M5V2B2"}
    ]).to_csv(leads_path, index=False)
    
    # Sales data - Ann Lee with different phone
    pd.DataFrame([
        {"order_id": "O1", "customer_email": "ann@example.com", "customer_phone": "555-9999",
         "first_name": "Ann", "last_name": "Lee", "postal_code": "M5V1A1"}
    ]).to_csv(sales_path, index=False)
    
    # Financial data - Ann without email but same phone from leads
    pd.DataFrame([
        {"entity_id": "F1", "email": "", "phone": "555-1111",
         "first_name": "Ann", "last_name": "Lee", "zip": "M5V1A1"}
    ]).to_csv(financial_path, index=False)
    
    # Create policy
    policy = {
        "sources": {
            "leads": str(leads_path),
            "sales": str(sales_path),
            "financial": str(financial_path)
        },
        "canonical_map": {
            "leads": {
                "id": "lead_id",
                "email": "email",
                "phone": "phone",
                "first": "first_name",
                "last": "last_name",
                "postal": "postal_code"
            },
                            "sales": {
                    "id": "order_id",
                    "email": "customer_email", 
                    "phone": "customer_phone",
                    "first": "first_name",
                    "last": "last_name",
                    "postal": "postal_code"
                },
            "financial": {
                "id": "entity_id",
                "email": "email",
                "phone": "phone",
                "first": "first_name",
                "last": "last_name",
                "postal": "zip"
            }
        },
        "blocking": ["email_exact", "phone_last7", "name_fsa"],
        "weights": {
            "email_exact": 0.9,
            "phone_exact": 0.7,
            "name_address": 0.5,
            "postal_match": 0.2
        },
        "thresholds": {
            "auto_merge": 0.9,
            "needs_review": 0.7
        },
        "survivorship": {
            "source_priority": ["sales", "leads", "financial"]
        }
    }
    
    # Save policy
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text(yaml.safe_dump(policy))
    
    # Create reports directory
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    
    # Change to tmp directory to run
    import os
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    
    try:
        # Run unification
        result = run(str(policy_path))
        
        # Debug: check what happened
        if result["golden_records"] != 2:
            pairs_df = pd.read_csv("reports/unify_events.csv")
            print(f"\nDebug - Pairs found: {len(pairs_df)}")
            if len(pairs_df) > 0:
                print(f"Pairs:\n{pairs_df}")
            golden_df = pd.read_csv("reports/golden_contacts.csv") 
            print(f"\nGolden records: {len(golden_df)}")
            print(f"Golden:\n{golden_df[['first', 'last', 'email', 'phone', 'source_count']]}")

        # Check results
        assert result["total_records"] == 4  # 2 leads + 1 sale + 1 financial
        assert result["golden_records"] == 2  # Ann merged, Bob separate
        assert result["dup_rate"] == 0.5  # 50% duplicates
        
        # Check golden records exist
        golden_df = pd.read_csv("reports/golden_contacts.csv")
        assert len(golden_df) == 2
        
        # Check Ann was merged (should have data from all 3 sources)
        ann_record = golden_df[golden_df["last"] == "Lee"].iloc[0]
        assert ann_record["source_count"] == 3
        assert "sales" in ann_record["sources"]
        
        # Check events file exists
        assert Path("reports/unify_events.csv").exists()
        
    finally:
        os.chdir(old_cwd)

def test_empty_sources(tmp_path):
    """Test handling of empty sources"""
    # Create empty CSV
    empty_path = tmp_path / "empty.csv"
    pd.DataFrame(columns=["id", "email", "name"]).to_csv(empty_path, index=False)
    
    policy = {
        "sources": {"empty": str(empty_path)},
        "canonical_map": {"empty": {"id": "id", "email": "email"}},
        "blocking": ["email_exact"],
        "weights": {"email_exact": 0.9},
        "thresholds": {"auto_merge": 0.9, "needs_review": 0.7},
        "survivorship": {}
    }
    
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text(yaml.safe_dump(policy))
    
    import os
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    (tmp_path / "reports").mkdir()
    
    try:
        result = run(str(policy_path))
        assert result["total_records"] == 0
        assert result["golden_records"] == 0
    finally:
        os.chdir(old_cwd)
