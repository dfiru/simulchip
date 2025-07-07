# Contributing

We welcome contributions to Simulchip! This guide will help you get started.

## Development Setup

1. Fork the repository on GitHub
2. Clone your fork locally:

   ```bash
   git clone https://github.com/yourusername/simulchip.git
   cd simulchip
   ```

3. Create a virtual environment:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

4. Install development dependencies:

   ```bash
   pip install -e ".[dev,docs]"
   pre-commit install
   ```

## Code Style

We use several tools to maintain code quality:

- **Black** for code formatting (88 character line length)
- **isort** for import organization
- **flake8** for linting
- **mypy** for type checking
- **pylint** for additional code quality checks

Run all checks:

```bash
make check
```

Or individually:

```bash
make format  # Run black and isort
make lint    # Run flake8, mypy, and pylint
make test    # Run pytest
```

## Contribution Guidelines

1. **All code must pass style checks** - Run `make check` before submitting
2. **New functionality must include tests** - We aim for high test coverage
3. **Update documentation** - Include docstrings and update docs if needed
4. **Follow existing patterns** - Match the code style of the surrounding code

## Submitting Changes

1. Create a feature branch:

   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes and commit:

   ```bash
   git add .
   git commit -m "Add your descriptive commit message"
   ```

3. Push to your fork:

   ```bash
   git push origin feature/your-feature-name
   ```

4. Open a Pull Request on GitHub

## Testing

Run the test suite:

```bash
make test
```

Run with coverage:

```bash
pytest --cov=simulchip tests/
```

## Documentation

Build documentation locally:

```bash
make docs
make docs-serve  # View at http://localhost:8000
```

## Code of Conduct

Please be respectful and constructive in all interactions. We're here to build something great together!
