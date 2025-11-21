"""
Unit tests for profile configuration system.
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, mock_open

from src.core.profiles import (
    Profile,
    ProfileError,
    ProfileNotFoundError,
    InvalidProfileError,
    load_profiles,
    get_profile,
    get_default_profile,
    list_profiles,
    validate_profile,
    apply_profile_to_ffmpeg_args,
    get_profile_summary,
    _profiles_cache,
)


class TestProfileDataclass:
    """Test Profile dataclass and validation."""

    def test_valid_profile_creation(self):
        """Test creating a valid profile."""
        profile = Profile(
            name="test_profile",
            description="Test profile",
            video_codec="libx264",
            video_bitrate="2M",
            resolution="1920x1080",
            audio_codec="aac",
            audio_bitrate="128k",
            preset="fast",
            fps="30",
        )

        assert profile.name == "test_profile"
        assert profile.video_codec == "libx264"
        assert profile.resolution == "1920x1080"

    def test_profile_with_crf(self):
        """Test profile with CRF instead of bitrate."""
        profile = Profile(
            name="crf_profile",
            description="CRF-based profile",
            video_codec="libx265",
            crf=22,
            resolution="source",
            audio_codec="aac",
            audio_bitrate="192k",
            preset="medium",
        )

        assert profile.crf == 22
        assert profile.video_bitrate is None

    def test_invalid_video_codec(self):
        """Test validation fails with invalid video codec."""
        with pytest.raises(InvalidProfileError, match="Invalid video codec"):
            Profile(
                name="invalid",
                description="Invalid codec",
                video_codec="invalid_codec",
                video_bitrate="2M",
                resolution="1920x1080",
                audio_codec="aac",
                audio_bitrate="128k",
            )

    def test_invalid_audio_codec(self):
        """Test validation fails with invalid audio codec."""
        with pytest.raises(InvalidProfileError, match="Invalid audio codec"):
            Profile(
                name="invalid",
                description="Invalid audio codec",
                video_codec="libx264",
                video_bitrate="2M",
                resolution="1920x1080",
                audio_codec="invalid_audio",
                audio_bitrate="128k",
            )

    def test_invalid_preset(self):
        """Test validation fails with invalid preset."""
        with pytest.raises(InvalidProfileError, match="Invalid preset"):
            Profile(
                name="invalid",
                description="Invalid preset",
                video_codec="libx264",
                video_bitrate="2M",
                resolution="1920x1080",
                audio_codec="aac",
                audio_bitrate="128k",
                preset="invalid_preset",
            )

    def test_invalid_crf_value(self):
        """Test validation fails with invalid CRF value."""
        with pytest.raises(InvalidProfileError, match="Invalid CRF"):
            Profile(
                name="invalid",
                description="Invalid CRF",
                video_codec="libx265",
                crf=52,  # Out of range
                resolution="source",
                audio_codec="aac",
                audio_bitrate="192k",
            )

    def test_missing_bitrate_and_crf(self):
        """Test validation fails when both bitrate and CRF are missing."""
        with pytest.raises(InvalidProfileError, match="video_bitrate or crf"):
            Profile(
                name="invalid",
                description="No bitrate or CRF",
                video_codec="libx264",
                resolution="1920x1080",
                audio_codec="aac",
                audio_bitrate="128k",
            )

    def test_invalid_resolution_format(self):
        """Test validation fails with invalid resolution format."""
        with pytest.raises(InvalidProfileError, match="Invalid resolution"):
            Profile(
                name="invalid",
                description="Invalid resolution",
                video_codec="libx264",
                video_bitrate="2M",
                resolution="1920",  # Missing height
                audio_codec="aac",
                audio_bitrate="128k",
            )

    def test_invalid_fps(self):
        """Test validation fails with invalid FPS."""
        with pytest.raises(InvalidProfileError, match="Invalid FPS"):
            Profile(
                name="invalid",
                description="Invalid FPS",
                video_codec="libx264",
                video_bitrate="2M",
                resolution="1920x1080",
                audio_codec="aac",
                audio_bitrate="128k",
                fps="invalid",
            )

    def test_get_resolution_tuple(self):
        """Test resolution parsing to tuple."""
        profile = Profile(
            name="test",
            description="Test",
            video_codec="libx264",
            video_bitrate="2M",
            resolution="1920x1080",
            audio_codec="aac",
            audio_bitrate="128k",
        )

        assert profile.get_resolution_tuple() == (1920, 1080)

    def test_get_resolution_tuple_source(self):
        """Test resolution tuple returns None for 'source'."""
        profile = Profile(
            name="test",
            description="Test",
            video_codec="libx264",
            video_bitrate="2M",
            resolution="source",
            audio_codec="aac",
            audio_bitrate="128k",
        )

        assert profile.get_resolution_tuple() is None

    def test_uses_hardware_acceleration(self):
        """Test hardware acceleration detection."""
        hw_profile = Profile(
            name="hw",
            description="Hardware accelerated",
            video_codec="hevc_videotoolbox",
            video_bitrate="4M",
            resolution="1920x1080",
            audio_codec="aac",
            audio_bitrate="192k",
        )

        assert hw_profile.uses_hardware_acceleration() is True

        sw_profile = Profile(
            name="sw",
            description="Software encoding",
            video_codec="libx264",
            video_bitrate="2M",
            resolution="1920x1080",
            audio_codec="aac",
            audio_bitrate="128k",
        )

        assert sw_profile.uses_hardware_acceleration() is False

    def test_to_dict(self):
        """Test profile conversion to dictionary."""
        profile = Profile(
            name="test",
            description="Test profile",
            video_codec="libx264",
            video_bitrate="2M",
            resolution="1920x1080",
            audio_codec="aac",
            audio_bitrate="128k",
            preset="fast",
        )

        profile_dict = profile.to_dict()
        assert profile_dict["name"] == "test"
        assert profile_dict["video_codec"] == "libx264"
        assert profile_dict["preset"] == "fast"


class TestProfileLoading:
    """Test profile loading from YAML."""

    def test_load_profiles(self):
        """Test loading profiles from config file."""
        # This will use the actual profiles.yaml file
        profiles = load_profiles(force_reload=True)

        assert isinstance(profiles, dict)
        assert len(profiles) > 0

        # Check some expected profiles exist
        assert "clip_720p" in profiles
        assert "movie_1080p" in profiles

    def test_load_profiles_caching(self):
        """Test that profiles are cached."""
        # First load
        profiles1 = load_profiles(force_reload=True)

        # Second load (should use cache)
        profiles2 = load_profiles(force_reload=False)

        # Should be the same object (cached)
        assert profiles1 is profiles2

    def test_get_profile_valid(self):
        """Test getting a valid profile by name."""
        profile = get_profile("clip_720p")

        assert profile.name == "clip_720p"
        assert isinstance(profile, Profile)

    def test_get_profile_invalid(self):
        """Test getting an invalid profile raises error."""
        with pytest.raises(ProfileNotFoundError, match="Profile 'nonexistent' not found"):
            get_profile("nonexistent")

    def test_get_default_profile(self):
        """Test getting the default profile."""
        profile = get_default_profile()

        assert isinstance(profile, Profile)
        # Default should be clip_720p based on profiles.yaml
        assert profile.name == "clip_720p"

    def test_list_profiles(self):
        """Test listing all profile names."""
        profile_names = list_profiles()

        assert isinstance(profile_names, list)
        assert len(profile_names) > 0
        assert "clip_720p" in profile_names
        assert "movie_1080p" in profile_names


class TestValidateProfile:
    """Test profile validation."""

    def test_validate_valid_profile(self):
        """Test validating a valid profile."""
        profile = Profile(
            name="test",
            description="Test",
            video_codec="libx264",
            video_bitrate="2M",
            resolution="1920x1080",
            audio_codec="aac",
            audio_bitrate="128k",
        )

        assert validate_profile(profile) is True

    def test_validate_invalid_profile(self):
        """Test validating an invalid profile raises error."""
        # Create a profile with invalid codec by bypassing __post_init__
        profile = Profile.__new__(Profile)
        profile.name = "invalid"
        profile.description = "Invalid"
        profile.video_codec = "invalid_codec"
        profile.video_bitrate = "2M"
        profile.resolution = "1920x1080"
        profile.audio_codec = "aac"
        profile.audio_bitrate = "128k"
        profile.preset = None
        profile.crf = None
        profile.fps = "source"
        profile.hardware_accel = None

        with pytest.raises(InvalidProfileError):
            validate_profile(profile)


class TestApplyProfileToFFmpegArgs:
    """Test generating FFmpeg arguments from profiles."""

    def test_apply_profile_with_bitrate(self):
        """Test applying profile with bitrate."""
        profile = Profile(
            name="test",
            description="Test",
            video_codec="libx264",
            video_bitrate="2M",
            resolution="1920x1080",
            audio_codec="aac",
            audio_bitrate="128k",
            preset="fast",
            fps="30",
        )

        args = apply_profile_to_ffmpeg_args(profile, "input.mp4", "output.mp4")

        assert "-i" in args
        assert "input.mp4" in args
        assert "-c:v" in args
        assert "libx264" in args
        assert "-b:v" in args
        assert "2M" in args
        assert "-s" in args
        assert "1920x1080" in args
        assert "-r" in args
        assert "30" in args
        assert "-c:a" in args
        assert "aac" in args
        assert "-b:a" in args
        assert "128k" in args
        assert "-preset" in args
        assert "fast" in args
        assert "output.mp4" in args

    def test_apply_profile_with_crf(self):
        """Test applying profile with CRF."""
        profile = Profile(
            name="test",
            description="Test",
            video_codec="libx265",
            crf=22,
            resolution="source",
            audio_codec="aac",
            audio_bitrate="192k",
            preset="medium",
        )

        args = apply_profile_to_ffmpeg_args(profile, "input.mp4", "output.mp4")

        assert "-crf" in args
        assert "22" in args
        assert "-b:v" not in args  # Bitrate should not be present
        assert "-s" not in args  # Resolution should not be set for 'source'

    def test_apply_profile_source_resolution(self):
        """Test applying profile with source resolution."""
        profile = Profile(
            name="test",
            description="Test",
            video_codec="libx264",
            video_bitrate="2M",
            resolution="source",
            audio_codec="aac",
            audio_bitrate="128k",
        )

        args = apply_profile_to_ffmpeg_args(profile, "input.mp4", "output.mp4")

        assert "-s" not in args  # Resolution should not be set

    def test_apply_profile_source_fps(self):
        """Test applying profile with source FPS."""
        profile = Profile(
            name="test",
            description="Test",
            video_codec="libx264",
            video_bitrate="2M",
            resolution="1920x1080",
            audio_codec="aac",
            audio_bitrate="128k",
            fps="source",
        )

        args = apply_profile_to_ffmpeg_args(profile, "input.mp4", "output.mp4")

        assert "-r" not in args  # FPS should not be set


class TestGetProfileSummary:
    """Test profile summary generation."""

    def test_get_profile_summary(self):
        """Test generating profile summary."""
        profile = Profile(
            name="test_profile",
            description="Test profile for testing",
            video_codec="libx264",
            video_bitrate="2M",
            resolution="1920x1080",
            audio_codec="aac",
            audio_bitrate="128k",
            preset="fast",
            fps="30",
        )

        summary = get_profile_summary(profile)

        assert "Profile: test_profile" in summary
        assert "Test profile for testing" in summary
        assert "libx264" in summary
        assert "2M" in summary
        assert "1920x1080" in summary
        assert "aac" in summary
        assert "128k" in summary
        assert "fast" in summary
        assert "30" in summary

    def test_get_profile_summary_with_crf(self):
        """Test generating profile summary with CRF."""
        profile = Profile(
            name="crf_profile",
            description="CRF-based profile",
            video_codec="libx265",
            crf=22,
            resolution="source",
            audio_codec="aac",
            audio_bitrate="192k",
            preset="medium",
        )

        summary = get_profile_summary(profile)

        assert "CRF: 22" in summary
        assert "source" in summary
