"""
Profile Configuration System
Manages video encoding profiles for different use cases.
"""

import os
import yaml
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path


class ProfileError(Exception):
    """Base exception for profile-related errors."""

    pass


class ProfileNotFoundError(ProfileError):
    """Raised when a requested profile is not found."""

    pass


class InvalidProfileError(ProfileError):
    """Raised when a profile configuration is invalid."""

    pass


@dataclass
class Profile:
    """
    Represents a video encoding profile.

    Attributes:
        name: Profile name/identifier
        description: Human-readable description
        video_codec: FFmpeg video codec (e.g., libx264, hevc_videotoolbox)
        video_bitrate: Video bitrate (e.g., "2M", "3500k")
        resolution: Output resolution (e.g., "1920x1080", "source")
        audio_codec: FFmpeg audio codec (e.g., aac, mp3)
        audio_bitrate: Audio bitrate (e.g., "192k", "128k")
        preset: Encoding preset for software codecs (optional)
        crf: Constant Rate Factor for quality-based encoding (optional)
        fps: Target frames per second (optional, "source" to keep original)
        hardware_accel: Hardware acceleration method (optional)
    """

    name: str
    description: str
    video_codec: str
    audio_codec: str
    audio_bitrate: str
    video_bitrate: Optional[str] = None
    resolution: str = "source"
    preset: Optional[str] = None
    crf: Optional[int] = None
    fps: Optional[str] = "source"
    hardware_accel: Optional[str] = None

    def __post_init__(self):
        """Validate profile after initialization."""
        self._validate()

    def _validate(self):
        """Validate profile configuration."""
        # Validate video codec
        valid_video_codecs = [
            "libx264",
            "libx265",
            "hevc_videotoolbox",
            "h264_videotoolbox",
            "h264_nvenc",
            "hevc_nvenc",
            "h264_qsv",
            "hevc_qsv",
            "libvpx",
            "libvpx-vp9",
            "libaom-av1",
            "copy",
        ]
        if self.video_codec not in valid_video_codecs:
            raise InvalidProfileError(
                f"Invalid video codec '{self.video_codec}'. "
                f"Valid codecs: {', '.join(valid_video_codecs)}"
            )

        # Validate audio codec
        valid_audio_codecs = ["aac", "mp3", "opus", "flac", "libmp3lame", "copy"]
        if self.audio_codec not in valid_audio_codecs:
            raise InvalidProfileError(
                f"Invalid audio codec '{self.audio_codec}'. "
                f"Valid codecs: {', '.join(valid_audio_codecs)}"
            )

        # Validate preset (if provided)
        if self.preset:
            valid_presets = [
                "ultrafast",
                "superfast",
                "veryfast",
                "faster",
                "fast",
                "medium",
                "slow",
                "slower",
                "veryslow",
            ]
            if self.preset not in valid_presets:
                raise InvalidProfileError(
                    f"Invalid preset '{self.preset}'. " f"Valid presets: {', '.join(valid_presets)}"
                )

        # Validate CRF (if provided)
        if self.crf is not None:
            if not isinstance(self.crf, int) or not (0 <= self.crf <= 51):
                raise InvalidProfileError(
                    f"Invalid CRF value '{self.crf}'. Must be integer between 0-51."
                )

        # Validate bitrate or CRF is present (for non-copy codecs)
        if self.video_codec != "copy":
            if self.video_bitrate is None and self.crf is None:
                raise InvalidProfileError(
                    "Profile must specify either video_bitrate or crf "
                    "(for non-copy video codecs)"
                )

        # Validate resolution format
        if self.resolution != "source":
            if not self._is_valid_resolution(self.resolution):
                raise InvalidProfileError(
                    f"Invalid resolution format '{self.resolution}'. "
                    "Must be 'source' or 'WIDTHxHEIGHT' (e.g., '1920x1080')"
                )

        # Validate FPS
        if self.fps and self.fps != "source":
            try:
                fps_val = int(self.fps)
                if fps_val <= 0:
                    raise ValueError()
            except (ValueError, TypeError):
                raise InvalidProfileError(
                    f"Invalid FPS value '{self.fps}'. "
                    "Must be 'source' or positive integer (e.g., 30)"
                )

    @staticmethod
    def _is_valid_resolution(resolution: str) -> bool:
        """Check if resolution string is valid (e.g., '1920x1080')."""
        try:
            parts = resolution.split("x")
            if len(parts) != 2:
                return False
            width, height = int(parts[0]), int(parts[1])
            return width > 0 and height > 0
        except (ValueError, AttributeError):
            return False

    def get_resolution_tuple(self) -> Optional[Tuple[int, int]]:
        """
        Parse resolution to (width, height) tuple.
        Returns None if resolution is 'source'.
        """
        if self.resolution == "source":
            return None
        parts = self.resolution.split("x")
        return (int(parts[0]), int(parts[1]))

    def uses_hardware_acceleration(self) -> bool:
        """Check if profile uses hardware acceleration."""
        hw_codecs = [
            "hevc_videotoolbox",
            "h264_videotoolbox",
            "h264_nvenc",
            "hevc_nvenc",
            "h264_qsv",
            "hevc_qsv",
        ]
        return self.video_codec in hw_codecs or bool(self.hardware_accel)

    def to_dict(self) -> Dict[str, Any]:
        """Convert profile to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "video_codec": self.video_codec,
            "video_bitrate": self.video_bitrate,
            "resolution": self.resolution,
            "audio_codec": self.audio_codec,
            "audio_bitrate": self.audio_bitrate,
            "preset": self.preset,
            "crf": self.crf,
            "fps": self.fps,
            "hardware_accel": self.hardware_accel,
        }


# Cache for loaded profiles
_profiles_cache: Optional[Dict[str, Profile]] = None
_default_profile: Optional[str] = None


def get_profiles_path() -> Path:
    """Get the path to profiles.yaml configuration file."""
    # Get the directory of this file
    current_dir = Path(__file__).parent
    # Navigate to configs directory
    configs_dir = current_dir.parent.parent / "configs"
    profiles_path = configs_dir / "profiles.yaml"

    if not profiles_path.exists():
        raise ProfileError(f"Profiles configuration file not found: {profiles_path}")

    return profiles_path


def load_profiles(force_reload: bool = False) -> Dict[str, Profile]:
    """
    Load all profiles from profiles.yaml.

    Args:
        force_reload: If True, reload profiles even if cached

    Returns:
        Dictionary mapping profile names to Profile objects

    Raises:
        ProfileError: If profiles cannot be loaded
        InvalidProfileError: If a profile configuration is invalid
    """
    global _profiles_cache, _default_profile

    # Return cached profiles if available
    if _profiles_cache is not None and not force_reload:
        return _profiles_cache

    try:
        profiles_path = get_profiles_path()

        with open(profiles_path, "r") as f:
            data = yaml.safe_load(f)

        if not data or "profiles" not in data:
            raise ProfileError("Invalid profiles.yaml: missing 'profiles' key")

        profiles_dict = {}
        for name, config in data["profiles"].items():
            try:
                # Add name to config
                config["name"] = name
                profile = Profile(**config)
                profiles_dict[name] = profile
            except TypeError as e:
                raise InvalidProfileError(f"Invalid configuration for profile '{name}': {e}")

        # Load default profile setting
        _default_profile = data.get("default_profile", "clip_720p")
        if _default_profile not in profiles_dict:
            raise ProfileError(f"Default profile '{_default_profile}' not found in profiles")

        # Cache the profiles
        _profiles_cache = profiles_dict

        return profiles_dict

    except yaml.YAMLError as e:
        raise ProfileError(f"Failed to parse profiles.yaml: {e}")
    except IOError as e:
        raise ProfileError(f"Failed to read profiles.yaml: {e}")


def get_profile(name: str) -> Profile:
    """
    Get a specific profile by name.

    Args:
        name: Profile name

    Returns:
        Profile object

    Raises:
        ProfileNotFoundError: If profile is not found
    """
    profiles = load_profiles()

    if name not in profiles:
        available = ", ".join(profiles.keys())
        raise ProfileNotFoundError(f"Profile '{name}' not found. Available profiles: {available}")

    return profiles[name]


def get_default_profile() -> Profile:
    """
    Get the default profile.

    Returns:
        Default Profile object
    """
    load_profiles()  # Ensure profiles are loaded
    return get_profile(_default_profile)


def list_profiles() -> List[str]:
    """
    Get list of all available profile names.

    Returns:
        List of profile names
    """
    profiles = load_profiles()
    return list(profiles.keys())


def validate_profile(profile: Profile) -> bool:
    """
    Validate a profile configuration.

    Args:
        profile: Profile object to validate

    Returns:
        True if valid

    Raises:
        InvalidProfileError: If profile is invalid
    """
    # Validation happens in Profile.__post_init__
    # This function is mainly for explicit validation calls
    profile._validate()
    return True


def apply_profile_to_ffmpeg_args(profile: Profile, input_path: str, output_path: str) -> List[str]:
    """
    Generate FFmpeg command arguments from a profile.

    Args:
        profile: Profile to apply
        input_path: Input file path
        output_path: Output file path

    Returns:
        List of FFmpeg command arguments
    """
    args = ["-i", input_path]

    # Video codec
    args.extend(["-c:v", profile.video_codec])

    # Video bitrate or CRF
    if profile.crf is not None:
        args.extend(["-crf", str(profile.crf)])
    elif profile.video_bitrate:
        args.extend(["-b:v", profile.video_bitrate])

    # Preset (for software codecs)
    if profile.preset:
        args.extend(["-preset", profile.preset])

    # Resolution
    if profile.resolution != "source":
        resolution_tuple = profile.get_resolution_tuple()
        if resolution_tuple:
            width, height = resolution_tuple
            args.extend(["-s", f"{width}x{height}"])

    # FPS
    if profile.fps and profile.fps != "source":
        args.extend(["-r", str(profile.fps)])

    # Audio codec
    args.extend(["-c:a", profile.audio_codec])

    # Audio bitrate
    if profile.audio_codec != "copy":
        args.extend(["-b:a", profile.audio_bitrate])

    # Output file
    args.append(output_path)

    return args


def get_profile_summary(profile: Profile) -> str:
    """
    Get a human-readable summary of a profile.

    Args:
        profile: Profile object

    Returns:
        Formatted summary string
    """
    lines = [
        f"Profile: {profile.name}",
        f"Description: {profile.description}",
        f"",
        f"Video:",
        f"  Codec: {profile.video_codec}",
    ]

    if profile.video_bitrate:
        lines.append(f"  Bitrate: {profile.video_bitrate}")
    if profile.crf is not None:
        lines.append(f"  CRF: {profile.crf}")

    lines.append(f"  Resolution: {profile.resolution}")

    if profile.preset:
        lines.append(f"  Preset: {profile.preset}")
    if profile.fps:
        lines.append(f"  FPS: {profile.fps}")
    if profile.hardware_accel:
        lines.append(f"  Hardware Accel: {profile.hardware_accel}")

    lines.extend(
        [
            f"",
            f"Audio:",
            f"  Codec: {profile.audio_codec}",
            f"  Bitrate: {profile.audio_bitrate}",
        ]
    )

    return "\n".join(lines)
