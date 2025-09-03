import yaml
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

from .block_and_match import apply_canonical, generate_pairs
from .merge import build_golden, calculate_metrics

def run(policy_path: str = "configs/unify_policy.yaml") -> Dict[str, Any]:
    """Run the identity unification process"""
    # Load policy
    policy = yaml.safe_load(Path(policy_path).read_text())
    
    # Load and canonicalize data sources
    frames = []
    
    for source_name, file_path in policy["sources"].items():
        # Read CSV
        df = pd.read_csv(file_path)
        
        # Add metadata
        df["source"] = source_name
        df["updated_at"] = pd.Timestamp.now()
        
        # Apply canonical mapping
        df = apply_canonical(df, policy["canonical_map"][source_name])
        
        # Ensure we have an ID column
        if "id" not in df.columns:
            print(f"Warning: No 'id' column in {source_name} after mapping")
            print(f"Available columns: {list(df.columns)}")
            continue
            
        # Select relevant columns
        cols = ["id", "email", "phone", "first", "last", "address", "postal", "city", "region", "source", "updated_at"]
        available_cols = [c for c in cols if c in df.columns]
        
        # Keep only needed columns to avoid duplicates
        frames.append(df[available_cols].copy())
    
    # Combine all sources
    all_df = pd.concat(frames, ignore_index=True)
    
    # Fill missing values with empty strings for blocking
    for col in ["email", "phone", "first", "last", "address", "postal"]:
        if col in all_df.columns:
            all_df[col] = all_df[col].fillna("").astype(str)
    
    # Generate pairs with blocking and scoring
    pairs = generate_pairs(
        all_df,
        policy["blocking"],
        policy["weights"],
        policy["thresholds"]
    )
    
    # Build golden records
    golden = build_golden(all_df, pairs, policy)
    
    # Calculate metrics
    metrics = calculate_metrics(len(all_df), len(golden), pairs)
    
    # Ensure reports directory exists
    Path("reports").mkdir(exist_ok=True)
    
    # Save golden records
    golden_path = Path("reports/golden_contacts.csv")
    golden.to_csv(golden_path, index=False)
    
    # Save match events
    events_path = Path("reports/unify_events.csv")
    if not pairs.empty:
        # Add metadata to pairs
        pairs["timestamp"] = datetime.now().isoformat()
        pairs["run_id"] = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
        pairs.to_csv(events_path, index=False)
    else:
        # Create empty events file
        pd.DataFrame(columns=["left", "right", "score", "decision", "timestamp"]).to_csv(events_path, index=False)
    
    # Print summary
    print(f"Identity Unification Complete!")
    print(f"  Total records: {metrics['total_records']}")
    print(f"  Golden records: {metrics['golden_records']}")
    print(f"  Duplicate rate: {metrics['dup_rate']:.1%}")
    print(f"  Auto-merge rate: {metrics.get('auto_merge_rate', 0):.1%}")
    
    return metrics

if __name__ == "__main__":
    run()
