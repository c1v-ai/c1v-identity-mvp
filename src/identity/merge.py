import pandas as pd
from typing import Dict, List, Any, Optional
from .uid import best_uid

def survivorship(group: pd.DataFrame, policy: Dict[str, Any]) -> Dict[str, Any]:
    """Apply survivorship rules to create golden record"""
    result = {}
    
    # Get source priority order
    source_order = policy.get("survivorship", {}).get("source_priority", [])
    
    # Sort group by source priority and recency
    g = group.copy()
    if source_order:
        g["_priority"] = g["source"].apply(lambda s: source_order.index(s) if s in source_order else len(source_order))
        g = g.sort_values(["_priority", "updated_at"], ascending=[True, False], na_position="last")
    else:
        g = g.sort_values("updated_at", ascending=False, na_position="last")
    
    # Apply survivorship rules for each field
    for field in ["email", "phone", "first", "last", "address", "postal", "city", "region"]:
        if field not in g.columns:
            continue
            
        if field in ["email", "phone"]:
            # Prefer non-null most recent
            non_null = g[g[field].notna()]
            if not non_null.empty:
                result[field] = non_null.iloc[0][field]
            else:
                result[field] = None
                
        elif field == "address":
            # Prefer longest non-null address
            candidates = g[g[field].notna()][field]
            if not candidates.empty:
                result[field] = max(candidates, key=lambda x: len(str(x)))
            else:
                result[field] = None
                
        else:
            # Default: prefer first non-null by priority
            non_null = g[g[field].notna()]
            if not non_null.empty:
                result[field] = non_null.iloc[0][field]
            else:
                result[field] = None
    
    # Generate best UID
    result["uid"] = best_uid(
        result.get("email"),
        result.get("phone"),
        result.get("first"),
        result.get("last"),
        result.get("postal")
    )
    
    # Collect source information
    result["source_ids"] = list(zip(g["source"], g["id"]))
    result["source_count"] = len(g)
    result["sources"] = sorted(g["source"].unique().tolist())
    
    # Confidence based on match scores (if available)
    if "score" in group.columns:
        result["confidence"] = group["score"].mean()
    else:
        result["confidence"] = 1.0
    
    return result

def build_golden(df: pd.DataFrame, pairs: pd.DataFrame, policy: Dict[str, Any]) -> pd.DataFrame:
    """Build golden records from matched pairs"""
    # Initialize union-find structure
    parent = {i: i for i in df.index}
    
    def find(x):
        """Find with path compression"""
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]
    
    def union(a, b):
        """Union two clusters"""
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra
    
    # Union all auto-merged pairs (only if pairs exist)
    if not pairs.empty and "decision" in pairs.columns:
        auto_merge_pairs = pairs[pairs["decision"] == "auto_merge"]
        for _, row in auto_merge_pairs.iterrows():
            union(row["left"], row["right"])
    
    # Assign cluster IDs
    df["cluster"] = df.index.map(find)
    
    # Build golden records for each cluster
    golden_records = []
    
    for cluster_id, group in df.groupby("cluster"):
        # Add match scores to group if available
        if not pairs.empty:
            # Get all scores for this cluster
            cluster_indices = set(group.index)
            relevant_pairs = pairs[
                (pairs["left"].isin(cluster_indices)) & 
                (pairs["right"].isin(cluster_indices))
            ]
            if not relevant_pairs.empty:
                group = group.copy()
                group["score"] = relevant_pairs["score"].mean()
        
        # Apply survivorship
        golden = survivorship(group, policy)
        golden["cluster_id"] = cluster_id
        golden_records.append(golden)
    
    return pd.DataFrame(golden_records)

def calculate_metrics(all_records: int, golden_records: int, pairs_df: pd.DataFrame) -> Dict[str, float]:
    """Calculate identity resolution metrics"""
    metrics = {
        "total_records": all_records,
        "golden_records": golden_records,
        "dup_rate": 1 - (golden_records / all_records) if all_records > 0 else 0,
        "compression_ratio": all_records / golden_records if golden_records > 0 else 1
    }
    
    if not pairs_df.empty:
        total_pairs = len(pairs_df)
        auto_merge = len(pairs_df[pairs_df["decision"] == "auto_merge"])
        needs_review = len(pairs_df[pairs_df["decision"] == "needs_review"])
        
        metrics.update({
            "total_pairs": total_pairs,
            "auto_merge_count": auto_merge,
            "auto_merge_rate": auto_merge / total_pairs if total_pairs > 0 else 0,
            "needs_review_count": needs_review,
            "needs_review_rate": needs_review / total_pairs if total_pairs > 0 else 0
        })
    
    return metrics
