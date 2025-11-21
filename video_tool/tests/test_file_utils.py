"""Tests for file_utils module."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from utils.file_utils import (
    validate_input_file,
    get_video_info,
    ensure_output_dir,
    generate_temp_filename,
    atomic_move,
    get_file_size,
    get_free_disk_space,
    check_disk_space,
    cleanup_temp_files,
    get_safe_filename,
    InvalidInputError,
    InsufficientDiskSpaceError,
)


class TestValidateInputFile:
    """Tests for validate_input_file function."""

    def test_validate_existing_file_returns_true(self, tmp_path):
        """Test that validate_input_file returns True for existing file."""
        test_file = tmp_path / "test.mp4"
        test_file.write_text("test content")

        assert validate_input_file(str(test_file)) is True

    def test_validate_nonexistent_file_raises_error(self):
        """Test that validate_input_file raises error for non-existent file."""
        with pytest.raises(InvalidInputError) as exc_info:
            validate_input_file("/nonexistent/file.mp4")
        assert "does not exist" in str(exc_info.value)

    def test_validate_directory_raises_error(self, tmp_path):
        """Test that validate_input_file raises error for directory."""
        with pytest.raises(InvalidInputError) as exc_info:
            validate_input_file(str(tmp_path))
        assert "not a file" in str(exc_info.value)

    def test_validate_empty_file_raises_error(self, tmp_path):
        """Test that validate_input_file raises error for empty file."""
        empty_file = tmp_path / "empty.mp4"
        empty_file.touch()

        with pytest.raises(InvalidInputError) as exc_info:
            validate_input_file(str(empty_file))
        assert "empty" in str(exc_info.value)


class TestGetVideoInfo:
    """Tests for get_video_info function."""

    @patch("utils.file_utils.run_ffprobe")
    @patch("utils.file_utils.validate_input_file")
    def test_get_video_info_returns_correct_data(self, mock_validate, mock_ffprobe, tmp_path):
        """Test that get_video_info returns correctly parsed data."""
        # Create test file
        test_file = tmp_path / "test.mp4"
        test_file.write_text("test")
        mock_validate.return_value = True

        # Mock ffprobe output
        ffprobe_output = {
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 1920,
                    "height": 1080,
                    "r_frame_rate": "30/1",
                },
                {
                    "codec_type": "audio",
                    "codec_name": "aac",
                },
            ],
            "format": {
                "duration": "120.5",
                "bit_rate": "5000000",
                "format_name": "mp4",
            },
        }

        mock_ffprobe.return_value = {
            "success": True,
            "stdout": json.dumps(ffprobe_output),
            "returncode": 0,
        }

        info = get_video_info(str(test_file))

        assert info["duration"] == 120.5
        assert info["width"] == 1920
        assert info["height"] == 1080
        assert info["codec"] == "h264"
        assert info["bitrate"] == 5000000
        assert info["fps"] == 30.0
        assert info["audio_codec"] == "aac"
        assert info["format"] == "mp4"

    @patch("utils.file_utils.run_ffprobe")
    @patch("utils.file_utils.validate_input_file")
    def test_get_video_info_handles_fractional_fps(self, mock_validate, mock_ffprobe, tmp_path):
        """Test that get_video_info correctly calculates fractional FPS."""
        test_file = tmp_path / "test.mp4"
        test_file.write_text("test")
        mock_validate.return_value = True

        ffprobe_output = {
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 1920,
                    "height": 1080,
                    "r_frame_rate": "30000/1001",  # 29.97 fps
                }
            ],
            "format": {"duration": "10", "bit_rate": "5000000", "format_name": "mp4"},
        }

        mock_ffprobe.return_value = {
            "success": True,
            "stdout": json.dumps(ffprobe_output),
            "returncode": 0,
        }

        info = get_video_info(str(test_file))
        assert 29.96 < info["fps"] < 29.98  # 30000/1001 ≈ 29.97

    @patch("utils.file_utils.run_ffprobe")
    @patch("utils.file_utils.validate_input_file")
    def test_get_video_info_handles_no_audio_stream(self, mock_validate, mock_ffprobe, tmp_path):
        """Test that get_video_info handles video without audio."""
        test_file = tmp_path / "test.mp4"
        test_file.write_text("test")
        mock_validate.return_value = True

        ffprobe_output = {
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 1920,
                    "height": 1080,
                    "r_frame_rate": "30/1",
                }
            ],
            "format": {"duration": "10", "bit_rate": "5000000", "format_name": "mp4"},
        }

        mock_ffprobe.return_value = {
            "success": True,
            "stdout": json.dumps(ffprobe_output),
            "returncode": 0,
        }

        info = get_video_info(str(test_file))
        assert info["audio_codec"] == "none"


class TestEnsureOutputDir:
    """Tests for ensure_output_dir function."""

    def test_ensure_output_dir_creates_directory(self, tmp_path):
        """Test that ensure_output_dir creates directory if it doesn't exist."""
        new_dir = tmp_path / "output" / "videos"
        ensure_output_dir(str(new_dir))
        assert new_dir.exists()
        assert new_dir.is_dir()

    def test_ensure_output_dir_accepts_existing_directory(self, tmp_path):
        """Test that ensure_output_dir accepts existing directory."""
        existing_dir = tmp_path / "existing"
        existing_dir.mkdir()
        ensure_output_dir(str(existing_dir))  # Should not raise

    def test_ensure_output_dir_raises_error_for_file(self, tmp_path):
        """Test that ensure_output_dir raises error if path is a file."""
        test_file = tmp_path / "file.txt"
        test_file.write_text("test")

        with pytest.raises(InvalidInputError) as exc_info:
            ensure_output_dir(str(test_file))
        assert "not a directory" in str(exc_info.value)


class TestGenerateTempFilename:
    """Tests for generate_temp_filename function."""

    def test_generate_temp_filename_creates_valid_path(self):
        """Test that generate_temp_filename creates valid temp file path."""
        temp_file = generate_temp_filename("test", ".mp4")

        assert temp_file.endswith(".mp4")
        assert "test_" in temp_file
        assert os.path.dirname(temp_file)  # Has directory component

        # Cleanup
        if os.path.exists(temp_file):
            os.remove(temp_file)

    def test_generate_temp_filename_with_default_args(self):
        """Test generate_temp_filename with default arguments."""
        temp_file = generate_temp_filename()

        assert temp_file.endswith(".mp4")
        assert "video_tool_" in temp_file

        # Cleanup
        if os.path.exists(temp_file):
            os.remove(temp_file)


class TestAtomicMove:
    """Tests for atomic_move function."""

    def test_atomic_move_moves_file_successfully(self, tmp_path):
        """Test that atomic_move successfully moves file."""
        src = tmp_path / "source.mp4"
        dst = tmp_path / "dest" / "output.mp4"

        src.write_text("test content")

        atomic_move(str(src), str(dst))

        assert dst.exists()
        assert not src.exists()
        assert dst.read_text() == "test content"

    def test_atomic_move_creates_destination_directory(self, tmp_path):
        """Test that atomic_move creates destination directory if needed."""
        src = tmp_path / "source.mp4"
        dst = tmp_path / "new" / "dir" / "output.mp4"

        src.write_text("test content")

        atomic_move(str(src), str(dst))

        assert dst.exists()
        assert dst.parent.exists()

    def test_atomic_move_raises_error_for_nonexistent_source(self, tmp_path):
        """Test that atomic_move raises error if source doesn't exist."""
        src = tmp_path / "nonexistent.mp4"
        dst = tmp_path / "output.mp4"

        with pytest.raises(InvalidInputError) as exc_info:
            atomic_move(str(src), str(dst))
        assert "does not exist" in str(exc_info.value)


class TestGetFileSize:
    """Tests for get_file_size function."""

    def test_get_file_size_returns_correct_size(self, tmp_path):
        """Test that get_file_size returns correct file size."""
        test_file = tmp_path / "test.mp4"
        content = "x" * 1024  # 1KB
        test_file.write_text(content)

        size = get_file_size(str(test_file))
        assert size == 1024

    def test_get_file_size_raises_error_for_nonexistent_file(self):
        """Test that get_file_size raises error for non-existent file."""
        with pytest.raises(InvalidInputError) as exc_info:
            get_file_size("/nonexistent/file.mp4")
        assert "does not exist" in str(exc_info.value)


class TestDiskSpace:
    """Tests for disk space functions."""

    def test_get_free_disk_space_returns_positive_value(self):
        """Test that get_free_disk_space returns positive value."""
        free_space = get_free_disk_space()
        assert free_space > 0

    def test_check_disk_space_passes_with_enough_space(self):
        """Test that check_disk_space passes with enough space."""
        # Check for small amount (1KB)
        assert check_disk_space(1024, buffer_gb=0.001) is True

    def test_check_disk_space_raises_error_with_insufficient_space(self):
        """Test that check_disk_space raises error with insufficient space."""
        # Try to check for impossibly large space
        with pytest.raises(InsufficientDiskSpaceError) as exc_info:
            check_disk_space(10**18, buffer_gb=0)  # 1 exabyte
        assert "Insufficient disk space" in str(exc_info.value)


class TestCleanupTempFiles:
    """Tests for cleanup_temp_files function."""

    def test_cleanup_temp_files_removes_existing_files(self, tmp_path):
        """Test that cleanup_temp_files removes existing files."""
        file1 = tmp_path / "temp1.mp4"
        file2 = tmp_path / "temp2.mp4"

        file1.write_text("test1")
        file2.write_text("test2")

        cleanup_temp_files(str(file1), str(file2))

        assert not file1.exists()
        assert not file2.exists()

    def test_cleanup_temp_files_handles_nonexistent_files(self, tmp_path):
        """Test that cleanup_temp_files handles non-existent files gracefully."""
        file1 = tmp_path / "exists.mp4"
        file2 = tmp_path / "nonexistent.mp4"

        file1.write_text("test")

        # Should not raise exception
        cleanup_temp_files(str(file1), str(file2))

        assert not file1.exists()


class TestGetSafeFilename:
    """Tests for get_safe_filename function."""

    def test_get_safe_filename_removes_unsafe_characters(self):
        """Test that get_safe_filename removes unsafe characters."""
        unsafe_name = 'My Video: Part "1" <2>.mp4'
        safe_name = get_safe_filename(unsafe_name)

        assert safe_name == "My Video_ Part _1_ _2_.mp4"
        assert ":" not in safe_name
        assert '"' not in safe_name
        assert "<" not in safe_name
        assert ">" not in safe_name

    def test_get_safe_filename_handles_slashes(self):
        """Test that get_safe_filename handles slashes."""
        name_with_slash = "folder/file\\name.mp4"
        safe_name = get_safe_filename(name_with_slash)

        assert "/" not in safe_name
        assert "\\" not in safe_name
        assert safe_name == "folder_file_name.mp4"

    def test_get_safe_filename_strips_leading_trailing_spaces(self):
        """Test that get_safe_filename strips leading/trailing spaces and dots."""
        name = "  .filename.mp4..  "
        safe_name = get_safe_filename(name)

        assert not safe_name.startswith(" ")
        assert not safe_name.endswith(" ")
        assert not safe_name.startswith(".")

    def test_get_safe_filename_limits_length(self):
        """Test that get_safe_filename limits filename length."""
        long_name = "x" * 300 + ".mp4"
        safe_name = get_safe_filename(long_name)

        assert len(safe_name) <= 204  # 200 + ".mp4"
        assert safe_name.endswith(".mp4")

    def test_get_safe_filename_preserves_extension(self):
        """Test that get_safe_filename preserves file extension."""
        name = "video.mp4"
        safe_name = get_safe_filename(name)

        assert safe_name == "video.mp4"
