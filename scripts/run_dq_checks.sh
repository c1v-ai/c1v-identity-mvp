#!/usr/bin/env bash
# Run DQ checks for all sources

set -euo pipefail

echo "🔒 Running Data Quality Checks..."

# Activate virtual environment
source .venv/bin/activate

# Set Python path
export PYTHONPATH=src

# Function to run checks for a source
run_check() {
    local source=$1
    local env=$2
    local contract="configs/contracts/${source}.yaml"
    local csv="data/synth/${source}.csv"
    
    if [ ! -f "$contract" ]; then
        echo "⚠️  Contract not found: $contract"
        return 1
    fi
    
    if [ ! -f "$csv" ]; then
        echo "⚠️  CSV not found: $csv"
        return 1
    fi
    
    echo ""
    echo "Checking $source in $env environment..."
    python -c "
from src.dq_gate.runner import run
from src.dq_gate.gate import decide_action, append_event
result = run('$contract', '$csv', '$env')
action = decide_action(result['severity'], '$env')
print(f'  Severity: {result[\"severity\"]}')
print(f'  Action: {action}')
print(f'  Issues: {len(result[\"issues\"])}')
append_event(result, action)
"
}

# Check which environment to use
ENV=${1:-staging}

echo "Environment: $ENV"

# Run checks for all sources
for source in financial leads sales; do
    run_check $source $ENV
done

echo ""
echo "✅ DQ checks complete!"
echo ""
echo "View detailed results:"
echo "  cat reports/dq_events.csv | tail -20"
echo ""
echo "Or run the Streamlit app for interactive view:"
echo "  ./scripts/run_demo.sh"
