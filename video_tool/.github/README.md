# CI/CD Setup

This directory contains GitHub Actions workflows for automated testing and code quality checks.

## Workflows

### 🧪 Tests (`test.yml`)

Runs the full test suite on every push and pull request.

**Features:**
- **Multi-Python Testing**: Tests against Python 3.9, 3.10, and 3.11
- **FFmpeg Integration**: Installs FFmpeg on macOS runners
- **Coverage Reports**: Generates coverage reports and uploads to Codecov
- **Dependency Caching**: Caches pip dependencies for faster builds

**Triggers:**
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop` branches

**Running Time:** ~5-10 minutes per Python version

### 🔍 Linting (`lint.yml`)

Performs code quality checks and static analysis.

**Tools Used:**
- **Black**: Code formatting (100 char line length)
- **isort**: Import statement ordering
- **Flake8**: Style guide enforcement and error detection
- **mypy**: Static type checking
- **Bandit**: Security issue detection

**Triggers:**
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop` branches

**Running Time:** ~2-3 minutes

## Badges

Add these badges to your main README.md:

```markdown
[![Tests](https://github.com/thanhtungnguyenphp/OhCut/actions/workflows/test.yml/badge.svg)](https://github.com/thanhtungnguyenphp/OhCut/actions/workflows/test.yml)
[![Linting](https://github.com/thanhtungnguyenphp/OhCut/actions/workflows/lint.yml/badge.svg)](https://github.com/thanhtungnguyenphp/OhCut/actions/workflows/lint.yml)
[![codecov](https://codecov.io/gh/thanhtungnguyenphp/OhCut/branch/main/graph/badge.svg)](https://codecov.io/gh/thanhtungnguyenphp/OhCut)
```

## Local Development

### Running Tests Locally

```bash
# Install test dependencies
pip install pytest pytest-cov pyyaml

# Run all tests
pytest tests/ -v

# Run tests with coverage
pytest tests/ --cov=src --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Running Linting Locally

```bash
# Install linting tools
pip install black flake8 isort mypy bandit

# Format code with Black
black src/ tests/

# Sort imports
isort src/ tests/

# Run Flake8
flake8 src/

# Type checking
mypy src/ --ignore-missing-imports

# Security checks
bandit -r src/ -ll
```

### Pre-commit Checks

To ensure your code passes CI checks before pushing:

```bash
# Format and lint
black src/ tests/
isort src/ tests/
flake8 src/

# Run tests
pytest tests/ -v

# Type check
mypy src/ --ignore-missing-imports
```

## Configuration Files

- **`pyproject.toml`**: Configuration for Black, isort, pytest, mypy, and coverage
- **`.flake8`**: Flake8 linting rules and exclusions
- **`pytest.ini`**: Pytest configuration (if using separate file)

## Troubleshooting

### Tests Failing in CI but Passing Locally

1. **Python Version Mismatch**: Ensure you're testing with the same Python versions
2. **FFmpeg Not Available**: CI installs FFmpeg automatically, ensure it's in PATH locally
3. **Dependencies**: Check that `requirements.txt` is up to date

### Linting Failures

1. **Black Formatting**: Run `black src/ tests/` to auto-format
2. **Import Order**: Run `isort src/ tests/` to fix import ordering
3. **Flake8 Errors**: Address specific errors shown in the output

### Coverage Upload Fails

- Codecov uploads are non-blocking (`fail_ci_if_error: false`)
- Ensure Codecov token is set in repository secrets if repo is private

## Matrix Testing

The test workflow uses a matrix strategy to test against multiple Python versions:

```yaml
strategy:
  matrix:
    python-version: ['3.9', '3.10', '3.11']
```

This ensures compatibility across different Python versions.

## Future Enhancements

Potential additions for future CI/CD improvements:

- [ ] Performance regression testing
- [ ] Docker image building and publishing
- [ ] Automatic release creation on tags
- [ ] Integration tests with real video files
- [ ] Dependency vulnerability scanning (Dependabot, Safety)
- [ ] Code quality metrics (SonarCloud, Code Climate)

## Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Codecov Documentation](https://docs.codecov.com/)
- [Black Code Style](https://black.readthedocs.io/)
- [Flake8 Rules](https://flake8.pycqa.org/en/latest/user/error-codes.html)
