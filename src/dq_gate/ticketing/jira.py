import os
try:
    import streamlit as st
    def _secret(key, default=None):
        return st.secrets.get(key, default) if hasattr(st, "secrets") else os.getenv(key, default)
except Exception:
    def _secret(key, default=None):
        return os.getenv(key, default)

def create(project_key: str | None, summary: str, description: str, assignee_email: str | None, priority: str = "Medium"):
    """Create JIRA ticket (stub for MVP)"""
    proj = project_key or _secret("JIRA_PROJECT", "DQ")
    assignee = assignee_email or _secret("JIRA_ASSIGNEE_EMAIL", "owner@company.com")
    print(f"[JIRA STUB] Creating ticket in project: {proj}")
    print(f"  Summary: {summary}")
    print(f"  Assignee: {assignee}")
    print(f"  Priority: {priority}")
    print(f"  Description:\n{description}")
    # Real integration would go here
    return f"STUB-{proj}-001"
