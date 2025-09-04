# Deploying to Streamlit Community Cloud

## Prereqs
- Repo pushed to GitHub (public or private).
- `requirements.txt` includes: pandas, pyyaml, streamlit.
- Entry point: `src/demo/streamlit_app.py`.
- `runtime.txt` set to `3.11`.

## One-time setup
1. Go to https://share.streamlit.io → New app.
2. Select this GitHub repo/branch.
3. Set Main file path: `src/demo/streamlit_app.py`.
4. Advanced settings → Secrets (TOML):
   ```toml
   APP_ENV = "prod_week1"
   SLACK_WEBHOOK = "https://hooks.slack.com/services/REDACTED"
   JIRA_PROJECT = "DQ"
   JIRA_ASSIGNEE_EMAIL = "owner@company.com"
   ```
5. Environment variables (if needed):
   - `PYTHONPATH=src`
   - `ASKDATA_SIMULATE=1`

## Deploy
Click Deploy. Streamlit installs requirements and starts the app.

### Live app URL (example)
If your app deploys under a generated subdomain, it will look like:

```
https://c1v-identity-mvp-meyapegxt3g6wxvpqpxjal.streamlit.app
```

## Notes
- `reports/` is ephemeral in Cloud; fine for MVP.
- For persistence later, switch to object storage.
- To update: push to the configured branch; Cloud redeploys automatically.

## Troubleshooting
- ImportError: ensure `sys.path.append(<repo>/src)` exists near the top of `streamlit_app.py`.
- Missing contracts: confirm `configs/contracts/*.yaml` is present.
- Permissions: ensure app can write `reports/`.
- Stale secrets: edit in App → Settings → Secrets; redeploy.
