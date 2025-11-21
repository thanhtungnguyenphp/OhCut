"""Integration tests for ffmpeg_runner with real FFmpeg commands.

These tests require FFmpeg to be installed on the system.
Mark as integration tests that can be skipped if FFmpeg is not available.
"""

import pytest
from core.ffmpeg_runner import (
    check_ffmpeg_installed,
    check_ffprobe_installed,
    get_ffmpeg_version,
    parse_ffmpeg_progress,
)


@pytest.mark.integration
class TestRealFFmpeg:
    """Integration tests with real FFmpeg installation."""

    def test_ffmpeg_is_installed(self):
        """Test that FFmpeg is actually installed on the system."""
        assert check_ffmpeg_installed() is True, "FFmpeg must be installed to run integration tests"

    def test_ffprobe_is_installed(self):
        """Test that ffprobe is actually installed on the system."""
        assert (
            check_ffprobe_installed() is True
        ), "ffprobe must be installed to run integration tests"

    def test_can_get_ffmpeg_version(self):
        """Test that we can get the actual FFmpeg version."""
        version = get_ffmpeg_version()
        assert version is not None
        assert len(version) > 0
        # Version should be numeric (e.g., "8.0", "7.1")
        assert version[0].isdigit()
        print(f"FFmpeg version detected: {version}")


@pytest.mark.unit
class TestProgressParsing:
    """Unit tests for progress parsing (no FFmpeg needed)."""

    def test_parse_real_ffmpeg_progress_output(self):
        """Test parsing actual FFmpeg progress output format."""
        # This is actual output from FFmpeg 8.0
        line = "frame=  123 fps= 45 q=28.0 size=    1024kB time=00:00:05.12 bitrate=1637.7kbits/s speed=1.87x"
        progress = parse_ffmpeg_progress(line)

        assert progress is not None
        assert progress["frame"] == 123
        assert progress["fps"] == 45.0
        assert progress["size_kb"] == 1024.0
        assert progress["time_seconds"] == 5.12
        assert progress["bitrate"] == 1637.7
        assert progress["speed"] == 1.87
