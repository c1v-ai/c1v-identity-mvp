import pandas as pd
import itertools
from typing import Dict, List, Optional, Tuple, Any
from .uid import norm_email, norm_phone, fsa, norm_address

def email_domain_last4(email: Optional[str]) -> Optional[str]:
    """Extract domain + last 4 chars of local part for blocking"""
    if not email:
        return None
    
    e = norm_email(email)
    if not e:
        return None
    
    local, _, domain = e.partition("@")
    
    # For gmail, dots are already removed
    # Get last 4 alphanumeric characters
    if len(local) >= 4:
        return f"{domain}|{local[-4:]}"
    else:
        return f"{domain}|{local}"

def phone_last7(phone: Optional[str]) -> Optional[str]:
    """Extract last 7 digits for blocking"""
    p = norm_phone(phone)
    return p[-7:] if p and len(p) >= 7 else None

def name_fsa(first: Optional[str], last: Optional[str], postal: Optional[str]) -> Optional[str]:
    """Create name + FSA blocking key"""
    if not last:
        return None
    
    last_clean = (last or "").strip().lower()
    first_initial = (first or "").strip()[:1].lower()
    postal_fsa = fsa(postal) or ""
    
    return f"{last_clean}|{first_initial}|{postal_fsa}"

def email_exact(email: Optional[str]) -> Optional[str]:
    """Exact email for blocking"""
    return norm_email(email)

def apply_canonical(df: pd.DataFrame, cmap: Dict[str, str]) -> pd.DataFrame:
    """Apply canonical mapping to dataframe columns"""
    # Create reverse mapping (original -> canonical)
    cols = {v: k for k, v in cmap.items() if v in df.columns}
    return df.rename(columns=cols)

def make_blocks(df: pd.DataFrame, rules: List[str]) -> pd.DataFrame:
    """Generate blocking keys for each record"""
    blocks = []
    
    for rule in rules:
        if rule == "email_domain_last4":
            blocks.append(df["email"].apply(email_domain_last4))
        elif rule == "phone_last7":
            blocks.append(df["phone"].apply(phone_last7))
        elif rule == "name_fsa":
            blocks.append(df.apply(lambda r: name_fsa(r.get("first"), r.get("last"), r.get("postal")), axis=1))
        elif rule == "email_exact":
            blocks.append(df["email"].apply(email_exact))
    
    # Combine all blocking keys
    block_df = pd.concat(blocks, axis=1)
    block_df.columns = [f"block_{i}" for i in range(len(blocks))]
    
    return block_df.fillna("")

def score_pair(a: Dict[str, Any], b: Dict[str, Any], weights: Dict[str, float]) -> float:
    """Score similarity between two records"""
    score = 0.0
    
    # Email exact match
    if (a.get("email") and b.get("email") and 
        norm_email(a["email"]) == norm_email(b["email"])):
        score += weights.get("email_exact", 0.9)
    
    # Phone exact match
    if (a.get("phone") and b.get("phone") and 
        norm_phone(a["phone"]) == norm_phone(b["phone"])):
        score += weights.get("phone_exact", 0.7)
    
    # Name + address match
    if (a.get("last") and b.get("last") and 
        a["last"].lower() == b["last"].lower() and 
        (a.get("first", "")[:1].lower() == b.get("first", "")[:1].lower())):
        score += weights.get("name_address", 0.5)
    
    # Postal match
    if (fsa(a.get("postal")) and 
        fsa(a.get("postal")) == fsa(b.get("postal"))):
        score += weights.get("postal_match", 0.2)
    
    return min(score, 1.0)

def generate_pairs(df: pd.DataFrame, blocking_rules: List[str], 
                   weights: Dict[str, float], thresholds: Dict[str, float]) -> pd.DataFrame:
    """Generate candidate pairs within blocks and score them"""
    # Create blocking keys
    block_df = make_blocks(df, blocking_rules)
    
    # Create composite block key
    df["block_key"] = block_df.astype(str).agg("|".join, axis=1)
    
    # Debug: print unique block keys
    # print(f"Debug - Unique block keys: {df['block_key'].unique()[:5]}")
    
    pairs = []
    
    # Group by each unique blocking key
    for block_val, group in df.groupby("block_key"):
        if block_val == "|" * (len(blocking_rules) - 1):  # Skip empty blocks
            continue
            
        ids = list(group.index)
        
        # Generate all pairs within block
        for i, j in itertools.combinations(ids, 2):
            a = df.loc[i].to_dict()
            b = df.loc[j].to_dict()
            
            # Score the pair
            score = score_pair(a, b, weights)
            
            # Determine decision
            if score >= thresholds["auto_merge"]:
                decision = "auto_merge"
            elif score >= thresholds["needs_review"]:
                decision = "needs_review"
            else:
                decision = "no_match"
            
            pairs.append({
                "left": i,
                "right": j,
                "score": score,
                "decision": decision,
                "left_source": a.get("source", ""),
                "right_source": b.get("source", "")
            })
    
    return pd.DataFrame(pairs)
