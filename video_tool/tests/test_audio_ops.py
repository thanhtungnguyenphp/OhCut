"""Unit tests for audio_ops module.

Tests audio extraction, replacement, mixing, and info retrieval operations.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, call

from core.audio_ops import (
    extract_audio,
    replace_audio,
    mix_audio_tracks,
    get_audio_info,
)
from core.ffmpeg_runner import FFmpegError
from utils.file_utils import InvalidInputError


class TestExtractAudio:
    """Tests for extract_audio() function."""

    @patch("core.audio_ops.run_ffmpeg")
    @patch("core.audio_ops.validate_input_file")
    @patch("core.audio_ops.ensure_output_dir")
    @patch("core.audio_ops.Path")
    def test_extract_audio_copy_mode(
        self, mock_path, mock_ensure_dir, mock_validate, mock_run_ffmpeg
    ):
        """Test audio extraction with codec copy mode."""
        # Setup
        mock_path_instance = MagicMock()
        mock_path_instance.parent = "/output"
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance
        
        # Execute
        result = extract_audio("input.mp4", "output.m4a", codec="copy")
        
        # Verify
        assert result == "output.m4a"
        mock_validate.assert_called_once_with("input.mp4")
        mock_ensure_dir.assert_called_once()
        
        # Verify FFmpeg command
        call_args = mock_run_ffmpeg.call_args[0][0]
        assert "-i" in call_args
        assert "input.mp4" in call_args
        assert "-vn" in call_args
        assert "-acodec" in call_args
        assert "copy" in call_args
        assert "output.m4a" in call_args

    @patch("core.audio_ops.run_ffmpeg")
    @patch("core.audio_ops.validate_input_file")
    @patch("core.audio_ops.ensure_output_dir")
    @patch("core.audio_ops.Path")
    def test_extract_audio_with_aac_codec(
        self, mock_path, mock_ensure_dir, mock_validate, mock_run_ffmpeg
    ):
        """Test audio extraction with AAC re-encoding."""
        # Setup
        mock_path_instance = MagicMock()
        mock_path_instance.parent = "/output"
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance
        
        # Execute
        result = extract_audio("input.mp4", "output.m4a", codec="aac", bitrate="192k")
        
        # Verify
        assert result == "output.m4a"
        
        # Verify FFmpeg command includes codec and bitrate
        call_args = mock_run_ffmpeg.call_args[0][0]
        assert "-acodec" in call_args
        assert "aac" in call_args
        assert "-b:a" in call_args
        assert "192k" in call_args

    @patch("core.audio_ops.run_ffmpeg")
    @patch("core.audio_ops.validate_input_file")
    @patch("core.audio_ops.ensure_output_dir")
    @patch("core.audio_ops.Path")
    def test_extract_audio_with_mp3_codec(
        self, mock_path, mock_ensure_dir, mock_validate, mock_run_ffmpeg
    ):
        """Test audio extraction with MP3 re-encoding."""
        # Setup
        mock_path_instance = MagicMock()
        mock_path_instance.parent = "/output"
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance
        
        # Execute
        result = extract_audio("input.mp4", "output.mp3", codec="mp3", bitrate="320k")
        
        # Verify
        assert result == "output.mp3"
        
        call_args = mock_run_ffmpeg.call_args[0][0]
        assert "mp3" in call_args
        assert "320k" in call_args

    @patch("core.audio_ops.run_ffmpeg")
    @patch("core.audio_ops.validate_input_file")
    @patch("core.audio_ops.ensure_output_dir")
    @patch("core.audio_ops.Path")
    def test_extract_audio_with_default_bitrate(
        self, mock_path, mock_ensure_dir, mock_validate, mock_run_ffmpeg
    ):
        """Test audio extraction uses default bitrate when not specified."""
        # Setup
        mock_path_instance = MagicMock()
        mock_path_instance.parent = "/output"
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance
        
        # Execute - no bitrate specified
        result = extract_audio("input.mp4", "output.m4a", codec="aac")
        
        # Verify default bitrate is used
        call_args = mock_run_ffmpeg.call_args[0][0]
        assert "aac" in call_args
        assert "-b:a" in call_args
        assert "128k" in call_args  # Default for AAC

    @patch("core.audio_ops.run_ffmpeg")
    @patch("core.audio_ops.validate_input_file")
    @patch("core.audio_ops.ensure_output_dir")
    @patch("core.audio_ops.Path")
    def test_extract_audio_opus_codec(
        self, mock_path, mock_ensure_dir, mock_validate, mock_run_ffmpeg
    ):
        """Test audio extraction with Opus codec."""
        # Setup
        mock_path_instance = MagicMock()
        mock_path_instance.parent = "/output"
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance
        
        # Execute
        result = extract_audio("input.mp4", "output.opus", codec="opus")
        
        # Verify
        call_args = mock_run_ffmpeg.call_args[0][0]
        assert "opus" in call_args
        assert "128k" in call_args  # Default for Opus

    @patch("core.audio_ops.run_ffmpeg")
    @patch("core.audio_ops.validate_input_file")
    @patch("core.audio_ops.ensure_output_dir")
    @patch("core.audio_ops.Path")
    def test_extract_audio_flac_codec_lossless(
        self, mock_path, mock_ensure_dir, mock_validate, mock_run_ffmpeg
    ):
        """Test audio extraction with FLAC (lossless, no bitrate)."""
        # Setup
        mock_path_instance = MagicMock()
        mock_path_instance.parent = "/output"
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance
        
        # Execute
        result = extract_audio("input.mp4", "output.flac", codec="flac")
        
        # Verify - no bitrate for lossless
        call_args = mock_run_ffmpeg.call_args[0][0]
        assert "flac" in call_args
        # Should NOT have bitrate for lossless codec
        if "-b:a" in call_args:
            # If -b:a exists, it shouldn't be in the command for FLAC
            pytest.fail("FLAC should not have bitrate specified")

    @patch("core.audio_ops.validate_input_file")
    def test_extract_audio_invalid_codec(self, mock_validate):
        """Test audio extraction with invalid codec raises error."""
        with pytest.raises(InvalidInputError) as exc_info:
            extract_audio("input.mp4", "output.mp4", codec="invalid")
        
        assert "Invalid codec" in str(exc_info.value)
        assert "invalid" in str(exc_info.value)

    @patch("core.audio_ops.validate_input_file")
    def test_extract_audio_invalid_input_file(self, mock_validate):
        """Test audio extraction with invalid input file."""
        mock_validate.side_effect = InvalidInputError("File not found")
        
        with pytest.raises(InvalidInputError) as exc_info:
            extract_audio("nonexistent.mp4", "output.m4a")
        
        assert "File not found" in str(exc_info.value)

    @patch("core.audio_ops.run_ffmpeg")
    @patch("core.audio_ops.validate_input_file")
    @patch("core.audio_ops.ensure_output_dir")
    @patch("core.audio_ops.Path")
    def test_extract_audio_ffmpeg_fails(
        self, mock_path, mock_ensure_dir, mock_validate, mock_run_ffmpeg
    ):
        """Test audio extraction when FFmpeg command fails."""
        # Setup
        mock_run_ffmpeg.side_effect = FFmpegError("FFmpeg failed", 1)
        
        # Execute & Verify
        with pytest.raises(FFmpegError) as exc_info:
            extract_audio("input.mp4", "output.m4a")
        
        assert "FFmpeg failed" in str(exc_info.value)

    @patch("core.audio_ops.run_ffmpeg")
    @patch("core.audio_ops.validate_input_file")
    @patch("core.audio_ops.ensure_output_dir")
    @patch("core.audio_ops.Path")
    def test_extract_audio_output_not_created(
        self, mock_path, mock_ensure_dir, mock_validate, mock_run_ffmpeg
    ):
        """Test error when output file is not created."""
        # Setup - FFmpeg succeeds but file doesn't exist
        mock_path_instance = MagicMock()
        mock_path_instance.parent = "/output"
        mock_path_instance.exists.return_value = False  # File not created
        mock_path.return_value = mock_path_instance
        
        # Execute & Verify
        with pytest.raises(FFmpegError) as exc_info:
            extract_audio("input.mp4", "output.m4a")
        
        assert "not created" in str(exc_info.value)


class TestReplaceAudio:
    """Tests for replace_audio() function."""

    @patch("core.audio_ops.run_ffmpeg")
    @patch("core.audio_ops.validate_input_file")
    @patch("core.audio_ops.get_video_info")
    @patch("core.audio_ops.ensure_output_dir")
    @patch("core.audio_ops.Path")
    def test_replace_audio_copy_mode(
        self, mock_path, mock_ensure_dir, mock_get_info, mock_validate, mock_run_ffmpeg
    ):
        """Test audio replacement with codec copy mode."""
        # Setup
        mock_get_info.return_value = {"duration": 120.0}
        mock_path_instance = MagicMock()
        mock_path_instance.parent = "/output"
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance
        
        # Execute
        result = replace_audio("video.mp4", "audio.m4a", "output.mp4", copy_codecs=True)
        
        # Verify
        assert result == "output.mp4"
        assert mock_validate.call_count == 2  # Called for both video and audio
        
        # Verify FFmpeg command
        call_args = mock_run_ffmpeg.call_args[0][0]
        assert call_args.count("-i") == 2  # Two inputs
        assert "-c:v" in call_args
        assert "copy" in call_args
        assert "-c:a" in call_args
        assert "-map" in call_args
        assert "-shortest" in call_args

    @patch("core.audio_ops.run_ffmpeg")
    @patch("core.audio_ops.validate_input_file")
    @patch("core.audio_ops.get_video_info")
    @patch("core.audio_ops.ensure_output_dir")
    @patch("core.audio_ops.Path")
    def test_replace_audio_reencode_mode(
        self, mock_path, mock_ensure_dir, mock_get_info, mock_validate, mock_run_ffmpeg
    ):
        """Test audio replacement with re-encoding."""
        # Setup
        mock_get_info.return_value = {"duration": 120.0}
        mock_path_instance = MagicMock()
        mock_path_instance.parent = "/output"
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance
        
        # Execute
        result = replace_audio("video.mp4", "audio.mp3", "output.mp4", copy_codecs=False)
        
        # Verify re-encoding parameters
        call_args = mock_run_ffmpeg.call_args[0][0]
        assert "libx264" in call_args
        assert "aac" in call_args
        assert "-preset" in call_args
        assert "-crf" in call_args

    @patch("core.audio_ops.validate_input_file")
    def test_replace_audio_invalid_video(self, mock_validate):
        """Test audio replacement with invalid video file."""
        # Setup
        def validate_side_effect(path):
            if "video" in path:
                raise InvalidInputError("Video file not found")
        
        mock_validate.side_effect = validate_side_effect
        
        # Execute & Verify
        with pytest.raises(InvalidInputError):
            replace_audio("invalid_video.mp4", "audio.m4a", "output.mp4")

    @patch("core.audio_ops.validate_input_file")
    def test_replace_audio_invalid_audio(self, mock_validate):
        """Test audio replacement with invalid audio file."""
        # Setup
        def validate_side_effect(path):
            if "audio" in path:
                raise InvalidInputError("Audio file not found")
        
        mock_validate.side_effect = validate_side_effect
        
        # Execute & Verify
        with pytest.raises(InvalidInputError):
            replace_audio("video.mp4", "invalid_audio.m4a", "output.mp4")

    @patch("core.audio_ops.run_ffmpeg")
    @patch("core.audio_ops.validate_input_file")
    @patch("core.audio_ops.get_video_info")
    @patch("core.audio_ops.ensure_output_dir")
    @patch("core.audio_ops.Path")
    def test_replace_audio_ffmpeg_fails(
        self, mock_path, mock_ensure_dir, mock_get_info, mock_validate, mock_run_ffmpeg
    ):
        """Test audio replacement when FFmpeg fails."""
        # Setup
        mock_get_info.return_value = {"duration": 120.0}
        mock_run_ffmpeg.side_effect = FFmpegError("FFmpeg error", 1)
        
        # Execute & Verify
        with pytest.raises(FFmpegError):
            replace_audio("video.mp4", "audio.m4a", "output.mp4")

    @patch("core.audio_ops.run_ffmpeg")
    @patch("core.audio_ops.validate_input_file")
    @patch("core.audio_ops.get_video_info")
    @patch("core.audio_ops.ensure_output_dir")
    @patch("core.audio_ops.Path")
    def test_replace_audio_output_not_created(
        self, mock_path, mock_ensure_dir, mock_get_info, mock_validate, mock_run_ffmpeg
    ):
        """Test error when output file is not created."""
        # Setup
        mock_get_info.return_value = {"duration": 120.0}
        mock_path_instance = MagicMock()
        mock_path_instance.parent = "/output"
        mock_path_instance.exists.return_value = False  # Not created
        mock_path.return_value = mock_path_instance
        
        # Execute & Verify
        with pytest.raises(FFmpegError) as exc_info:
            replace_audio("video.mp4", "audio.m4a", "output.mp4")
        
        assert "not created" in str(exc_info.value)


class TestMixAudioTracks:
    """Tests for mix_audio_tracks() function."""

    @patch("core.audio_ops.run_ffmpeg")
    @patch("core.audio_ops.validate_input_file")
    @patch("core.audio_ops.ensure_output_dir")
    @patch("core.audio_ops.Path")
    def test_mix_two_audio_tracks(
        self, mock_path, mock_ensure_dir, mock_validate, mock_run_ffmpeg
    ):
        """Test mixing two audio tracks."""
        # Setup
        mock_path_instance = MagicMock()
        mock_path_instance.parent = "/output"
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance
        
        # Execute
        result = mix_audio_tracks(["audio1.m4a", "audio2.m4a"], "mixed.m4a")
        
        # Verify
        assert result == "mixed.m4a"
        assert mock_validate.call_count == 2
        
        # Verify FFmpeg command
        call_args = mock_run_ffmpeg.call_args[0][0]
        assert call_args.count("-i") == 2
        assert "-filter_complex" in call_args
        # Check that filter string contains amix and inputs=2
        filter_idx = call_args.index("-filter_complex") + 1
        filter_str = call_args[filter_idx]
        assert "amix" in filter_str
        assert "inputs=2" in filter_str

    @patch("core.audio_ops.run_ffmpeg")
    @patch("core.audio_ops.validate_input_file")
    @patch("core.audio_ops.ensure_output_dir")
    @patch("core.audio_ops.Path")
    def test_mix_multiple_audio_tracks(
        self, mock_path, mock_ensure_dir, mock_validate, mock_run_ffmpeg
    ):
        """Test mixing multiple (3+) audio tracks."""
        # Setup
        mock_path_instance = MagicMock()
        mock_path_instance.parent = "/output"
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance
        
        audio_files = ["audio1.m4a", "audio2.m4a", "audio3.m4a", "audio4.m4a"]
        
        # Execute
        result = mix_audio_tracks(audio_files, "mixed.m4a", codec="mp3", bitrate="256k")
        
        # Verify
        assert result == "mixed.m4a"
        assert mock_validate.call_count == 4
        
        call_args = mock_run_ffmpeg.call_args[0][0]
        assert call_args.count("-i") == 4
        # Check filter string contains inputs=4
        filter_idx = call_args.index("-filter_complex") + 1
        filter_str = call_args[filter_idx]
        assert "inputs=4" in filter_str
        assert "mp3" in call_args
        assert "256k" in call_args

    def test_mix_audio_empty_list(self):
        """Test mixing with empty audio list raises error."""
        with pytest.raises(InvalidInputError) as exc_info:
            mix_audio_tracks([], "output.m4a")
        
        assert "cannot be empty" in str(exc_info.value)

    def test_mix_audio_single_file(self):
        """Test mixing with only one file raises error."""
        with pytest.raises(InvalidInputError) as exc_info:
            mix_audio_tracks(["audio1.m4a"], "output.m4a")
        
        assert "At least 2" in str(exc_info.value)

    @patch("core.audio_ops.validate_input_file")
    def test_mix_audio_invalid_file(self, mock_validate):
        """Test mixing with invalid audio file."""
        # Setup - second file is invalid
        def validate_side_effect(path):
            if "audio2" in path:
                raise InvalidInputError("File not found")
        
        mock_validate.side_effect = validate_side_effect
        
        # Execute & Verify
        with pytest.raises(InvalidInputError):
            mix_audio_tracks(["audio1.m4a", "audio2.m4a"], "output.m4a")

    @patch("core.audio_ops.run_ffmpeg")
    @patch("core.audio_ops.validate_input_file")
    @patch("core.audio_ops.ensure_output_dir")
    @patch("core.audio_ops.Path")
    def test_mix_audio_ffmpeg_fails(
        self, mock_path, mock_ensure_dir, mock_validate, mock_run_ffmpeg
    ):
        """Test mixing when FFmpeg fails."""
        # Setup
        mock_run_ffmpeg.side_effect = FFmpegError("Mixing failed", 1)
        
        # Execute & Verify
        with pytest.raises(FFmpegError):
            mix_audio_tracks(["audio1.m4a", "audio2.m4a"], "output.m4a")


class TestGetAudioInfo:
    """Tests for get_audio_info() function."""

    @patch("core.audio_ops.get_video_info")
    def test_get_audio_info_success(self, mock_get_video_info):
        """Test getting audio info from video file."""
        # Setup
        mock_get_video_info.return_value = {
            "duration": 120.5,
            "audio_codec": "aac",
            "video_codec": "h264",
        }
        
        # Execute
        result = get_audio_info("video.mp4")
        
        # Verify
        assert result["audio_codec"] == "aac"
        assert result["duration"] == 120.5
        mock_get_video_info.assert_called_once_with("video.mp4")

    @patch("core.audio_ops.get_video_info")
    def test_get_audio_info_no_audio(self, mock_get_video_info):
        """Test getting audio info from video with no audio."""
        # Setup
        mock_get_video_info.return_value = {
            "duration": 60.0,
            "video_codec": "h264",
        }
        
        # Execute
        result = get_audio_info("video.mp4")
        
        # Verify
        assert result["audio_codec"] == "none"
        assert result["duration"] == 60.0

    @patch("core.audio_ops.get_video_info")
    def test_get_audio_info_invalid_file(self, mock_get_video_info):
        """Test getting audio info from invalid file."""
        # Setup
        mock_get_video_info.side_effect = InvalidInputError("File not found")
        
        # Execute & Verify
        with pytest.raises(InvalidInputError):
            get_audio_info("nonexistent.mp4")


# Integration-style tests (still using mocks but testing workflows)
class TestAudioOpsWorkflows:
    """Test common audio operation workflows."""

    @patch("core.audio_ops.run_ffmpeg")
    @patch("core.audio_ops.validate_input_file")
    @patch("core.audio_ops.ensure_output_dir")
    @patch("core.audio_ops.Path")
    def test_extract_and_verify_workflow(
        self, mock_path, mock_ensure_dir, mock_validate, mock_run_ffmpeg
    ):
        """Test complete extract audio workflow."""
        # Setup
        mock_path_instance = MagicMock()
        mock_path_instance.parent = "/output"
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance
        
        # Execute - extract with various codecs
        result1 = extract_audio("movie.mp4", "audio_copy.m4a", codec="copy")
        result2 = extract_audio("movie.mp4", "audio_aac.m4a", codec="aac", bitrate="192k")
        result3 = extract_audio("movie.mp4", "audio.mp3", codec="mp3", bitrate="320k")
        
        # Verify all succeeded
        assert result1 == "audio_copy.m4a"
        assert result2 == "audio_aac.m4a"
        assert result3 == "audio.mp3"
        assert mock_run_ffmpeg.call_count == 3

    @patch("core.audio_ops.run_ffmpeg")
    @patch("core.audio_ops.validate_input_file")
    @patch("core.audio_ops.get_video_info")
    @patch("core.audio_ops.ensure_output_dir")
    @patch("core.audio_ops.Path")
    def test_replace_audio_workflow(
        self, mock_path, mock_ensure_dir, mock_get_info, mock_validate, mock_run_ffmpeg
    ):
        """Test complete replace audio workflow."""
        # Setup
        mock_get_info.return_value = {"duration": 180.0}
        mock_path_instance = MagicMock()
        mock_path_instance.parent = "/output"
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance
        
        # Execute - replace with copy mode
        result = replace_audio(
            "original_video.mp4",
            "new_audio.m4a",
            "final_video.mp4",
            copy_codecs=True
        )
        
        # Verify
        assert result == "final_video.mp4"
        mock_run_ffmpeg.assert_called_once()
