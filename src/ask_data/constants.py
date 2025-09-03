"""
Constants and configuration for Ask the Data module.
"""

# Guardrail limits
DRY_RUN_MAX_BYTES = 1_000_000_000  # 1 GB
ROW_CAP = 50_000
DEFAULT_WINDOW_DAYS = 90

# Router template patterns
ROUTER_PATTERNS = [
    # (regex_pattern, view_name, select_columns, default_days, description)
    (
        r"\brevenue\b.*\blast\s+(\d+)\s+days?", 
        "dm.metrics_revenue_daily", 
        ["date", "revenue"], 
        None,
        "Revenue by day for specified period"
    ),
    (
        r"\bdup(licate)?\b.*\brate\b.*\btrend\b", 
        "dm.metrics_dup_rate", 
        ["date", "dup_rate"], 
        90,
        "Duplicate rate trend over time"
    ),
    (
        r"\bmatch\b.*\buplift\b", 
        "dm.metrics_match_uplift", 
        ["date", "uplift"], 
        90,
        "Match rate uplift over time"
    ),
    (
        r"\bactive\s+customers?\b.*\blast\s+(\d+)\s+days?", 
        "dm.metrics_active_customers", 
        ["date", "active_customers"], 
        None,
        "Active customer count for specified period"
    ),
    (
        r"\border\b.*\bchannel\b.*\blast\s+(\d+)\s+days?", 
        "dm.fact_events_view", 
        ["event_date", "channel", "amount"], 
        None,
        "Orders by channel for specified period"
    )
]

# Allowed BigQuery views (semantic layer)
ALLOWED_VIEWS = {
    "dm.metrics_revenue_daily",
    "dm.metrics_dup_rate",
    "dm.metrics_match_uplift",
    "dm.metrics_active_customers",
    "dm.dim_customer_masked",
    "dm.fact_events_view",
}

# Error messages
ERROR_MESSAGES = {
    "dml_not_allowed": "DML operations (INSERT/UPDATE/DELETE) are not allowed",
    "select_star_not_allowed": "SELECT * is not allowed - specify columns explicitly",
    "view_not_allowed": "Only approved semantic layer views may be queried",
    "no_date_predicate": "Date partition predicate is required for performance",
    "query_too_large": "Query exceeds byte limit - refine filters or reduce scope",
    "too_many_rows": "Query would return too many rows - add filters or reduce scope"
}
