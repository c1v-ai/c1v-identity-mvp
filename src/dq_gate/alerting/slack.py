def send(webhook: str, channel: str, text: str, severity: str = "INFO"):
    """Send alert to Slack (stub for MVP)"""
    emoji = {
        "RED": "🔴",
        "AMBER": "🟡", 
        "GREEN": "🟢",
        "INFO": "ℹ️"
    }
    
    print(f"[SLACK STUB] {emoji.get(severity, '')} → {channel}")
    print(f"  Webhook: {webhook}")
    print(f"  Message: {text}")
    
    # In production, would use:
    # requests.post(webhook, json={"channel": channel, "text": text})
