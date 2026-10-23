.PHONY: all lint format typecheck test coverage fetch extract match enrich aggregate pipeline performance-test install install-dev preprocess test-all test-python test-react test-e2e test-watch test-coverage test-parallel test-slow test-fast test-unit test-integration test-api start-servers stop-servers server-status restart-servers lint-count lint-e501 lint-f401 lint-f841 lint-auto-fix lint-format lint-systematic publish-data

all: preprocess lint format typecheck test

# Preprocess YAML catalogs
preprocess:
	python sotd/utils/yaml_preprocessor.py

# Lint with Ruff
lint:
	ruff check .

# Enhanced linting targets for systematic error fixing
lint-count:
	@echo "=== LINTER ERROR COUNTS ==="
	@echo "Total errors: $$(ruff check . | wc -l)"
	@echo "E501 (line length): $$(ruff check . --select E501 | wc -l)"
	@echo "F401 (unused imports): $$(ruff check . --select F401 | wc -l)"
	@echo "F841 (unused variables): $$(ruff check . --select F841 | wc -l)"
	@echo "E401 (multiple imports): $$(ruff check . --select E401 | wc -l)"
	@echo "I001 (import sorting): $$(ruff check . --select I001 | wc -l)"

lint-e501:
	@echo "=== E501 LINE LENGTH ERRORS ==="
	ruff check . --select E501

lint-f401:
	@echo "=== F401 UNUSED IMPORT ERRORS ==="
	ruff check . --select F401

lint-f841:
	@echo "=== F841 UNUSED VARIABLE ERRORS ==="
	ruff check . --select F841

lint-auto-fix:
	@echo "=== AUTO-FIXING FIXABLE ERRORS ==="
	ruff check . --fix

lint-format:
	@echo "=== FORMATTING FILES (fixes most E501 errors) ==="
	ruff format .
	black .

# Systematic linter error fixing workflow
lint-systematic:
	@echo "=== SYSTEMATIC LINTER ERROR FIXING WORKFLOW ==="
	@echo "Step 1: Getting current error counts..."
	@$(MAKE) lint-count
	@echo ""
	@echo "Step 2: Auto-fixing fixable errors..."
	@$(MAKE) lint-auto-fix
	@echo ""
	@echo "Step 3: Formatting files (fixes most E501 errors)..."
	@$(MAKE) lint-format
	@echo ""
	@echo "Step 4: Getting updated error counts..."
	@$(MAKE) lint-count
	@echo ""
	@echo "=== WORKFLOW COMPLETE ==="
	@echo "Check linter_errors_todo.md for progress tracking"
	@echo "Run 'make lint-e501', 'make lint-f401', 'make lint-f841' for remaining errors"

# Format code: Black first, then Ruff's auto-formatter (optional)
format: ruff-format
	black .

ruff-format:
	ruff format .

typecheck:
	pyright

# =============================================================================
# SERVER MANAGEMENT
# =============================================================================

# Start servers for testing
start-servers:
	@echo "Starting servers for testing..."
	cd webui && ./scripts/manage-servers.sh start
	@echo "Waiting for servers to be ready..."
	@sleep 5
	@echo "Servers should be ready now"

# Stop servers
stop-servers:
	@echo "Stopping servers..."
	cd webui && ./scripts/manage-servers.sh stop

# Check server status
server-status:
	@echo "Checking server status..."
	cd webui && ./scripts/manage-servers.sh status

# Restart servers (clean restart)
restart-servers:
	@echo "Restarting servers..."
	cd webui && ./scripts/manage-servers.sh stop
	@sleep 2
	cd webui && ./scripts/manage-servers.sh start
	@echo "Waiting for servers to be ready..."
	@sleep 5
	@echo "Servers restarted and ready"

# =============================================================================
# TEST TARGETS
# =============================================================================

# Main test target - runs all tests
test: test-python

# Run all test types (Python + React + E2E)
test-all: test-python test-react test-e2e

# Python pipeline tests (default test target)
test-python:
	PYTHONPATH=. pytest tests/

# React/TypeScript unit tests (with server management)
test-react: restart-servers
	@echo "Running React tests..."
	cd webui && npm run test
	@echo "Stopping servers after React tests..."
	cd webui && ./scripts/manage-servers.sh stop

# React tests in watch mode (with server management)
test-react-watch: restart-servers
	@echo "Running React tests in watch mode..."
	cd webui && npm run test:watch
	@echo "Stopping servers after React tests..."
	cd webui && ./scripts/manage-servers.sh stop

# React tests with coverage (with server management)
test-react-coverage: restart-servers
	@echo "Running React tests with coverage..."
	cd webui && npm run test:coverage
	@echo "Stopping servers after React tests..."
	cd webui && ./scripts/manage-servers.sh stop

# Playwright end-to-end tests (with server management)
test-e2e: start-servers
	@echo "Running E2E tests..."
	cd webui && npm run test:e2e
	@echo "Stopping servers after E2E tests..."
	cd webui && ./scripts/manage-servers.sh stop

# Playwright tests in UI mode (interactive) - with server management
test-e2e-ui-interactive: start-servers
	@echo "Running E2E tests in UI mode..."
	cd webui && npm run test:e2e:ui
	@echo "Stopping servers after E2E tests..."
	cd webui && ./scripts/manage-servers.sh stop

# Playwright tests in headed mode (visible browser) - with server management
test-e2e-headed: start-servers
	@echo "Running E2E tests in headed mode..."
	cd webui && npm run test:e2e:headed
	@echo "Stopping servers after E2E tests..."
	cd webui && ./scripts/manage-servers.sh stop

# Playwright tests in debug mode - with server management
test-e2e-debug: start-servers
	@echo "Running E2E tests in debug mode..."
	cd webui && npm run test:e2e:debug
	@echo "Stopping servers after E2E tests..."
	cd webui && ./scripts/manage-servers.sh stop

# Playwright tests in background mode (non-blocking) - with server management
test-e2e-background: start-servers
	@echo "Running E2E tests in background mode..."
	cd webui && ./scripts/auto-playwright.sh
	@echo "Stopping servers after E2E tests..."
	cd webui && ./scripts/manage-servers.sh stop

# Quick E2E tests (Chromium only, basic tests) - with server management
test-e2e-quick: start-servers
	@echo "Running quick E2E tests..."
	cd webui && npx playwright test --project=chromium
	@echo "Stopping servers after E2E tests..."
	cd webui && ./scripts/manage-servers.sh stop

# All E2E tests across all browsers - with server management
test-e2e-all: start-servers
	@echo "Running all E2E tests across browsers..."
	cd webui && npx playwright test
	@echo "Stopping servers after E2E tests..."
	cd webui && ./scripts/manage-servers.sh stop

# Monitor E2E test logs
test-e2e-monitor:
	cd webui && ./scripts/monitor-tests.sh

# Watch E2E tests - with server management
test-e2e-watch: start-servers
	@echo "Running E2E tests in watch mode..."
	cd webui && npm run test:e2e:ui
	@echo "Stopping servers after E2E tests..."
	cd webui && ./scripts/manage-servers.sh stop

# =============================================================================
# PYTHON TEST VARIATIONS
# =============================================================================

# Fast Python tests (parallel, quiet)
test-fast:
	PYTHONPATH=. pytest tests/ -n 4 -q

# Parallel Python tests (auto-detect cores)
test-parallel:
	PYTHONPATH=. pytest tests/ -n auto -q

# Slow Python tests (with timing info)
test-slow:
	PYTHONPATH=. pytest tests/ --durations=10 -v

# Python tests with coverage
test-coverage:
	pytest --cov=sotd --cov-report=term-missing tests/

# Python tests with HTML coverage report
test-coverage-html:
	pytest --cov=sotd --cov-report=html tests/
	@echo "Coverage report available at htmlcov/index.html"

# Python integration tests (requires API server)
test-integration:
	PYTHONPATH=. pytest tests/ -m integration

# Python integration directory tests (no API server required)
test-integration-dir:
	PYTHONPATH=. pytest tests/integration/

# Production catalog integration tests (uses production YAML catalogs)
# These tests validate catalog integrity and should be run separately
# Uses pytest marker to select only production tests
test-production:
	PYTHONPATH=. pytest tests/integration/ -m production -v

# =============================================================================
# REACT TEST VARIATIONS (WITH SERVER MANAGEMENT)
# =============================================================================

# React unit tests only - with server management
test-react-unit: start-servers
	@echo "Running React unit tests..."
	cd webui && npm run test:unit
	@echo "Stopping servers after React unit tests..."
	cd webui && ./scripts/manage-servers.sh stop

# React integration tests - with server management
test-react-integration: start-servers
	@echo "Running React integration tests..."
	cd webui && npm test -- --testPathPattern=integration
	@echo "Stopping servers after React integration tests..."
	cd webui && ./scripts/manage-servers.sh stop

# React API tests - with server management
test-react-api: start-servers
	@echo "Running React API tests..."
	cd webui && npm test -- --testPathPattern=api
	@echo "Stopping servers after React API tests..."
	cd webui && ./scripts/manage-servers.sh stop

# =============================================================================
# E2E TEST VARIATIONS (WITH SERVER MANAGEMENT)
# =============================================================================

# E2E tests for specific browser - with server management
test-e2e-chromium: start-servers
	@echo "Running E2E tests for Chromium..."
	cd webui && npx playwright test --project=chromium
	@echo "Stopping servers after E2E tests..."
	cd webui && ./scripts/manage-servers.sh stop

test-e2e-firefox: start-servers
	@echo "Running E2E tests for Firefox..."
	cd webui && npx playwright test --project=firefox
	@echo "Stopping servers after E2E tests..."
	cd webui && ./scripts/manage-servers.sh stop

test-e2e-webkit: start-servers
	@echo "Running E2E tests for WebKit..."
	cd webui && npx playwright test --project=webkit
	@echo "Stopping servers after E2E tests..."
	cd webui && ./scripts/manage-servers.sh stop

# E2E tests for specific test files - with server management
test-e2e-basic: start-servers
	@echo "Running basic E2E tests..."
	cd webui && npx playwright test basic.spec.ts
	@echo "Stopping servers after E2E tests..."
	cd webui && ./scripts/manage-servers.sh stop

test-e2e-api: start-servers
	@echo "Running API E2E tests..."
	cd webui && npx playwright test api-integration.spec.ts
	@echo "Stopping servers after E2E tests..."
	cd webui && ./scripts/manage-servers.sh stop

test-e2e-ui: start-servers
	@echo "Running UI E2E tests..."
	cd webui && npx playwright test ui-components.spec.ts
	@echo "Stopping servers after E2E tests..."
	cd webui && ./scripts/manage-servers.sh stop

# =============================================================================
# PIPELINE PHASE TARGETS
# =============================================================================

# Individual phase targets (with --force flag as per development rules)
fetch:
	python sotd/fetch/run.py --month 2025-05 --force

extract:
	python sotd/extract/run.py --month 2025-05 --force

match:
	python sotd/match/run.py --month 2025-05 --force

enrich:
	python sotd/enrich/run.py --month 2025-05 --force

aggregate:
	python sotd/aggregate/run.py --month 2025-05 --force

# Pipeline targets (using unified run.py orchestration)
pipeline:
	python run.py --month 2025-05 --force

pipeline-debug:
	python run.py --month 2025-05 --force --debug

# Performance testing
performance-test:
	python run.py aggregate --month 2025-01 --force --debug
	python run.py aggregate --month 2025-02 --force --debug

# =============================================================================
# INSTALLATION TARGETS
# =============================================================================

# Install dependencies
install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt

# Install webui dependencies
install-webui:
	cd webui && npm install

# Install all dependencies (Python + WebUI)
install-all: install-dev install-webui

# =============================================================================
# DEVELOPMENT HELPERS
# =============================================================================

# Start development servers
dev-webui:
	cd webui && npm run dev

# Build webui for production
build-webui:
	cd webui && npm run build

# Lint webui
lint-webui:
	cd webui && npm run lint

# Type check webui
typecheck-webui:
	cd webui && npx tsc --noEmit

# Clean build artifacts
clean:
	rm -rf webui/dist webui/build webui/.next
	rm -rf htmlcov .coverage .pytest_cache
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# =============================================================================
# QUICK TEST SUITES (WITH SERVER MANAGEMENT)
# =============================================================================

# Quick test suite (fast Python tests + basic React tests) - with server management
test-quick: test-fast
	@echo "Running React unit tests..."
	cd webui && ./scripts/manage-servers.sh restart
	@sleep 5
	cd webui && npm run test:unit
	cd webui && ./scripts/manage-servers.sh stop

# Full test suite (all tests with coverage) - with server management
test-full: test-coverage
	@echo "Running React tests with coverage..."
	cd webui && ./scripts/manage-servers.sh start
	cd webui && npm run test:coverage
	cd webui && ./scripts/manage-servers.sh stop
	@echo "Running E2E tests..."
	cd webui && ./scripts/manage-servers.sh start
	cd webui && npx playwright test
	cd webui && ./scripts/manage-servers.sh stop

# CI test suite (comprehensive but fast) - with server management
test-ci: test-python
	@echo "Running React tests..."
	cd webui && ./scripts/manage-servers.sh start
	cd webui && npm run test
	cd webui && ./scripts/manage-servers.sh stop
	@echo "Running quick E2E tests..."
	cd webui && ./scripts/manage-servers.sh start
	cd webui && npx playwright test --project=chromium
	cd webui && ./scripts/manage-servers.sh stop

# Development test suite (watch mode for active development) - with server management
test-dev: test-python
	@echo "Starting servers for development testing..."
	cd webui && ./scripts/manage-servers.sh start
	@echo "Running React tests in watch mode..."
	@echo "Press Ctrl+C to stop the development test suite"
	cd webui && npm run test:watch

# =============================================================================
# DATA PUBLISHING
# =============================================================================

# Publish the slim public data bundle (aggregated slices) to the NAS
publish-data:  ## rsync the slim public data bundle to the NAS
	./scripts/publish-public-data.sh
