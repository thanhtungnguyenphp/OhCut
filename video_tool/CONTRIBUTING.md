# Contributing to Video Tool

Thank you for your interest in contributing to Video Tool! This document provides guidelines and instructions for development.

## Development Setup

### Prerequisites

- Python 3.9 or higher
- FFmpeg installed
- Git

### Setting Up Development Environment

1. **Fork and clone the repository:**
   ```bash
   git clone https://github.com/yourusername/video-tool.git
   cd video-tool
   ```

2. **Create a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install development dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install -e .
   ```

4. **Verify installation:**
   ```bash
   video-tool --help
   pytest tests/
   ```

## Code Style Guidelines

### Python Style

We follow PEP 8 with some modifications:

- **Line length:** 100 characters maximum
- **Formatting:** Use `black` for automatic formatting
- **Imports:** Use `isort` for organizing imports
- **Type hints:** Use type hints for all function signatures

### Code Formatting

Before committing, run:

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Check linting
flake8 src/ tests/

# Type checking
mypy src/
```

### Naming Conventions

- **Functions:** `snake_case`
- **Classes:** `PascalCase`
- **Constants:** `UPPER_SNAKE_CASE`
- **Private methods:** `_leading_underscore`

### Docstrings

Use Google-style docstrings:

```python
def cut_by_duration(input_path: str, output_dir: str, segment_duration: int) -> list[str]:
    """Cut video into segments by duration.
    
    Args:
        input_path: Path to input video file.
        output_dir: Directory for output segments.
        segment_duration: Duration of each segment in seconds.
    
    Returns:
        List of output file paths.
    
    Raises:
        InvalidInputError: If input file doesn't exist or is invalid.
        FFmpegError: If FFmpeg command fails.
    """
    pass
```

## Testing Guidelines

### Writing Tests

- Write tests for all new features
- Aim for >80% code coverage
- Use meaningful test names: `test_<function>_<scenario>_<expected_result>`

### Test Structure

```python
def test_cut_video_by_duration_creates_correct_segments():
    """Test that cutting a video creates the expected number of segments."""
    # Arrange
    input_video = "test_data/sample.mp4"
    output_dir = "test_output"
    segment_duration = 60
    
    # Act
    result = cut_by_duration(input_video, output_dir, segment_duration)
    
    # Assert
    assert len(result) == 3
    assert all(Path(f).exists() for f in result)
```

### Running Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest --cov=src tests/

# Run specific test file
pytest tests/test_video_ops.py

# Run specific test
pytest tests/test_video_ops.py::test_cut_video_by_duration
```

## Git Workflow

### Branching Strategy

- `main`: Production-ready code
- `develop`: Development branch
- `feature/<name>`: New features
- `bugfix/<name>`: Bug fixes
- `hotfix/<name>`: Urgent fixes

### Commit Messages

Follow conventional commits:

```
<type>(<scope>): <subject>

<body>

<footer>
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting
- `refactor`: Code refactoring
- `test`: Tests
- `chore`: Maintenance

Examples:
```
feat(video-ops): add support for H.265 encoding

Implemented H.265 encoding with hardware acceleration support.
Falls back to H.264 if H.265 is not available.

Closes #123
```

### Pull Request Process

1. Create a feature branch from `develop`
2. Make your changes
3. Write/update tests
4. Update documentation
5. Run tests and linting
6. Create pull request to `develop`
7. Wait for code review
8. Address feedback
9. Merge after approval

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
Describe testing performed

## Checklist
- [ ] Code follows style guidelines
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] All tests pass
- [ ] No linting errors
```

## Project Structure

```
video_tool/
├── src/
│   ├── cli/              # Command-line interface
│   │   └── main.py       # CLI entry point
│   ├── core/             # Core functionality
│   │   ├── ffmpeg_runner.py
│   │   ├── video_ops.py
│   │   ├── audio_ops.py
│   │   └── profiles.py
│   ├── pipelines/        # Workflow pipelines
│   │   └── movie_pipeline.py
│   └── utils/            # Utilities
│       ├── file_utils.py
│       └── logger.py
├── tests/                # Tests mirror src/ structure
│   ├── test_ffmpeg_runner.py
│   ├── test_video_ops.py
│   └── ...
├── configs/              # Configuration files
│   ├── profiles.yaml
│   └── logging.yaml
└── logs/                 # Log files (git ignored)
```

## Adding New Features

### 1. Plan

- Check if issue exists, create if not
- Discuss approach in issue
- Get feedback before implementing

### 2. Implement

- Create feature branch
- Write code following guidelines
- Add docstrings and type hints
- Handle errors appropriately

### 3. Test

- Write unit tests
- Write integration tests if needed
- Ensure all tests pass
- Check code coverage

### 4. Document

- Update README if needed
- Add docstrings
- Update CHANGELOG
- Add usage examples

### 5. Submit

- Create pull request
- Fill out PR template
- Wait for review
- Address feedback

## Common Development Tasks

### Adding a New Video Operation

1. Add function to `src/core/video_ops.py`
2. Write tests in `tests/test_video_ops.py`
3. Add CLI command in `src/cli/main.py`
4. Update README with usage example

### Adding a New Configuration Option

1. Update `configs/profiles.yaml` or relevant config
2. Update Pydantic model if exists
3. Update documentation
4. Add validation

### Fixing a Bug

1. Create test that reproduces bug
2. Fix the bug
3. Verify test passes
4. Check for similar bugs
5. Update CHANGELOG

## Questions?

- Open an issue for bugs
- Open a discussion for questions
- Check existing issues/discussions first

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on the code, not the person
- Help others learn

Thank you for contributing to Video Tool!
