import csv, yaml, json
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

POLICY = None
EVENT_LOG = Path("reports/dq_events.csv")

def load_policy(path: str = "configs/gate_policy.yaml") -> dict:
    """Load gate policy"""
    global POLICY
    if POLICY is None:
        POLICY = yaml.safe_load(Path(path).read_text())
    return POLICY

def load_rbac(path: str = "configs/rbac.yaml") -> dict:
    """Load RBAC configuration"""
    return yaml.safe_load(Path(path).read_text())

def decide_action(severity: str, env: str, policy: dict = None) -> str:
    """Determine action based on severity and environment"""
    p = policy or load_policy()
    env_policy = p.get(env, p.get("default", {}))
    
    actions = {
        "GREEN": "PASS",
        "AMBER": env_policy.get("on_amber", "WARN"),
        "RED": env_policy.get("on_red", "BLOCK")
    }
    
    return actions.get(severity, "WARN")

def append_event(event: Dict[str, Any], action: str):
    """Append event to audit log"""
    EVENT_LOG.parent.mkdir(parents=True, exist_ok=True)
    
    headers = [
        "ts", "timestamp", "env", "source", "owner", 
        "severity", "action", "rule", "field", "detail"
    ]
    
    write_header = not EVENT_LOG.exists()
    
    with EVENT_LOG.open("a", newline="") as f:
        writer = csv.writer(f)
        
        if write_header:
            writer.writerow(headers)
        
        timestamp = datetime.fromtimestamp(event["ts"]).isoformat()
        
        if event["issues"]:
            for issue in event["issues"]:
                writer.writerow([
                    event["ts"],
                    timestamp,
                    event["env"],
                    event["source"],
                    event.get("owner", ""),
                    event["severity"],
                    action,
                    issue["rule"],
                    issue.get("field", ""),
                    issue.get("detail", "")
                ])
        else:
            # Log even when no issues (GREEN)
            writer.writerow([
                event["ts"],
                timestamp,
                event["env"],
                event["source"],
                event.get("owner", ""),
                event["severity"],
                action,
                "no_issues",
                "",
                ""
            ])

def get_metrics() -> Dict[str, Any]:
    """Calculate DQ metrics from event log"""
    if not EVENT_LOG.exists():
        return {
            "coverage_pct": 0,
            "prevented_defects": 0,
            "mttr_hours": 0
        }
    
    import pandas as pd
    df = pd.read_csv(EVENT_LOG)
    
    # Coverage: sources with at least one check
    unique_sources = df["source"].nunique()
    
    # Prevented defects: RED blocks in staging
    prevented = len(df[(df["severity"] == "RED") & (df["env"] == "staging")])
    
    return {
        "coverage_pct": min(unique_sources * 20, 100),  # Assume 5 sources = 100%
        "prevented_defects": prevented,
        "mttr_hours": 48  # Placeholder
    }
