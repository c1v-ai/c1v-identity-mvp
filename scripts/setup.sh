#!/usr/bin/env bash
# Setup script for C1V Identity MVP

set -e

echo "🔧 Setting up C1V Identity MVP..."

# Create virtual environment if not exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create necessary directories
echo "Creating directories..."
mkdir -p data/synth data/pairs reports configs/contracts

# Generate synthetic data if not exists
if [ ! -f "data/synth/leads.csv" ]; then
    echo "Generating synthetic data..."
    python src/gen/synth_from_schemas.py --dev
fi

# Generate DQ contracts if not exists
if [ ! -f "configs/contracts/financial.yaml" ]; then
    echo "Generating DQ contracts..."
    make scaffold-contracts
fi

echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Run tests: make test"
echo "  2. Start demo: ./scripts/run_demo.sh"
echo "  3. Run identity unification: make run-unify"
