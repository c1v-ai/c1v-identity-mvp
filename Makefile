.PHONY: install test run-app clean test-dq test-identity scaffold-contracts run-unify metrics-export deploy-notes

export PYTHONPATH := src

install:
	pip install -r requirements.txt

test:
	pytest tests/ -q

test-dq:
	pytest tests/dq_gate/ -q

test-identity:
	pytest tests/identity/ -q

run-app:
	streamlit run src/demo/streamlit_app.py --server.port 8501

scaffold-contracts:
	python -m src.dq_gate.contract_scaffold data/synth/financial.csv financial fin-owner@company.com
	python -m src.dq_gate.contract_scaffold data/synth/leads.csv leads mkt-owner@company.com  
	python -m src.dq_gate.contract_scaffold data/synth/sales.csv sales sales-owner@company.com

run-unify:
	python -m src.identity.run_unify

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache

metrics-export:
	@echo "Exporting metrics snapshot..."
	@python -c "import pandas as pd; from src.dq_gate.gate import get_metrics; print(pd.DataFrame([get_metrics()]))"

deploy-notes:
	@echo "Push to GitHub and configure Streamlit Cloud:"
	@echo "  - Repo: c1v-ai/c1v-identity-mvp"
	@echo "  - Main file: src/demo/streamlit_app.py"
	@echo "  - Secrets: APP_ENV, SLACK_WEBHOOK, JIRA_PROJECT, JIRA_ASSIGNEE_EMAIL"
	@echo "  - Env vars: PYTHONPATH=src, ASKDATA_SIMULATE=1"
