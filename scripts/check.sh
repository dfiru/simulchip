#!/bin/bash
# Run code quality checks

set -e

echo "🔍 Running code quality checks..."
echo

echo "📐 Checking formatting with black..."
black --check simulchip tests example.py || (echo "❌ Black check failed. Run 'black simulchip tests example.py' to fix." && exit 1)
echo "✅ Black check passed"
echo

echo "📦 Checking imports with isort..."
isort --check-only --profile black simulchip tests example.py || (echo "❌ isort check failed. Run 'isort --profile black simulchip tests example.py' to fix." && exit 1)
echo "✅ isort check passed"
echo

echo "🔎 Running flake8..."
flake8 simulchip tests example.py || (echo "❌ Flake8 check failed" && exit 1)
echo "✅ Flake8 check passed"
echo

echo "🏷️ Running mypy type checks..."
mypy simulchip tests example.py || (echo "❌ mypy check failed" && exit 1)
echo "✅ mypy check passed"
echo

echo "📊 Running pylint..."
pylint simulchip example.py
echo

echo "✅ All checks completed!"
