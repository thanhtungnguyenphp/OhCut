# Video Tool 🎬

A powerful Python-based command-line tool for automated video and audio processing using FFmpeg.

**Status:** Phase 1 MVP Complete ✅ | Production Ready 🚀

## Features

### Video Operations
- ✅ Cut videos into segments by duration or timestamps
- ✅ Concatenate multiple videos with codec compatibility checking
- ✅ Display comprehensive video information
- 🚧 Add intro/outro clips (Phase 2)
- 🚧 Insert advertisements at specific positions (Phase 2)
- 🚧 Change video speed (Phase 2)

### Audio Operations
- ✅ Extract audio from videos (copy or re-encode)
- ✅ Replace audio tracks in videos
- ✅ Mix multiple audio tracks
- ✅ Get audio metadata information

### Encoding Profiles
- ✅ 11 built-in profiles for different use cases
  - Movie profiles: 1080p, 720p (high quality)
  - Clip profiles: 720p, 480p (optimized for segments)
  - Web profiles: 1080p, 720p (H.264 compatibility)
  - Mobile profiles: 720p, 480p (efficient streaming)
  - Quality profiles: CRF-based variable bitrate
- ✅ Hardware acceleration support (VideoToolbox on macOS)
- ✅ Custom profile configuration via YAML

### CLI Features
- ✅ 9 commands with rich console output
- ✅ Progress bars and status indicators
- ✅ Dry-run mode for previewing operations
- ✅ Verbose logging with --verbose flag
- ✅ Custom log file support
- ✅ Color-coded output with emojis

### Logging & Monitoring
- ✅ Rich console logging with colors and tracebacks
- ✅ Rotating file logs (10MB, 5 backups)
- ✅ Separate error log file
- ✅ Structured logging with operation context
- ✅ FFmpeg command logging with execution timing

## Requirements

- Python 3.9 or higher
- FFmpeg installed on your system

## Installation

### 1. Install FFmpeg

**macOS:**
```bash
brew install ffmpeg
```

**Verify FFmpeg installation:**
```bash
ffmpeg -version
```

### 2. Clone the Repository

```bash
git clone https://github.com/yourusername/video-tool.git
cd video-tool
```

### 3. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Install the Package

```bash
pip install -e .
```

## Quick Start

### 1. Check Video Information

```bash
video-tool info --input movie.mp4
```

Displays video information in a formatted table:
- Duration, resolution, codec, bitrate, FPS
- Audio codec and file size

### 2. Cut Video into Segments

```bash
# Cut into 11-minute segments
video-tool cut --input movie.mp4 --duration 11 --output-dir ./output

# Custom prefix for output files
video-tool cut -i movie.mp4 -d 15 -o ./clips --prefix segment

# Force re-encoding with profile
video-tool cut -i movie.mp4 -o ./output --no-copy --profile clip_720p
```

### 3. Concatenate Multiple Videos

```bash
# Concatenate with codec copy (fast)
video-tool concat --inputs part1.mp4 part2.mp4 part3.mp4 --output final.mp4

# Using wildcard (shell expansion)
video-tool concat -i clips/*.mp4 -o combined.mp4

# Force re-encoding if codecs don't match
video-tool concat -i part1.mp4 -i part2.mp4 -o final.mp4 --no-copy
```

### 4. Extract Audio from Video

```bash
# Extract with codec copy (fastest)
video-tool audio extract --input movie.mp4 --output audio.m4a --codec copy

# Re-encode to MP3
video-tool audio extract -i video.mp4 -o audio.mp3 --codec mp3 --bitrate 192k

# Extract as OPUS
video-tool audio extract -i film.mkv -o soundtrack.opus -c opus -b 128k
```

### 5. Replace Audio Track

```bash
video-tool audio replace --video movie.mp4 --audio new_audio.m4a --output result.mp4

# With shorter syntax
video-tool audio replace -v video.mp4 -a soundtrack.mp3 -o final.mp4
```

### 6. List Encoding Profiles

```bash
video-tool profiles list
```

Shows all available encoding profiles with descriptions, resolutions, and codecs.

### 7. Show Profile Details

```bash
video-tool profiles show clip_720p
video-tool profiles show movie_1080p
```

Displays detailed information about a specific profile.

### 8. Show Version

```bash
video-tool version
```

Displays Video Tool version and FFmpeg version.

## Global Options

All commands support these global options:

### Verbose Mode

```bash
video-tool --verbose cut -i movie.mp4 -o ./output
video-tool -v info -i video.mp4
```

Enables detailed DEBUG logging:
- Full FFmpeg command output
- Progress callbacks
- Detailed error traces

### Dry Run Mode

```bash
video-tool --dry-run cut -i movie.mp4 -o ./output -d 11
video-tool --dry-run concat -i part1.mp4 -i part2.mp4 -o final.mp4
```

Shows what would be done without executing:
- Preview of output files
- Video duration calculations
- No actual file operations

### Custom Log File

```bash
video-tool --log-file /tmp/process.log cut -i movie.mp4 -o ./output
video-tool -v --log-file debug.log concat -i *.mp4 -o final.mp4
```

Specifies custom log file path (default: `logs/video_tool.log`).

## Usage Examples

### Example 1: Process a Movie into Clips

```bash
# Step 1: Check video information
video-tool info -i movie.mp4

# Step 2: Cut into 11-minute segments with preview
video-tool --dry-run cut -i movie.mp4 -o ./clips -d 11

# Step 3: Execute the cut
video-tool cut -i movie.mp4 -o ./clips -d 11 --prefix movie_part

# Result: movie_part_001.mp4, movie_part_002.mp4, ...
```

### Example 2: Extract and Replace Audio

```bash
# Extract audio from video
video-tool audio extract -i movie.mp4 -o audio.m4a --codec copy

# Edit audio externally (e.g., adjust volume, add effects)
# ...

# Replace with edited audio
video-tool audio replace -v movie.mp4 -a edited_audio.m4a -o final.mp4
```

### Example 3: Concatenate Clips with Intro

```bash
# Add intro to multiple clips
video-tool concat -i intro.mp4 -i clip1.mp4 -o clip1_with_intro.mp4
video-tool concat -i intro.mp4 -i clip2.mp4 -o clip2_with_intro.mp4

# Or combine everything at once
video-tool concat -i intro.mp4 -i clip1.mp4 -i clip2.mp4 -i outro.mp4 -o final_movie.mp4
```

### Example 4: Re-encode with Different Profile

```bash
# List available profiles
video-tool profiles list

# View profile details
video-tool profiles show web_720p

# Cut and re-encode using profile (Phase 2 feature)
# video-tool cut -i movie.mp4 -o ./clips --no-copy --profile web_720p
```

## Troubleshooting

### FFmpeg Not Found

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get install ffmpeg

# Verify installation
ffmpeg -version
```

### Permission Errors

```bash
# Ensure output directory exists and is writable
mkdir -p output
chmod 755 output
```

### Video Compatibility Issues

```bash
# Check video codec and format
video-tool info -i input.mp4

# Re-encode incompatible videos
ffmpeg -i input.mp4 -c:v libx264 -c:a aac output.mp4
```

### Log Analysis

```bash
# Enable verbose mode for detailed diagnostics
video-tool --verbose --log-file debug.log cut -i movie.mp4 -o ./output

# Check log file
tail -f logs/video_tool.log
```

## Configuration

### Profiles

Encoding profiles are defined in `configs/profiles.yaml`:

```yaml
profiles:
  movie_1080p:
    video_codec: hevc_videotoolbox
    video_bitrate: 4M
    resolution: 1920x1080
    audio_codec: aac
    audio_bitrate: 192k
  
  clip_720p:
    video_codec: hevc_videotoolbox
    video_bitrate: 2M
    resolution: 1280x720
    audio_codec: aac
    audio_bitrate: 128k
```

### Logging

Configure logging in `configs/logging.yaml`:

```yaml
version: 1
handlers:
  console:
    class: logging.StreamHandler
    level: INFO
  file:
    class: logging.handlers.RotatingFileHandler
    filename: logs/video_tool.log
    maxBytes: 10485760  # 10MB
    backupCount: 5
```

## Project Structure

```
video_tool/
├── src/
│   ├── cli/              # CLI commands
│   ├── core/             # Core operations (video_ops, audio_ops, ffmpeg_runner)
│   ├── pipelines/        # Workflow pipelines
│   └── utils/            # Helper functions
├── tests/                # Unit and integration tests
├── configs/              # Configuration files
├── logs/                 # Log files
├── requirements.txt      # Python dependencies
├── setup.py             # Package setup
└── README.md            # This file
```

## Development

For detailed development guidelines, environment setup, code style, testing, and contribution workflow, see [CONTRIBUTING.md](CONTRIBUTING.md).

### Quick Start for Developers

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/ -v

# Code formatting
black src/

# Linting
flake8 src/
```

## Roadmap

### Phase 1: MVP (Core CLI) ✅ COMPLETED
- ✅ FFmpeg wrapper with robust error handling
- ✅ Video operations: cut, concat, info
- ✅ Audio operations: extract, replace
- ✅ Profile system with validation
- ✅ CLI with rich output and global options
- ✅ Comprehensive logging system
- ✅ Unit and integration tests (~75% coverage)
- ✅ Documentation (README + CONTRIBUTING)

### Phase 2: Production-Ready (Planned)
- [ ] Re-encoding with profile support
- [ ] Job queue for batch processing
- [ ] Web UI for visual workflow management
- [ ] REST API for programmatic access
- [ ] Enhanced error recovery

### Phase 3: Advanced Features (Future)
- [ ] Hardware acceleration (GPU encoding)
- [ ] Metadata management and editing
- [ ] Subtitle extraction and embedding
- [ ] Advanced filters and effects

### Phase 4: AI & Cloud (Future)
- [ ] Scene detection and smart segmentation
- [ ] Cloud storage integration
- [ ] Distributed processing

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

## License

MIT License - See LICENSE file for details.

## Support

For issues and feature requests, please open an issue on GitHub.

## Author

Jerry - Video Processing Tool Development

---

**Note:** This tool is designed for macOS environments with focus on performance and reliability. Linux support may be added in future releases.
