# Umbrella-GovOps — developer harness.
# Run `make help` for the menu.

PY ?= python3
PIP ?= pip3
PYTEST ?= $(PY) -m pytest
NPM ?= npm
REPORTS_DIR := reports/harness

.DEFAULT_GOAL := help

# ----------------------------------------------------------------------------
# Discovery
# ----------------------------------------------------------------------------

.PHONY: help
help: ## Show this menu
	@awk 'BEGIN {FS = ":.*##"; printf "\nUmbrella-GovOps developer harness\n\nUsage: \033[36mmake <target>\033[0m\n\n"} \
		/^[a-zA-Z0-9_.-]+:.*?##/ { printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)
	@echo ""

# ----------------------------------------------------------------------------
# Bootstrap
# ----------------------------------------------------------------------------

.PHONY: install
install: ## Install Python dev/test dependencies
	$(PIP) install --upgrade pip
	$(PIP) install -e . pytest pyyaml jsonschema click

.PHONY: install-e2e
install-e2e: ## Install Playwright + Chromium for e2e
	cd tests/e2e && $(NPM) install --no-audit --no-fund
	cd tests/e2e && npx playwright install chromium

.PHONY: reports-dir
reports-dir:
	mkdir -p $(REPORTS_DIR)

# ----------------------------------------------------------------------------
# Suites
# ----------------------------------------------------------------------------

.PHONY: test-unit
test-unit: reports-dir ## Run unit suite (CLI + schemas + conformance)
	PYTHONPATH=. $(PYTEST) tests/unit/ tests/conformance/ -v \
		--junitxml=$(REPORTS_DIR)/junit-unit.xml

.PHONY: test-scale
test-scale: reports-dir ## Run scale suite (100 + 1000 controls; set SCALE_N=10000 for 10k)
	PYTHONPATH=. $(PYTEST) tests/scale/ -v \
		--junitxml=$(REPORTS_DIR)/junit-scale.xml

.PHONY: test-scale-10k
test-scale-10k: reports-dir ## Run the opt-in 10k-control scale test
	SCALE_N=10000 PYTHONPATH=. $(PYTEST) tests/scale/ -v -k 10k \
		--junitxml=$(REPORTS_DIR)/junit-scale-10k.xml

.PHONY: test-chaos
test-chaos: reports-dir ## Run chaos monkey (6 mutations + random walk)
	PYTHONPATH=. $(PYTEST) tests/chaos/ -v \
		--junitxml=$(REPORTS_DIR)/junit-chaos.xml

.PHONY: test-e2e
test-e2e: reports-dir ## Run Playwright e2e suite against the live site
	cd tests/e2e && npx playwright test --reporter=list

.PHONY: test-e2e-local
test-e2e-local: reports-dir ## Run Playwright against a local preview (BASE_URL=...)
	cd tests/e2e && BASE_URL=$${BASE_URL:-http://localhost:8080} npx playwright test --reporter=list

# ----------------------------------------------------------------------------
# Composite targets
# ----------------------------------------------------------------------------

.PHONY: test-py
test-py: test-unit test-scale test-chaos ## All Python suites (no e2e)

.PHONY: test-all
test-all: test-py test-e2e ## Full harness: unit + scale + chaos + e2e

.PHONY: harness-report
harness-report: ## Print the latest harness artifact paths
	@echo "Harness reports:"
	@ls -la $(REPORTS_DIR) 2>/dev/null || echo "  (no reports yet — run 'make test-all')"

# ----------------------------------------------------------------------------
# Housekeeping
# ----------------------------------------------------------------------------

.PHONY: clean
clean: ## Remove harness reports and pytest caches
	rm -rf $(REPORTS_DIR) .pytest_cache **/__pycache__
	cd tests/e2e && rm -rf node_modules test-results playwright-report

.PHONY: fmt
fmt: ## Format Python sources (best-effort, no hard dependency)
	@command -v ruff >/dev/null 2>&1 && ruff format . || echo "ruff not installed; skip"
