import os
try:
    import streamlit as st
    def _secret(key, default=None):
        return st.secrets.get(key, default) if hasattr(st, "secrets") else os.getenv(key, default)
except Exception:
    def _secret(key, default=None):
        return os.getenv(key, default)

def send(webhook: str | None, channel: str, text: str, severity: str = "INFO"):
    """Send alert to Slack (stub for MVP)"""
    emoji = {
        "RED": "🔴",
        "AMBER": "🟡", 
        "GREEN": "🟢",
        "INFO": "ℹ️"
    }
    hook = webhook or _secret("SLACK_WEBHOOK")
    print(f"[SLACK STUB] {emoji.get(severity, '')} → {channel}")
    print(f"  Webhook: {hook}")
    print(f"  Message: {text}")
    # Real call (disabled):
    # if hook:
    #     requests.post(hook, json={"channel": channel, "text": text})
