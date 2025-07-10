#!/bin/bash
# Run code quality checks

set -e

echo "🔍 Running code quality checks via pre-commit..."
echo

# Run all pre-commit hooks
pre-commit run --all-files || (echo "❌ Pre-commit checks failed" && exit 1)

echo
echo "📊 Running pylint (not included in pre-commit)..."
pylint simulchip cli example.py
echo

echo "✅ All checks completed!"
