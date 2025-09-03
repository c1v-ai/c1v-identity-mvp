#!/usr/bin/env bash
set -euo pipefail
source .venv/bin/activate
pytest -q --maxfail=1 --disable-warnings --cov=src
