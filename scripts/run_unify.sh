#!/usr/bin/env bash
# Run identity unification across all sources

set -euo pipefail

echo "🔗 Running Identity Unification..."

# Activate virtual environment
source .venv/bin/activate

# Set Python path
export PYTHONPATH=src

# Check if data exists
for source in financial leads sales; do
    if [ ! -f "data/synth/${source}.csv" ]; then
        echo "⚠️  Missing data: data/synth/${source}.csv"
        echo "Run ./scripts/setup.sh first"
        exit 1
    fi
done

# Run unification
echo "Processing sources: financial, leads, sales"
python -m src.identity.run_unify

echo ""
echo "✅ Identity unification complete!"
echo ""
echo "Results:"
echo "  - Golden records: reports/golden_contacts.csv"
echo "  - Match events: reports/unify_events.csv"
echo ""

# Show summary
if [ -f "reports/golden_contacts.csv" ]; then
    golden_count=$(wc -l < reports/golden_contacts.csv)
    echo "Golden records created: $((golden_count - 1))"
fi

if [ -f "reports/unify_events.csv" ]; then
    events_count=$(wc -l < reports/unify_events.csv)
    echo "Match decisions made: $((events_count - 1))"
fi

echo ""
echo "View results in Streamlit:"
echo "  ./scripts/run_demo.sh"
echo "  → Go to 'Identity Unify' tab"
