#!/usr/bin/env bash
set -euo pipefail
source .venv/bin/activate
uvicorn src.serve.api:app --reload --port 8000
