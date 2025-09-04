# Makefile for Preppr application testing and development

.PHONY: test test-unit test-integration test-api test-coverage test-fast test-all
.PHONY: test-nutrition test-subscription test-tips test-meal-planning test-shopping test-admin
.PHONY: coverage coverage-html coverage-xml lint format clean install help

# Variables
PYTHON = python3
PIP = pip3
TEST_RUNNER = python run_tests.py

# Default target
help:
	@echo "Preppr Development Commands"
	@echo "=========================="
	@echo ""
	@echo "Testing:"
	@echo "  test              - Run all tests (excluding slow)"
	@echo "  test-fast         - Run fast tests only (unit + api)"
	@echo "  test-unit         - Run unit tests"
	@echo "  test-integration  - Run integration tests"
	@echo "  test-api          - Run API tests"
	@echo "  test-all          - Run all tests including slow ones"
	@echo ""
	@echo "Feature-specific tests:"
	@echo "  test-nutrition    - Run nutrition tracking tests"
	@echo "  test-subscription - Run subscription and tier tests"
	@echo "  test-tips         - Run tips system tests"
	@echo "  test-meal-planning- Run meal planning tests"
	@echo "  test-shopping     - Run shopping and pantry tests"
	@echo "  test-admin        - Run admin and promo code tests"
	@echo ""
	@echo "Coverage:"
	@echo "  coverage          - Run tests with coverage report"
	@echo "  coverage-html     - Generate HTML coverage report"
	@echo "  coverage-xml      - Generate XML coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint              - Run code linting"
	@echo "  format            - Format code with black"
	@echo ""
	@echo "Setup:"
	@echo "  install           - Install dependencies"
	@echo "  clean             - Clean temporary files"

# Test commands
test:
	$(TEST_RUNNER) --category all

test-fast:
	$(TEST_RUNNER) --fast

test-unit:
	$(TEST_RUNNER) --category unit

test-integration:
	$(TEST_RUNNER) --category integration

test-api:
	$(TEST_RUNNER) --category api

test-all:
	$(TEST_RUNNER) --category all --ci

# Feature-specific test commands
test-nutrition:
	$(TEST_RUNNER) --category nutrition

test-subscription:
	$(TEST_RUNNER) --category subscription

test-tips:
	$(TEST_RUNNER) --category tips

test-meal-planning:
	$(TEST_RUNNER) --category meal_planning

test-shopping:
	$(TEST_RUNNER) --category shopping,pantry

test-admin:
	$(TEST_RUNNER) --category admin,promo_codes

# Coverage commands
coverage:
	$(TEST_RUNNER) --coverage

coverage-html:
	$(TEST_RUNNER) --coverage --html-cov

coverage-xml:
	$(TEST_RUNNER) --coverage
	$(PYTHON) -m coverage xml

# Code quality commands
lint:
	@echo "Running flake8..."
	-$(PYTHON) -m flake8 src tests --max-line-length=100 --ignore=E203,W503
	@echo "Running pylint..."
	-$(PYTHON) -m pylint src --disable=C0111,C0103,R0903,R0913

format:
	@echo "Formatting with black..."
	$(PYTHON) -m black src tests --line-length=100
	@echo "Sorting imports with isort..."
	$(PYTHON) -m isort src tests --profile black

# Setup and maintenance
install:
	$(PIP) install -r requirements.txt
	$(PIP) install pytest pytest-cov pytest-mock pytest-timeout pytest-xdist
	$(PIP) install black flake8 pylint isort

clean:
	@echo "Cleaning temporary files..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf coverage.xml
	rm -rf coverage.json
	rm -rf .coverage.*

# CI/CD commands
ci-test:
	$(TEST_RUNNER) --ci

ci-install:
	$(PIP) install -r requirements.txt
	$(PIP) install pytest pytest-cov pytest-mock pytest-timeout pytest-xdist coverage

# Development shortcuts
dev: install test-fast

check: lint test-fast

full-check: lint test-all coverage-html