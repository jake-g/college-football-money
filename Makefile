# Money vs winning in college football.
#
#   make setup    create .venv and install the package
#   make data     download finances + this season
#   make report   rebuild charts and the markdown report
#   make check    lint + tests

SHELL := /bin/bash
.DEFAULT_GOAL := help

PY := .venv/bin/python
SEASON ?= 2026
SEASONS ?= 2023 2024 2025 2026
WORKERS ?= 8

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

.PHONY: setup
setup: ## Create .venv and install the package with dev tools
	python3 -m venv .venv
	$(PY) -m pip install --quiet --upgrade pip
	$(PY) -m pip install --quiet -e ".[dev]"
	-$(PY) -m pre_commit install
	@echo "Ready. Next: make data"

.PHONY: money
money: ## Download federal EADA athletics finance filings
	$(PY) -m cfbmoney money

.PHONY: fetch
fetch: ## Pull this season's results and stats from ESPN
	$(PY) -m cfbmoney --season $(SEASON) --workers $(WORKERS) fetch

.PHONY: history
history: ## Pull prior seasons for the trend charts
	@for s in $(SEASONS); do $(PY) -m cfbmoney --season $$s --workers $(WORKERS) fetch || exit 1; done

.PHONY: data
data: money fetch ## Download finances and the current season

.PHONY: analyze
analyze: ## Correlations and regression, printed to stdout
	$(PY) -m cfbmoney --season $(SEASON) analyze

.PHONY: report
report: ## Rebuild the charts and the markdown report
	$(PY) -m cfbmoney --season $(SEASON) --predictor football_expenses report

.PHONY: panel
panel: ## Pool seasons and trend the correlation
	$(PY) -m cfbmoney --seasons $(SEASONS) panel

.PHONY: refresh
refresh: ## Weekly in-season update (fetch fresh results + rebuild report)
	$(PY) -m cfbmoney --season $(SEASON) --workers $(WORKERS) --predictor football_expenses refresh

.PHONY: format
format: ## Auto-format and auto-fix
	$(PY) -m ruff format src tests
	$(PY) -m ruff check --fix src tests

.PHONY: lint
lint: ## Lint without modifying files
	$(PY) -m ruff check src tests

.PHONY: test
test: ## Run the unit tests
	$(PY) -m pytest

.PHONY: check
check: lint test ## Lint + tests

.PHONY: clean
clean: ## Drop caches; keeps reports and processed data
	rm -rf .pytest_cache .ruff_cache data/raw/espn
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +
