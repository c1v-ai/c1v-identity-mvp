def create(project_key: str, summary: str, description: str, assignee_email: str, priority: str = "Medium"):
    """Create JIRA ticket (stub for MVP)"""
    print(f"[JIRA STUB] Creating ticket in project: {project_key}")
    print(f"  Summary: {summary}")
    print(f"  Assignee: {assignee_email}")
    print(f"  Priority: {priority}")
    print(f"  Description:\n{description}")
    
    # In production, would use:
    # jira_client.create_issue(project=project_key, summary=summary, ...)
    
    return f"STUB-{project_key}-001"
