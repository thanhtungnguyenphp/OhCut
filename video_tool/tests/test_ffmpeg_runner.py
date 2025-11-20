"""Tests for ffmpeg_runner module."""

import pytest
from unittest.mock import patch, MagicMock, call
import subprocess

from core.ffmpeg_runner import (
    check_ffmpeg_installed,
    check_ffprobe_installed,
    get_ffmpeg_version,
    parse_ffmpeg_progress,
    run_ffmpeg,
    run_ffprobe,
    FFmpegError,
    FFmpegNotFoundError,
)


class TestCheckInstalled:
    """Tests for checking if FFmpeg/ffprobe are installed."""

    @patch("shutil.which")
    def test_check_ffmpeg_installed_returns_true_when_found(self, mock_which):
        """Test that check_ffmpeg_installed returns True when FFmpeg is found."""
        mock_which.return_value = "/usr/bin/ffmpeg"
        assert check_ffmpeg_installed() is True
        mock_which.assert_called_once_with("ffmpeg")

    @patch("shutil.which")
    def test_check_ffmpeg_installed_returns_false_when_not_found(self, mock_which):
        """Test that check_ffmpeg_installed returns False when FFmpeg is not found."""
        mock_which.return_value = None
        assert check_ffmpeg_installed() is False

    @patch("shutil.which")
    def test_check_ffprobe_installed_returns_true_when_found(self, mock_which):
        """Test that check_ffprobe_installed returns True when ffprobe is found."""
        mock_which.return_value = "/usr/bin/ffprobe"
        assert check_ffprobe_installed() is True
        mock_which.assert_called_once_with("ffprobe")

    @patch("shutil.which")
    def test_check_ffprobe_installed_returns_false_when_not_found(self, mock_which):
        """Test that check_ffprobe_installed returns False when ffprobe is not found."""
        mock_which.return_value = None
        assert check_ffprobe_installed() is False


class TestGetVersion:
    """Tests for getting FFmpeg version."""

    @patch("core.ffmpeg_runner.check_ffmpeg_installed")
    def test_get_ffmpeg_version_raises_error_when_not_installed(self, mock_check):
        """Test that get_ffmpeg_version raises error when FFmpeg is not installed."""
        mock_check.return_value = False
        with pytest.raises(FFmpegNotFoundError):
            get_ffmpeg_version()

    @patch("subprocess.run")
    @patch("core.ffmpeg_runner.check_ffmpeg_installed")
    def test_get_ffmpeg_version_returns_version_string(self, mock_check, mock_run):
        """Test that get_ffmpeg_version returns correct version string."""
        mock_check.return_value = True
        mock_run.return_value = MagicMock(
            stdout="ffmpeg version 8.0 Copyright (c) 2000-2025\n",
            returncode=0,
        )

        version = get_ffmpeg_version()
        assert version == "8.0"

    @patch("subprocess.run")
    @patch("core.ffmpeg_runner.check_ffmpeg_installed")
    def test_get_ffmpeg_version_handles_timeout(self, mock_check, mock_run):
        """Test that get_ffmpeg_version handles timeout gracefully."""
        mock_check.return_value = True
        mock_run.side_effect = subprocess.TimeoutExpired("ffmpeg", 5)

        with pytest.raises(FFmpegError) as exc_info:
            get_ffmpeg_version()
        assert "timed out" in str(exc_info.value)


class TestParseProgress:
    """Tests for parsing FFmpeg progress output."""

    def test_parse_ffmpeg_progress_with_valid_line(self):
        """Test parsing a valid FFmpeg progress line."""
        line = "frame=  100 fps=30.0 size=    1024kB time=00:00:04.00 bitrate=2000.5kbits/s speed=1.0x"
        progress = parse_ffmpeg_progress(line)

        assert progress is not None
        assert progress["frame"] == 100
        assert progress["fps"] == 30.0
        assert progress["size_kb"] == 1024.0
        assert progress["time_seconds"] == 4.0
        assert progress["bitrate"] == 2000.5
        assert progress["speed"] == 1.0

    def test_parse_ffmpeg_progress_with_time_format(self):
        """Test parsing time in HH:MM:SS.ms format."""
        line = "frame=  500 time=00:01:30.50 bitrate=1500kbits/s"
        progress = parse_ffmpeg_progress(line)

        assert progress is not None
        assert progress["time_seconds"] == 90.5  # 1 min 30.5 sec

    def test_parse_ffmpeg_progress_with_hours(self):
        """Test parsing time with hours."""
        line = "frame=1000 time=01:15:30.00"
        progress = parse_ffmpeg_progress(line)

        assert progress is not None
        assert progress["time_seconds"] == 4530.0  # 1 hour 15 min 30 sec

    def test_parse_ffmpeg_progress_returns_none_for_invalid_line(self):
        """Test that invalid lines return None."""
        assert parse_ffmpeg_progress("") is None
        assert parse_ffmpeg_progress("Some random text") is None
        assert parse_ffmpeg_progress(None) is None

    def test_parse_ffmpeg_progress_with_partial_data(self):
        """Test parsing line with only some fields."""
        line = "frame=  200 fps=25.5"
        progress = parse_ffmpeg_progress(line)

        assert progress is not None
        assert progress["frame"] == 200
        assert progress["fps"] == 25.5
        assert "time_seconds" not in progress


class TestRunFFmpeg:
    """Tests for running FFmpeg commands."""

    @patch("core.ffmpeg_runner.check_ffmpeg_installed")
    def test_run_ffmpeg_raises_error_when_not_installed(self, mock_check):
        """Test that run_ffmpeg raises error when FFmpeg is not installed."""
        mock_check.return_value = False
        with pytest.raises(FFmpegNotFoundError):
            run_ffmpeg(["-version"])

    @patch("subprocess.Popen")
    @patch("core.ffmpeg_runner.check_ffmpeg_installed")
    def test_run_ffmpeg_executes_successfully(self, mock_check, mock_popen):
        """Test successful FFmpeg command execution."""
        mock_check.return_value = True

        # Mock process
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stderr = iter([])
        mock_process.stdout.read.return_value = ""
        mock_process.wait.return_value = None
        mock_popen.return_value = mock_process

        result = run_ffmpeg(["-version"])

        assert result["success"] is True
        assert result["returncode"] == 0
        mock_popen.assert_called_once()

    @patch("subprocess.Popen")
    @patch("core.ffmpeg_runner.check_ffmpeg_installed")
    def test_run_ffmpeg_raises_error_on_failure(self, mock_check, mock_popen):
        """Test that run_ffmpeg raises error when command fails."""
        mock_check.return_value = True

        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.stderr = iter(["Error: Invalid input\n"])
        mock_process.stdout.read.return_value = ""
        mock_process.wait.return_value = None
        mock_popen.return_value = mock_process

        with pytest.raises(FFmpegError) as exc_info:
            run_ffmpeg(["-i", "nonexistent.mp4"])
        assert exc_info.value.returncode == 1

    @patch("subprocess.Popen")
    @patch("core.ffmpeg_runner.check_ffmpeg_installed")
    def test_run_ffmpeg_calls_progress_callback(self, mock_check, mock_popen):
        """Test that run_ffmpeg calls progress callback with parsed data."""
        mock_check.return_value = True

        progress_line = "frame=  100 fps=30.0 time=00:00:04.00\n"
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stderr = iter([progress_line])
        mock_process.stdout.read.return_value = ""
        mock_process.wait.return_value = None
        mock_popen.return_value = mock_process

        callback = MagicMock()
        result = run_ffmpeg(["-i", "test.mp4"], progress_callback=callback)

        assert result["success"] is True
        callback.assert_called_once()
        progress_data = callback.call_args[0][0]
        assert progress_data["frame"] == 100

    @patch("subprocess.Popen")
    @patch("core.ffmpeg_runner.check_ffmpeg_installed")
    def test_run_ffmpeg_handles_timeout(self, mock_check, mock_popen):
        """Test that run_ffmpeg handles timeout correctly."""
        mock_check.return_value = True

        mock_process = MagicMock()
        mock_process.stderr = iter([])
        mock_process.wait.side_effect = subprocess.TimeoutExpired("ffmpeg", 10)
        mock_popen.return_value = mock_process

        with pytest.raises(FFmpegError) as exc_info:
            run_ffmpeg(["-i", "test.mp4"], timeout=10)
        assert "timed out" in str(exc_info.value)
        mock_process.kill.assert_called_once()

    @patch("subprocess.Popen")
    @patch("core.ffmpeg_runner.check_ffmpeg_installed")
    def test_run_ffmpeg_handles_callback_exception(self, mock_check, mock_popen):
        """Test that run_ffmpeg continues when callback raises exception."""
        mock_check.return_value = True

        progress_line = "frame=  100 fps=30.0\n"
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stderr = iter([progress_line])
        mock_process.stdout.read.return_value = ""
        mock_process.wait.return_value = None
        mock_popen.return_value = mock_process

        # Callback that raises exception
        callback = MagicMock(side_effect=Exception("Callback error"))

        # Should not raise exception, just log warning
        result = run_ffmpeg(["-i", "test.mp4"], progress_callback=callback)
        assert result["success"] is True


class TestRunFFprobe:
    """Tests for running ffprobe commands."""

    @patch("core.ffmpeg_runner.check_ffprobe_installed")
    def test_run_ffprobe_raises_error_when_not_installed(self, mock_check):
        """Test that run_ffprobe raises error when ffprobe is not installed."""
        mock_check.return_value = False
        with pytest.raises(FFmpegNotFoundError):
            run_ffprobe(["-version"])

    @patch("subprocess.run")
    @patch("core.ffmpeg_runner.check_ffprobe_installed")
    def test_run_ffprobe_executes_successfully(self, mock_check, mock_run):
        """Test successful ffprobe command execution."""
        mock_check.return_value = True
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"format": {"duration": "10.5"}}',
            stderr="",
        )

        result = run_ffprobe(["-show_format", "test.mp4"])

        assert result["success"] is True
        assert result["returncode"] == 0
        assert "duration" in result["stdout"]

    @patch("subprocess.run")
    @patch("core.ffmpeg_runner.check_ffprobe_installed")
    def test_run_ffprobe_raises_error_on_failure(self, mock_check, mock_run):
        """Test that run_ffprobe raises error when command fails."""
        mock_check.return_value = True
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Error: File not found",
        )

        with pytest.raises(FFmpegError) as exc_info:
            run_ffprobe(["-show_format", "nonexistent.mp4"])
        assert exc_info.value.returncode == 1

    @patch("subprocess.run")
    @patch("core.ffmpeg_runner.check_ffprobe_installed")
    def test_run_ffprobe_handles_timeout(self, mock_check, mock_run):
        """Test that run_ffprobe handles timeout correctly."""
        mock_check.return_value = True
        mock_run.side_effect = subprocess.TimeoutExpired("ffprobe", 30)

        with pytest.raises(FFmpegError) as exc_info:
            run_ffprobe(["-show_format", "test.mp4"])
        assert "timed out" in str(exc_info.value)


class TestFFmpegError:
    """Tests for FFmpegError exception."""

    def test_ffmpeg_error_stores_attributes(self):
        """Test that FFmpegError stores message, returncode, and stderr."""
        error = FFmpegError("Test error", 1, "stderr output")
        assert error.message == "Test error"
        assert error.returncode == 1
        assert error.stderr == "stderr output"
        assert str(error) == "Test error"

    def test_ffmpeg_error_with_default_stderr(self):
        """Test FFmpegError with default empty stderr."""
        error = FFmpegError("Test error", 1)
        assert error.stderr == ""
