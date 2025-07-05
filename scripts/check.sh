#!/bin/bash
# Run all code quality checks

set -e

echo "🔍 Running code quality checks..."
echo

echo "📐 Checking formatting with black..."
black --check netrunner_proxy tests || (echo "❌ Black check failed. Run 'make format' to fix." && exit 1)
echo "✅ Black check passed"
echo

echo "📦 Checking imports with isort..."
isort --check-only netrunner_proxy tests || (echo "❌ isort check failed. Run 'make format' to fix." && exit 1)
echo "✅ isort check passed"
echo

echo "🔎 Running flake8..."
flake8 netrunner_proxy tests || (echo "❌ Flake8 check failed" && exit 1)
echo "✅ Flake8 check passed"
echo

echo "🏷️ Running mypy type checks..."
mypy netrunner_proxy || (echo "❌ mypy check failed" && exit 1)
echo "✅ mypy check passed"
echo

echo "📊 Running pylint..."
pylint netrunner_proxy
echo

echo "✅ All checks completed!"