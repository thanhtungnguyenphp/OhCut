"""File utilities for video processing.

This module provides utilities for:
- File validation and checking
- Video information extraction using ffprobe
- Directory management
- Temporary file handling
- Atomic file operations
"""

import json
import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Optional

from core.ffmpeg_runner import run_ffprobe, FFmpegError, FFmpegNotFoundError

logger = logging.getLogger(__name__)


class InvalidInputError(Exception):
    """Exception raised when input file is invalid."""

    pass


class InsufficientDiskSpaceError(Exception):
    """Exception raised when there is not enough disk space."""

    pass


def validate_input_file(path: str) -> bool:
    """Validate that input file exists and is readable.

    Args:
        path: Path to the file to validate.

    Returns:
        bool: True if file is valid.

    Raises:
        InvalidInputError: If file doesn't exist, is not a file, or is not readable.

    Example:
        >>> validate_input_file("video.mp4")
        True
    """
    file_path = Path(path)

    if not file_path.exists():
        raise InvalidInputError(f"File does not exist: {path}")

    if not file_path.is_file():
        raise InvalidInputError(f"Path is not a file: {path}")

    if not os.access(file_path, os.R_OK):
        raise InvalidInputError(f"File is not readable: {path}")

    if file_path.stat().st_size == 0:
        raise InvalidInputError(f"File is empty: {path}")

    logger.info(f"File validated: {path}")
    return True


def get_video_info(path: str) -> Dict[str, any]:
    """Get video information using ffprobe.

    Extracts information including:
    - duration (seconds)
    - width (pixels)
    - height (pixels)
    - codec (video codec name)
    - bitrate (bits per second)
    - fps (frames per second)
    - audio_codec (audio codec name)
    - format (container format)

    Args:
        path: Path to video file.

    Returns:
        Dict with video information.

    Raises:
        InvalidInputError: If file is invalid.
        FFmpegError: If ffprobe fails.

    Example:
        >>> info = get_video_info("video.mp4")
        >>> print(f"Duration: {info['duration']}s")
        >>> print(f"Resolution: {info['width']}x{info['height']}")
    """
    # Validate file first
    validate_input_file(path)

    # Run ffprobe to get video info in JSON format
    args = [
        "-v", "error",  # Only show errors
        "-print_format", "json",  # Output as JSON
        "-show_format",  # Show format info
        "-show_streams",  # Show stream info
        path,
    ]

    try:
        result = run_ffprobe(args)
        data = json.loads(result["stdout"])
    except json.JSONDecodeError as e:
        raise FFmpegError(f"Failed to parse ffprobe output: {e}", -1)
    except FFmpegError:
        raise
    except Exception as e:
        raise FFmpegError(f"Failed to get video info: {e}", -1)

    # Extract video stream info
    video_stream = None
    audio_stream = None

    for stream in data.get("streams", []):
        if stream.get("codec_type") == "video" and video_stream is None:
            video_stream = stream
        elif stream.get("codec_type") == "audio" and audio_stream is None:
            audio_stream = stream

    if not video_stream:
        raise InvalidInputError(f"No video stream found in file: {path}")

    # Extract format info
    format_info = data.get("format", {})

    # Build info dict
    info = {
        "duration": float(format_info.get("duration", 0)),
        "width": int(video_stream.get("width", 0)),
        "height": int(video_stream.get("height", 0)),
        "codec": video_stream.get("codec_name", "unknown"),
        "bitrate": int(format_info.get("bit_rate", 0)),
        "format": format_info.get("format_name", "unknown"),
    }

    # Calculate FPS (frames per second)
    # FPS can be in format "30/1" or "30000/1001"
    fps_str = video_stream.get("r_frame_rate", "0/1")
    try:
        num, den = map(int, fps_str.split("/"))
        info["fps"] = round(num / den, 2) if den != 0 else 0
    except (ValueError, ZeroDivisionError):
        info["fps"] = 0

    # Add audio codec if available
    if audio_stream:
        info["audio_codec"] = audio_stream.get("codec_name", "none")
    else:
        info["audio_codec"] = "none"

    logger.info(f"Video info extracted: {path} - {info['duration']}s, "
                f"{info['width']}x{info['height']}, {info['codec']}")

    return info


def ensure_output_dir(path: str) -> None:
    """Ensure output directory exists, create if it doesn't.

    Args:
        path: Path to directory.

    Raises:
        OSError: If directory cannot be created.
        InvalidInputError: If path exists but is not a directory.

    Example:
        >>> ensure_output_dir("/output/videos")
    """
    dir_path = Path(path)

    if dir_path.exists():
        if not dir_path.is_dir():
            raise InvalidInputError(f"Path exists but is not a directory: {path}")
        logger.debug(f"Output directory exists: {path}")
    else:
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created output directory: {path}")
        except OSError as e:
            raise OSError(f"Failed to create directory {path}: {e}")


def generate_temp_filename(prefix: str = "video_tool", suffix: str = ".mp4") -> str:
    """Generate a temporary filename in system temp directory.

    Args:
        prefix: Prefix for temp filename.
        suffix: Suffix/extension for temp filename.

    Returns:
        str: Full path to temporary file.

    Example:
        >>> temp_file = generate_temp_filename("output", ".mp4")
        >>> print(temp_file)
        /tmp/output_abc123.mp4
    """
    fd, temp_path = tempfile.mkstemp(prefix=prefix + "_", suffix=suffix)
    os.close(fd)  # Close file descriptor, we just want the path
    logger.debug(f"Generated temp filename: {temp_path}")
    return temp_path


def atomic_move(src: str, dst: str) -> None:
    """Move file atomically from source to destination.

    This ensures that if the operation fails, the destination is not left
    in a partial state. The source file is only removed after successful copy.

    Args:
        src: Source file path.
        dst: Destination file path.

    Raises:
        InvalidInputError: If source doesn't exist.
        OSError: If move operation fails.

    Example:
        >>> atomic_move("/tmp/video.mp4", "/output/final.mp4")
    """
    src_path = Path(src)
    dst_path = Path(dst)

    if not src_path.exists():
        raise InvalidInputError(f"Source file does not exist: {src}")

    try:
        # Ensure destination directory exists
        ensure_output_dir(str(dst_path.parent))

        # Use shutil.move which handles cross-filesystem moves
        shutil.move(str(src_path), str(dst_path))
        logger.info(f"Moved file: {src} -> {dst}")

    except OSError as e:
        raise OSError(f"Failed to move file from {src} to {dst}: {e}")


def get_file_size(path: str) -> int:
    """Get file size in bytes.

    Args:
        path: Path to file.

    Returns:
        int: File size in bytes.

    Raises:
        InvalidInputError: If file doesn't exist.

    Example:
        >>> size = get_file_size("video.mp4")
        >>> print(f"Size: {size / 1024 / 1024:.2f} MB")
    """
    file_path = Path(path)

    if not file_path.exists():
        raise InvalidInputError(f"File does not exist: {path}")

    return file_path.stat().st_size


def get_free_disk_space(path: str = ".") -> int:
    """Get free disk space in bytes for the given path.

    Args:
        path: Path to check (default: current directory).

    Returns:
        int: Free disk space in bytes.

    Example:
        >>> free_space = get_free_disk_space("/output")
        >>> print(f"Free: {free_space / 1024 / 1024 / 1024:.2f} GB")
    """
    stat = shutil.disk_usage(path)
    return stat.free


def check_disk_space(required_bytes: int, path: str = ".", buffer_gb: float = 1.0) -> bool:
    """Check if there is enough disk space available.

    Args:
        required_bytes: Required space in bytes.
        path: Path to check (default: current directory).
        buffer_gb: Additional buffer space in GB (default: 1.0).

    Returns:
        bool: True if enough space is available.

    Raises:
        InsufficientDiskSpaceError: If not enough space available.

    Example:
        >>> check_disk_space(1024 * 1024 * 1024)  # Check for 1GB
        True
    """
    free_space = get_free_disk_space(path)
    buffer_bytes = int(buffer_gb * 1024 * 1024 * 1024)
    required_with_buffer = required_bytes + buffer_bytes

    if free_space < required_with_buffer:
        free_gb = free_space / 1024 / 1024 / 1024
        required_gb = required_with_buffer / 1024 / 1024 / 1024
        raise InsufficientDiskSpaceError(
            f"Insufficient disk space. Required: {required_gb:.2f}GB, "
            f"Available: {free_gb:.2f}GB"
        )

    logger.debug(f"Disk space check passed: {required_bytes} bytes required")
    return True


def cleanup_temp_files(*paths: str) -> None:
    """Clean up temporary files.

    Args:
        *paths: Variable number of file paths to delete.

    Example:
        >>> cleanup_temp_files("/tmp/file1.mp4", "/tmp/file2.mp4")
    """
    for path in paths:
        try:
            file_path = Path(path)
            if file_path.exists() and file_path.is_file():
                file_path.unlink()
                logger.debug(f"Cleaned up temp file: {path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup temp file {path}: {e}")


def get_safe_filename(filename: str) -> str:
    """Convert filename to safe version (remove/replace unsafe characters).

    Args:
        filename: Original filename.

    Returns:
        str: Safe filename.

    Example:
        >>> get_safe_filename("My Video: Part 1.mp4")
        'My_Video_Part_1.mp4'
    """
    # Replace unsafe characters with underscore
    unsafe_chars = '<>:"/\\|?*'
    safe_name = filename

    for char in unsafe_chars:
        safe_name = safe_name.replace(char, "_")

    # Remove leading/trailing whitespace and dots
    safe_name = safe_name.strip(". ")

    # Limit filename length (255 is max on most systems, leave room for path)
    if len(safe_name) > 200:
        name, ext = os.path.splitext(safe_name)
        safe_name = name[:200 - len(ext)] + ext

    return safe_name
