"""Tests for video_ops module."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, call

from core.video_ops import (
    cut_by_duration,
    cut_by_timestamps,
    concat_videos,
    get_segment_info,
)
from core.ffmpeg_runner import FFmpegError
from utils.file_utils import InvalidInputError


class TestCutByDuration:
    """Tests for cut_by_duration function."""

    @patch("core.video_ops.run_ffmpeg")
    @patch("core.video_ops.check_disk_space")
    @patch("core.video_ops.get_file_size")
    @patch("core.video_ops.ensure_output_dir")
    @patch("core.video_ops.get_video_info")
    @patch("core.video_ops.validate_input_file")
    def test_cut_by_duration_creates_correct_segments(
        self,
        mock_validate,
        mock_video_info,
        mock_ensure_dir,
        mock_file_size,
        mock_check_space,
        mock_ffmpeg,
        tmp_path,
    ):
        """Test that cut_by_duration creates correct number of segments."""
        # Setup mocks
        mock_validate.return_value = True
        mock_video_info.return_value = {"duration": 100.0}  # 100 seconds
        mock_file_size.return_value = 1024 * 1024  # 1MB
        mock_check_space.return_value = True
        mock_ffmpeg.return_value = {"success": True, "returncode": 0}

        # Create fake output files
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        for i in range(1, 4):  # 3 segments for 100s video with 40s segments
            (output_dir / f"part_{i:03d}.mp4").write_text("segment")

        # Call function
        segments = cut_by_duration(
            "input.mp4", str(output_dir), segment_duration=40, prefix="part"
        )

        # Verify
        assert len(segments) == 3
        assert all(Path(seg).exists() for seg in segments)
        mock_ffmpeg.assert_called_once()

    @patch("core.video_ops.validate_input_file")
    def test_cut_by_duration_raises_error_for_invalid_duration(self, mock_validate):
        """Test that cut_by_duration raises error for invalid segment duration."""
        mock_validate.return_value = True

        with pytest.raises(InvalidInputError) as exc_info:
            cut_by_duration("input.mp4", "/output", segment_duration=0)
        assert "positive" in str(exc_info.value).lower()

        with pytest.raises(InvalidInputError) as exc_info:
            cut_by_duration("input.mp4", "/output", segment_duration=-10)
        assert "positive" in str(exc_info.value).lower()

    @patch("core.video_ops.run_ffmpeg")
    @patch("core.video_ops.check_disk_space")
    @patch("core.video_ops.get_file_size")
    @patch("core.video_ops.ensure_output_dir")
    @patch("core.video_ops.get_video_info")
    @patch("core.video_ops.validate_input_file")
    def test_cut_by_duration_uses_copy_codec_by_default(
        self,
        mock_validate,
        mock_video_info,
        mock_ensure_dir,
        mock_file_size,
        mock_check_space,
        mock_ffmpeg,
        tmp_path,
    ):
        """Test that cut_by_duration uses codec copy by default."""
        mock_validate.return_value = True
        mock_video_info.return_value = {"duration": 60.0}
        mock_file_size.return_value = 1024 * 1024
        mock_check_space.return_value = True
        mock_ffmpeg.return_value = {"success": True, "returncode": 0}

        output_dir = tmp_path / "output"
        output_dir.mkdir()
        (output_dir / "part_001.mp4").write_text("segment")

        cut_by_duration("input.mp4", str(output_dir), 60)

        # Check that FFmpeg was called with -c copy
        call_args = mock_ffmpeg.call_args[0][0]
        assert "-c" in call_args
        assert "copy" in call_args

    @patch("core.video_ops.run_ffmpeg")
    @patch("core.video_ops.check_disk_space")
    @patch("core.video_ops.get_file_size")
    @patch("core.video_ops.ensure_output_dir")
    @patch("core.video_ops.get_video_info")
    @patch("core.video_ops.validate_input_file")
    def test_cut_by_duration_re_encodes_when_copy_false(
        self,
        mock_validate,
        mock_video_info,
        mock_ensure_dir,
        mock_file_size,
        mock_check_space,
        mock_ffmpeg,
        tmp_path,
    ):
        """Test that cut_by_duration re-encodes when copy_codec=False."""
        mock_validate.return_value = True
        mock_video_info.return_value = {"duration": 60.0}
        mock_file_size.return_value = 1024 * 1024
        mock_check_space.return_value = True
        mock_ffmpeg.return_value = {"success": True, "returncode": 0}

        output_dir = tmp_path / "output"
        output_dir.mkdir()
        (output_dir / "part_001.mp4").write_text("segment")

        cut_by_duration("input.mp4", str(output_dir), 60, copy_codec=False)

        # Check that FFmpeg was called with encoding options
        call_args = mock_ffmpeg.call_args[0][0]
        assert "-c:v" in call_args
        assert "libx264" in call_args
        assert "-c:a" in call_args
        assert "aac" in call_args

    @patch("core.video_ops.run_ffmpeg")
    @patch("core.video_ops.check_disk_space")
    @patch("core.video_ops.get_file_size")
    @patch("core.video_ops.ensure_output_dir")
    @patch("core.video_ops.get_video_info")
    @patch("core.video_ops.validate_input_file")
    def test_cut_by_duration_calculates_correct_num_segments(
        self,
        mock_validate,
        mock_video_info,
        mock_ensure_dir,
        mock_file_size,
        mock_check_space,
        mock_ffmpeg,
        tmp_path,
    ):
        """Test correct calculation of number of segments."""
        mock_validate.return_value = True
        mock_file_size.return_value = 1024 * 1024
        mock_check_space.return_value = True
        mock_ffmpeg.return_value = {"success": True, "returncode": 0}

        test_cases = [
            (100, 30, 4),  # 100s / 30s = 3.33... -> 4 segments
            (120, 60, 2),  # 120s / 60s = 2 segments
            (65, 30, 3),  # 65s / 30s = 2.16... -> 3 segments
        ]

        for duration, segment_dur, expected_segments in test_cases:
            mock_video_info.return_value = {"duration": float(duration)}
            output_dir = tmp_path / f"output_{duration}"
            output_dir.mkdir()

            # Create expected files
            for i in range(1, expected_segments + 1):
                (output_dir / f"part_{i:03d}.mp4").write_text("segment")

            segments = cut_by_duration("input.mp4", str(output_dir), segment_dur)
            assert len(segments) == expected_segments

    @patch("core.video_ops.run_ffmpeg")
    @patch("core.video_ops.check_disk_space")
    @patch("core.video_ops.get_file_size")
    @patch("core.video_ops.ensure_output_dir")
    @patch("core.video_ops.get_video_info")
    @patch("core.video_ops.validate_input_file")
    def test_cut_by_duration_raises_error_when_no_segments_created(
        self,
        mock_validate,
        mock_video_info,
        mock_ensure_dir,
        mock_file_size,
        mock_check_space,
        mock_ffmpeg,
        tmp_path,
    ):
        """Test that error is raised when no segments are created."""
        mock_validate.return_value = True
        mock_video_info.return_value = {"duration": 100.0}
        mock_file_size.return_value = 1024 * 1024
        mock_check_space.return_value = True
        mock_ffmpeg.return_value = {"success": True, "returncode": 0}

        output_dir = tmp_path / "output"
        output_dir.mkdir()
        # Don't create any output files

        with pytest.raises(FFmpegError) as exc_info:
            cut_by_duration("input.mp4", str(output_dir), 30)
        assert "No output segments" in str(exc_info.value)


class TestCutByTimestamps:
    """Tests for cut_by_timestamps function."""

    @patch("core.video_ops.run_ffmpeg")
    @patch("core.video_ops.ensure_output_dir")
    @patch("core.video_ops.validate_input_file")
    def test_cut_by_timestamps_creates_correct_segments(
        self, mock_validate, mock_ensure_dir, mock_ffmpeg, tmp_path
    ):
        """Test that cut_by_timestamps creates segments at correct positions."""
        mock_validate.return_value = True
        mock_ffmpeg.return_value = {"success": True, "returncode": 0}

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        timestamps = [(0, 30), (30, 60), (60, 90)]

        # Create fake output files
        for i in range(1, 4):
            (output_dir / f"clip_{i:03d}.mp4").write_text("segment")

        segments = cut_by_timestamps(
            "input.mp4", str(output_dir), timestamps, prefix="clip"
        )

        assert len(segments) == 3
        assert mock_ffmpeg.call_count == 3  # One call per segment

    @patch("core.video_ops.validate_input_file")
    def test_cut_by_timestamps_raises_error_for_empty_timestamps(self, mock_validate):
        """Test that error is raised for empty timestamps list."""
        mock_validate.return_value = True

        with pytest.raises(InvalidInputError) as exc_info:
            cut_by_timestamps("input.mp4", "/output", [])
        assert "empty" in str(exc_info.value).lower()

    @patch("core.video_ops.validate_input_file")
    def test_cut_by_timestamps_raises_error_for_invalid_timestamps(self, mock_validate):
        """Test that error is raised for invalid timestamps."""
        mock_validate.return_value = True

        # Negative values
        with pytest.raises(InvalidInputError):
            cut_by_timestamps("input.mp4", "/output", [(-10, 20)])

        # End before start
        with pytest.raises(InvalidInputError):
            cut_by_timestamps("input.mp4", "/output", [(50, 20)])

        # Equal start and end
        with pytest.raises(InvalidInputError):
            cut_by_timestamps("input.mp4", "/output", [(30, 30)])

    @patch("core.video_ops.run_ffmpeg")
    @patch("core.video_ops.ensure_output_dir")
    @patch("core.video_ops.validate_input_file")
    def test_cut_by_timestamps_uses_correct_ffmpeg_args(
        self, mock_validate, mock_ensure_dir, mock_ffmpeg, tmp_path
    ):
        """Test that correct FFmpeg arguments are used."""
        mock_validate.return_value = True
        mock_ffmpeg.return_value = {"success": True, "returncode": 0}

        output_dir = tmp_path / "output"
        output_dir.mkdir()
        (output_dir / "part_001.mp4").write_text("segment")

        cut_by_timestamps("input.mp4", str(output_dir), [(10, 40)])

        # Check FFmpeg call arguments
        call_args = mock_ffmpeg.call_args[0][0]
        assert "-ss" in call_args
        assert "10" in call_args  # Start time
        assert "-t" in call_args
        assert "30" in call_args  # Duration (40 - 10)


class TestConcatVideos:
    """Tests for concat_videos function."""

    @patch("core.video_ops.run_ffmpeg")
    @patch("core.video_ops.cleanup_temp_files")
    @patch("core.video_ops.generate_temp_filename")
    @patch("core.video_ops.ensure_output_dir")
    @patch("core.video_ops.get_video_info")
    @patch("core.video_ops.validate_input_file")
    def test_concat_videos_creates_output(
        self,
        mock_validate,
        mock_video_info,
        mock_ensure_dir,
        mock_temp_filename,
        mock_cleanup,
        mock_ffmpeg,
        tmp_path,
    ):
        """Test that concat_videos creates output file."""
        mock_validate.return_value = True
        mock_video_info.return_value = {
            "duration": 60.0,
            "codec": "h264",
            "width": 1920,
            "height": 1080,
        }
        mock_temp_filename.return_value = str(tmp_path / "concat.txt")
        mock_ffmpeg.return_value = {"success": True, "returncode": 0}

        # Create fake output
        output_file = tmp_path / "output.mp4"
        output_file.write_text("concatenated video")

        result = concat_videos(
            ["video1.mp4", "video2.mp4"],
            str(output_file),
        )

        assert result == str(output_file)
        assert output_file.exists()
        mock_ffmpeg.assert_called_once()
        mock_cleanup.assert_called_once()

    @patch("core.video_ops.validate_input_file")
    def test_concat_videos_raises_error_for_empty_input(self, mock_validate):
        """Test that concat_videos raises error for empty input list."""
        with pytest.raises(InvalidInputError) as exc_info:
            concat_videos([], "output.mp4")
        assert "empty" in str(exc_info.value).lower()

    @patch("core.video_ops.validate_input_file")
    def test_concat_videos_raises_error_for_single_input(self, mock_validate):
        """Test that concat_videos requires at least 2 files."""
        mock_validate.return_value = True
        with pytest.raises(InvalidInputError) as exc_info:
            concat_videos(["video1.mp4"], "output.mp4")
        assert "at least 2" in str(exc_info.value).lower()

    @patch("core.video_ops.run_ffmpeg")
    @patch("core.video_ops.cleanup_temp_files")
    @patch("core.video_ops.generate_temp_filename")
    @patch("core.video_ops.ensure_output_dir")
    @patch("core.video_ops.get_video_info")
    @patch("core.video_ops.validate_input_file")
    def test_concat_videos_checks_codec_compatibility(
        self,
        mock_validate,
        mock_video_info,
        mock_ensure_dir,
        mock_temp_filename,
        mock_cleanup,
        mock_ffmpeg,
        tmp_path,
    ):
        """Test that concat_videos checks codec compatibility."""
        mock_validate.return_value = True
        mock_temp_filename.return_value = str(tmp_path / "concat.txt")

        # First video H.264, second video H.265
        def video_info_side_effect(path):
            if "video1" in path:
                return {"codec": "h264", "width": 1920, "height": 1080}
            else:
                return {"codec": "h265", "width": 1920, "height": 1080}

        mock_video_info.side_effect = video_info_side_effect

        # Should raise error with codec copy
        with pytest.raises(InvalidInputError) as exc_info:
            concat_videos(["video1.mp4", "video2.mp4"], "output.mp4")
        assert "incompatible codecs" in str(exc_info.value).lower()

    @patch("core.video_ops.run_ffmpeg")
    @patch("core.video_ops.cleanup_temp_files")
    @patch("core.video_ops.generate_temp_filename")
    @patch("core.video_ops.ensure_output_dir")
    @patch("core.video_ops.get_video_info")
    @patch("core.video_ops.validate_input_file")
    def test_concat_videos_allows_incompatible_with_reencoding(
        self,
        mock_validate,
        mock_video_info,
        mock_ensure_dir,
        mock_temp_filename,
        mock_cleanup,
        mock_ffmpeg,
        tmp_path,
    ):
        """Test that concat_videos allows incompatible codecs with re-encoding."""
        mock_validate.return_value = True
        mock_temp_filename.return_value = str(tmp_path / "concat.txt")
        mock_ffmpeg.return_value = {"success": True, "returncode": 0}

        # Different codecs
        def video_info_side_effect(path):
            if "video1" in path:
                return {"codec": "h264", "width": 1920, "height": 1080}
            else:
                return {"codec": "h265", "width": 1920, "height": 1080}

        mock_video_info.side_effect = video_info_side_effect

        output_file = tmp_path / "output.mp4"
        output_file.write_text("video")

        # Should succeed with copy_codec=False
        result = concat_videos(
            ["video1.mp4", "video2.mp4"],
            str(output_file),
            copy_codec=False,
        )

        assert result == str(output_file)

    @patch("core.video_ops.run_ffmpeg")
    @patch("core.video_ops.cleanup_temp_files")
    @patch("core.video_ops.generate_temp_filename")
    @patch("core.video_ops.ensure_output_dir")
    @patch("core.video_ops.validate_input_file")
    def test_concat_videos_skips_validation_when_disabled(
        self,
        mock_validate,
        mock_ensure_dir,
        mock_temp_filename,
        mock_cleanup,
        mock_ffmpeg,
        tmp_path,
    ):
        """Test that concat_videos can skip compatibility validation."""
        mock_validate.return_value = True
        mock_temp_filename.return_value = str(tmp_path / "concat.txt")
        mock_ffmpeg.return_value = {"success": True, "returncode": 0}

        output_file = tmp_path / "output.mp4"
        output_file.write_text("video")

        # Should not call get_video_info when validation is disabled
        result = concat_videos(
            ["video1.mp4", "video2.mp4"],
            str(output_file),
            validate_compatibility=False,
        )

        assert result == str(output_file)

    @patch("core.video_ops.run_ffmpeg")
    @patch("core.video_ops.cleanup_temp_files")
    @patch("core.video_ops.generate_temp_filename")
    @patch("core.video_ops.ensure_output_dir")
    @patch("core.video_ops.get_video_info")
    @patch("core.video_ops.validate_input_file")
    def test_concat_videos_uses_copy_codec_by_default(
        self,
        mock_validate,
        mock_video_info,
        mock_ensure_dir,
        mock_temp_filename,
        mock_cleanup,
        mock_ffmpeg,
        tmp_path,
    ):
        """Test that concat_videos uses codec copy by default."""
        mock_validate.return_value = True
        mock_video_info.return_value = {"codec": "h264", "width": 1920, "height": 1080}
        mock_temp_filename.return_value = str(tmp_path / "concat.txt")
        mock_ffmpeg.return_value = {"success": True, "returncode": 0}

        output_file = tmp_path / "output.mp4"
        output_file.write_text("video")

        concat_videos(["video1.mp4", "video2.mp4"], str(output_file))

        # Check FFmpeg was called with -c copy
        call_args = mock_ffmpeg.call_args[0][0]
        assert "-c" in call_args
        assert "copy" in call_args


class TestGetSegmentInfo:
    """Tests for get_segment_info function."""

    @patch("core.video_ops.get_video_info")
    def test_get_segment_info_returns_correct_data(self, mock_video_info):
        """Test that get_segment_info returns correct segmentation info."""
        mock_video_info.return_value = {"duration": 100.0, "codec": "h264"}

        info = get_segment_info("video.mp4", 30)

        assert info["total_duration"] == 100.0
        assert info["segment_duration"] == 30
        assert info["num_segments"] == 4  # ceil(100/30)
        assert info["last_segment_duration"] == 10.0  # 100 % 30
        assert "video_info" in info

    @patch("core.video_ops.get_video_info")
    def test_get_segment_info_handles_exact_division(self, mock_video_info):
        """Test get_segment_info when duration divides evenly."""
        mock_video_info.return_value = {"duration": 120.0, "codec": "h264"}

        info = get_segment_info("video.mp4", 60)

        assert info["num_segments"] == 2
        assert info["last_segment_duration"] == 60.0  # Full segment

    @patch("core.video_ops.get_video_info")
    def test_get_segment_info_calculates_last_segment_correctly(self, mock_video_info):
        """Test correct calculation of last segment duration."""
        test_cases = [
            (100, 30, 10),  # 100 % 30 = 10
            (125, 40, 5),  # 125 % 40 = 5
            (90, 30, 30),  # 90 % 30 = 0 -> full segment
        ]

        for total_dur, segment_dur, expected_last in test_cases:
            mock_video_info.return_value = {"duration": float(total_dur), "codec": "h264"}
            info = get_segment_info("video.mp4", segment_dur)
            assert info["last_segment_duration"] == expected_last


class TestProfileBasedReEncoding:
    """Tests for profile-based re-encoding support."""

    @patch("core.video_ops.get_profile")
    @patch("core.video_ops.run_ffmpeg")
    @patch("core.video_ops.check_disk_space")
    @patch("core.video_ops.get_file_size")
    @patch("core.video_ops.ensure_output_dir")
    @patch("core.video_ops.get_video_info")
    @patch("core.video_ops.validate_input_file")
    def test_cut_by_duration_uses_profile_when_specified(
        self,
        mock_validate,
        mock_video_info,
        mock_ensure_dir,
        mock_file_size,
        mock_check_space,
        mock_ffmpeg,
        mock_get_profile,
        tmp_path,
    ):
        """Test that cut_by_duration uses specified profile for re-encoding."""
        from core.profiles import Profile
        
        # Setup mocks
        mock_validate.return_value = True
        mock_video_info.return_value = {"duration": 60.0}
        mock_file_size.return_value = 1024 * 1024
        mock_check_space.return_value = True
        mock_ffmpeg.return_value = {"success": True, "returncode": 0}
        
        # Mock profile
        mock_profile = Profile(
            name="test_720p",
            description="Test profile",
            video_codec="hevc_videotoolbox",
            video_bitrate="2M",
            resolution="1280x720",
            audio_codec="aac",
            audio_bitrate="128k",
            preset=None,
            crf=None,
        )
        mock_get_profile.return_value = mock_profile
        
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        (output_dir / "part_001.mp4").write_text("segment")
        
        # Call with profile
        cut_by_duration(
            "input.mp4",
            str(output_dir),
            60,
            copy_codec=False,
            profile_name="test_720p",
        )
        
        # Verify profile was loaded
        mock_get_profile.assert_called_once_with("test_720p")
        
        # Verify FFmpeg was called with profile settings
        call_args = mock_ffmpeg.call_args[0][0]
        assert "-c:v" in call_args
        assert "hevc_videotoolbox" in call_args
        assert "-b:v" in call_args
        assert "2M" in call_args
        assert "-s" in call_args
        assert "1280x720" in call_args
        assert "-c:a" in call_args
        assert "aac" in call_args
        assert "-b:a" in call_args
        assert "128k" in call_args

    @patch("core.video_ops.get_profile")
    @patch("core.video_ops.run_ffmpeg")
    @patch("core.video_ops.ensure_output_dir")
    @patch("core.video_ops.validate_input_file")
    def test_cut_by_timestamps_uses_profile_when_specified(
        self,
        mock_validate,
        mock_ensure_dir,
        mock_ffmpeg,
        mock_get_profile,
        tmp_path,
    ):
        """Test that cut_by_timestamps uses specified profile for re-encoding."""
        from core.profiles import Profile
        
        mock_validate.return_value = True
        mock_ffmpeg.return_value = {"success": True, "returncode": 0}
        
        mock_profile = Profile(
            name="web_480p",
            description="Web profile",
            video_codec="libx264",
            video_bitrate=None,
            crf=23,
            preset="fast",
            resolution="854x480",
            audio_codec="aac",
            audio_bitrate="96k",
        )
        mock_get_profile.return_value = mock_profile
        
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        (output_dir / "clip_001.mp4").write_text("segment")
        
        cut_by_timestamps(
            "input.mp4",
            str(output_dir),
            [(0, 30)],
            copy_codec=False,
            prefix="clip",
            profile_name="web_480p",
        )
        
        # Verify profile settings in FFmpeg args
        call_args = mock_ffmpeg.call_args[0][0]
        assert "libx264" in call_args
        assert "-crf" in call_args
        assert "23" in call_args
        assert "-preset" in call_args
        assert "fast" in call_args
        assert "854x480" in call_args

    @patch("core.video_ops.get_profile")
    @patch("core.video_ops.run_ffmpeg")
    @patch("core.video_ops.cleanup_temp_files")
    @patch("core.video_ops.generate_temp_filename")
    @patch("core.video_ops.ensure_output_dir")
    @patch("core.video_ops.get_video_info")
    @patch("core.video_ops.validate_input_file")
    def test_concat_videos_uses_profile_when_specified(
        self,
        mock_validate,
        mock_video_info,
        mock_ensure_dir,
        mock_temp_filename,
        mock_cleanup,
        mock_ffmpeg,
        mock_get_profile,
        tmp_path,
    ):
        """Test that concat_videos uses specified profile for re-encoding."""
        from core.profiles import Profile
        
        mock_validate.return_value = True
        mock_video_info.return_value = {"codec": "h264", "width": 1920, "height": 1080"}
        mock_temp_filename.return_value = str(tmp_path / "concat.txt")
        mock_ffmpeg.return_value = {"success": True, "returncode": 0}
        
        mock_profile = Profile(
            name="movie_1080p",
            description="Movie profile",
            video_codec="hevc_videotoolbox",
            video_bitrate="4M",
            resolution="source",
            audio_codec="aac",
            audio_bitrate="192k",
        )
        mock_get_profile.return_value = mock_profile
        
        output_file = tmp_path / "output.mp4"
        output_file.write_text("video")
        
        concat_videos(
            ["video1.mp4", "video2.mp4"],
            str(output_file),
            copy_codec=False,
            profile_name="movie_1080p",
        )
        
        # Verify profile was used
        call_args = mock_ffmpeg.call_args[0][0]
        assert "hevc_videotoolbox" in call_args
        assert "4M" in call_args
        assert "192k" in call_args

    @patch("core.video_ops.get_profile")
    @patch("core.video_ops.run_ffmpeg")
    @patch("core.video_ops.check_disk_space")
    @patch("core.video_ops.get_file_size")
    @patch("core.video_ops.ensure_output_dir")
    @patch("core.video_ops.get_video_info")
    @patch("core.video_ops.validate_input_file")
    def test_cut_with_invalid_profile_raises_error(
        self,
        mock_validate,
        mock_video_info,
        mock_ensure_dir,
        mock_file_size,
        mock_check_space,
        mock_ffmpeg,
        mock_get_profile,
        tmp_path,
    ):
        """Test that invalid profile name raises appropriate error."""
        from core.profiles import ProfileNotFoundError
        
        mock_validate.return_value = True
        mock_video_info.return_value = {"duration": 60.0}
        mock_file_size.return_value = 1024 * 1024
        mock_check_space.return_value = True
        
        # Mock profile not found
        mock_get_profile.side_effect = ProfileNotFoundError("Profile 'invalid' not found")
        
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        # Should raise InvalidInputError
        with pytest.raises(InvalidInputError) as exc_info:
            cut_by_duration(
                "input.mp4",
                str(output_dir),
                60,
                copy_codec=False,
                profile_name="invalid",
            )
        
        assert "not found" in str(exc_info.value).lower()
