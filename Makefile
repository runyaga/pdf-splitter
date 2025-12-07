.PHONY: lint format typecheck test test-fast coverage quality clean install-dev help

# Default target
help:
	@echo "Available commands:"
	@echo "  make install-dev  - Install dev dependencies"
	@echo "  make lint         - Run ruff linter"
	@echo "  make lint-fix     - Run ruff linter with auto-fix"
	@echo "  make format       - Run ruff formatter"
	@echo "  make format-check - Check formatting without changes"
	@echo "  make typecheck    - Run mypy type checker"
	@echo "  make test         - Run pytest with coverage"
	@echo "  make test-fast    - Run pytest without coverage"
	@echo "  make coverage     - Generate HTML coverage report"
	@echo "  make quality      - Run all checks (lint + typecheck + test)"
	@echo "  make clean        - Remove build artifacts and caches"
	@echo "  make pre-commit   - Install pre-commit hooks"

# Install dev dependencies
install-dev:
	pip install -e ".[dev]"

# Linting
lint:
	ruff check src/ tests/

lint-fix:
	ruff check --fix src/ tests/

# Formatting
format:
	ruff format src/ tests/

format-check:
	ruff format --check src/ tests/

# Type checking
typecheck:
	mypy src/

# Testing
test:
	pytest --cov=src --cov-report=term-missing tests/

test-fast:
	pytest tests/

# Coverage report
coverage:
	pytest --cov=src --cov-report=html tests/
	@echo "Coverage report generated in htmlcov/index.html"

# Run all quality checks
quality: lint typecheck test

# Pre-commit hooks
pre-commit:
	pre-commit install
	@echo "Pre-commit hooks installed"

pre-commit-run:
	pre-commit run --all-files

# Clean up
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleaned build artifacts and caches"
