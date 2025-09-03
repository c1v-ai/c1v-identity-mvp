#!/usr/bin/env bash
# Run the integrated Streamlit demo app with all modules

set -euo pipefail

echo "🚀 Starting C1V Identity Demo..."

# Activate virtual environment
source .venv/bin/activate

# Set Python path
export PYTHONPATH=src

# Optional: simulate mode for Ask the Data (no BigQuery required)
export ASKDATA_SIMULATE=1

# Start Streamlit
echo "Starting Streamlit on http://localhost:8501"
echo "Available tabs:"
echo "  - Single Match: Test individual record pairs"
echo "  - CSV Upload: Batch matching with ROI"
echo "  - Ask the Data: Natural language queries"
echo "  - DQ Gate: Data quality validation"
echo "  - Identity Unify: Deduplication and golden records"
echo ""
echo "Press Ctrl+C to stop"
echo ""

streamlit run src/demo/streamlit_app.py --server.port 8501
