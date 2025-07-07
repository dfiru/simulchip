.PHONY: help install install-dev format lint type-check test clean docs docs-serve all check

help:
	@echo "Available commands:"
	@echo "  make install       Install the package"
	@echo "  make install-dev   Install with development dependencies"
	@echo "  make format        Format code with black and isort"
	@echo "  make lint          Run linting checks"
	@echo "  make type-check    Run mypy type checking"
	@echo "  make test          Run tests"
	@echo "  make clean         Clean up cache files"
	@echo "  make docs          Build documentation"
	@echo "  make docs-serve    Build and serve documentation locally"
	@echo "  make check         Run all quality checks (lint, type-check, test)"
	@echo "  make all           Run format, lint, type-check, and test"

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

install-docs:
	pip install -e ".[docs]"

format:
	@echo "Running isort..."
	isort simulchip tests
	@echo "Running black..."
	black simulchip tests

lint:
	@echo "Running flake8..."
	flake8 simulchip tests
	@echo "Running pylint..."
	pylint simulchip

type-check:
	@echo "Running mypy..."
	mypy simulchip

test:
	@echo "Running tests..."
	pytest tests/ -v

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.coverage" -delete
	find . -type d -name "htmlcov" -exec rm -rf {} +
	rm -rf docs/build
	rm -rf docs/source/generated

docs:
	@echo "Building documentation..."
	cd docs && make html

docs-serve: docs
	@echo "Serving documentation at http://localhost:8000"
	cd docs/build/html && python -m http.server

check: lint type-check test

all: format lint type-check test
