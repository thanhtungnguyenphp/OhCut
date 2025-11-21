# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

Video Tool is a Python-based CLI application for automated video and audio processing using FFmpeg. The project is in **Phase 1 Complete** status with ~75% test coverage and is preparing for Phase 2 enhancements.

**Key Technologies:** Python 3.9+, FFmpeg, Typer (CLI), Rich (output), Pydantic (validation)

## Commands

### Development Setup
```bash
# Create virtual environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
pip install -e .

# Verify FFmpeg is installed
ffmpeg -version
```

### Testing
```bash
# Run all tests
pytest tests/ -v

# Run with coverage report
pytest tests/ -v --cov=src --cov-report=term --cov-report=html

# Run specific test file
pytest tests/test_video_ops.py -v

# Run only integration tests (slower, use real FFmpeg)
pytest tests/ -v -m integration

# Run without integration tests (faster)
pytest tests/ -v -m "not integration"
```

### Code Quality
```bash
# Format code (line length: 100)
black src/ tests/

# Sort imports
isort src/ tests/

# Lint
flake8 src/ tests/

# Type check
mypy src/ --ignore-missing-imports

# Run all quality checks at once
black src/ tests/ && isort src/ tests/ && flake8 src/ tests/
```

### Running the CLI
```bash
# Install in development mode first
pip install -e .

# Basic commands
video-tool info -i movie.mp4
video-tool cut -i movie.mp4 -o ./output -d 11
video-tool concat -i part1.mp4 -i part2.mp4 -o final.mp4
video-tool audio extract -i movie.mp4 -o audio.m4a --codec copy
video-tool profiles list

# Global options (work with all commands)
video-tool --verbose cut -i movie.mp4 -o ./output      # Debug logging
video-tool --dry-run cut -i movie.mp4 -o ./output -d 11  # Preview without execution
video-tool --log-file custom.log cut -i movie.mp4 -o ./output  # Custom log file
```

### CI/CD
```bash
# CI/CD runs automatically on push/PR to main/develop branches
# Workflows: .github/workflows/test.yml, .github/workflows/lint.yml
# Test matrix: Python 3.9, 3.10, 3.11 on macOS runners
```

## Architecture

### High-Level Structure
```
video_tool/
├── src/
│   ├── cli/              # CLI layer - Typer commands, user interaction
│   ├── core/             # Core business logic - FFmpeg operations
│   ├── pipelines/        # Future: workflow orchestration (Phase 2+)
│   └── utils/            # Shared utilities - logging, file operations
├── tests/                # Mirrors src/ structure
├── configs/              # YAML configuration files
└── logs/                 # Runtime logs (gitignored)
```

### Core Modules

**`src/core/ffmpeg_runner.py`** - FFmpeg wrapper
- `run_ffmpeg()`: Executes FFmpeg with progress parsing and error handling
- `parse_ffmpeg_progress()`: Parses stderr for frame/time/speed info
- Returns structured dict with success/stdout/stderr/returncode
- All FFmpeg operations go through this module for consistency

**`src/core/video_ops.py`** - Video operations
- `cut_by_duration()`: Segments video using FFmpeg segment muxer
- `cut_by_timestamps()`: Cuts video at specific time points
- `concat_videos()`: Concatenates multiple videos with codec validation
- Supports both codec copy mode (fast) and re-encoding with profiles

**`src/core/audio_ops.py`** - Audio operations
- `extract_audio()`: Extracts audio track (copy or re-encode)
- `replace_audio()`: Replaces video audio track
- Handles codec validation and bitrate settings

**`src/core/profiles.py`** - Encoding profile system
- 11 built-in profiles: movie, clip, web, mobile, quality-based (CRF)
- `Profile` dataclass with validation
- `get_profile()`, `list_profiles()`: Profile management
- Profiles configured in `configs/profiles.yaml`

**`src/utils/logger.py`** - Logging system
- `setup_logging()`: Configures from `configs/logging.yaml`
- `log_operation()`: Context manager for structured operation logging
- Thread-local context storage for nested operations
- Rotating file handler (10MB, 5 backups)

**`src/utils/file_utils.py`** - File operations
- `validate_input_file()`: Checks file existence and readability
- `get_video_info()`: Uses ffprobe to extract video metadata
- `check_disk_space()`: Validates sufficient space before operations
- `ensure_output_dir()`: Creates directories with proper permissions

**`src/cli/main.py`** - CLI entry point
- Typer-based commands with rich console output
- Global options: --verbose, --dry-run, --log-file
- Subcommands: cut, concat, info, audio, profiles, version
- FFmpeg availability check on startup

### Important Patterns

**Error Handling**
- Custom exceptions: `FFmpegError`, `InvalidInputError`, `ProfileError`
- Always validate inputs before FFmpeg execution
- Log errors with full context before raising

**Codec Copy vs Re-encoding**
- Default behavior: codec copy (stream copy) for speed
- Use `--no-copy` flag to force re-encoding
- When re-encoding, apply profile with `--profile <name>`
- Re-encoding uses profile settings or defaults: libx264, aac, medium preset

**FFmpeg Argument Building**
- Build args as list: `["-i", input_path, "-c", "copy", output_path]`
- Log full command before execution
- Use `-c copy` for stream copy, `-c:v codec -c:a codec` for re-encoding

**Profile Application** ✅ PRODUCTION READY (Phase 2 Task 2.1 complete)
- Profiles define video/audio codecs, bitrates, resolutions, presets
- Hardware acceleration: VideoToolbox on macOS (hevc_videotoolbox)
- When `copy_codec=False`, apply profile settings to FFmpeg args
- Implementation: `video_ops.py:cut_by_duration()` lines 120-168
- Implementation: `video_ops.py:concat_videos()` lines 443-467
- Performance: 4-5x realtime (hardware), 2-3x realtime (software)
- Size reduction: 20-30% with maintained quality

## Development Guidelines

### Adding New Video Operations
1. Add function to `src/core/video_ops.py` with comprehensive docstring
2. Validate inputs using `utils/file_utils.py` helpers
3. Build FFmpeg args list, support both copy and re-encode modes
4. Execute via `ffmpeg_runner.run_ffmpeg()`
5. Add CLI command in `src/cli/main.py` with rich output
6. Write unit tests in `tests/test_video_ops.py` using mocks
7. Write integration test in `tests/test_ffmpeg_integration.py` if needed

### Testing Strategy
- **Unit tests**: Mock FFmpeg calls, test logic and arg building
- **Integration tests**: Use real FFmpeg with small test videos
- Test fixtures: `tests/fixtures/generate_samples.py` creates sample videos
- Mark integration tests with `@pytest.mark.integration`
- Use `conftest.py` for shared fixtures like temp directories

### Code Style
- Line length: 100 characters (configured in pyproject.toml)
- Docstrings: Google style with Args/Returns/Raises/Example sections
- Type hints: Required for all function signatures
- Imports: Sorted with isort (profile: black)
- Naming: snake_case for functions, PascalCase for classes, UPPER_SNAKE_CASE for constants

### Configuration Files
- **`configs/profiles.yaml`**: Video encoding profiles (11 built-in)
- **`configs/logging.yaml`**: Logging configuration (console + rotating file)
- **`pyproject.toml`**: Tool configs for black, isort, pytest, mypy, coverage
- **`.flake8`**: Flake8 linting rules

### Re-encoding with Profiles (Task 2.1 Complete)
Re-encoding support is production-ready:
- Use `--no-copy` flag to enable re-encoding
- Use `--profile <name>` to specify encoding profile
- Hardware profiles: clip_720p, movie_1080p, movie_720p (HEVC)
- Software profiles: web_720p, mobile_720p, quality_high (H.264/HEVC)
- Limitation: VideoToolbox fails on 480p, use software profiles instead
- Performance benchmarks documented in TASK_2.1_COMPLETE.md

**Example usage:**
```bash
# Cut with hardware re-encoding
video-tool cut -i movie.mp4 -o ./output -d 11 --no-copy --profile clip_720p

# Concat with software re-encoding
video-tool concat -i part1.mp4 -i part2.mp4 -o final.mp4 --no-copy --profile web_720p
```

### Working with FFmpeg
- Always check FFmpeg installation with `check_ffmpeg_installed()`
- Use ffprobe for metadata: `ffprobe -v quiet -print_format json -show_format`
- Parse FFmpeg stderr for progress (stdout is usually empty)
- FFmpeg writes progress to stderr in format: `frame=X fps=Y time=HH:MM:SS.ms`

## Current Development Status

**Phase 1 Complete ✅**
- Core CLI with 9 commands
- Video cut/concat operations (codec copy mode)
- Audio extract/replace operations
- Profile system with 11 built-in profiles
- Logging with rich output and rotating files
- ~75% test coverage
- CI/CD with GitHub Actions

**Phase 2 In Progress 🚧** (See PHASE_2_ANALYSIS.md and TASK_2.1_COMPLETE.md)
- Task 2.1: Re-encoding support (cut/concat with profiles) - **✅ DONE**
- Task 2.2: Complete test coverage (audio_ops, logger) - **✅ DONE**
- Task 2.3: CI/CD pipeline - **✅ DONE**
- Task 2.4: Database & Job Tracking
- Task 2.5: Queue System for background processing
- Task 2.6: Web API
- Task 2.7: Enhanced error handling with automatic fallback
- Task 2.11: Comprehensive integration tests

**Phase 2 Task 2.1 Achievements** ✅
- Cut with profile support: Tested with clip_720p, web_720p
- Concat with profile support: Fully implemented and tested
- Hardware acceleration: Verified on macOS (VideoToolbox)
- Performance: 4.3x realtime encoding speed measured
- Size optimization: 23% reduction verified (876 MB → 672 MB)
- Known limitation: VideoToolbox fails on 480p (use software profiles)
- Documentation: Updated README.md, cmd.md, TASK_2.1_COMPLETE.md

## Troubleshooting

**FFmpeg Not Found**
```bash
# macOS
brew install ffmpeg

# Verify installation
which ffmpeg
ffmpeg -version
```

**Import Errors in Tests**
Tests run from repository root. If imports fail, check:
- Virtual environment is activated
- Package installed in editable mode: `pip install -e .`
- PYTHONPATH includes src directory

**CI/CD Failures**
- macOS runners required (VideoToolbox hardware acceleration)
- FFmpeg installed via Homebrew in CI
- Coverage uploaded to Codecov for Python 3.11 only

**Test Fixtures Missing**
Generate sample videos for integration tests:
```bash
python tests/fixtures/generate_samples.py
```

## External References

- FFmpeg Documentation: https://ffmpeg.org/documentation.html
- Typer CLI Documentation: https://typer.tiangolo.com/
- Rich Console Documentation: https://rich.readthedocs.io/
