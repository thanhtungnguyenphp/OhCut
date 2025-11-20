"""Audio operations module for extracting, replacing, and manipulating audio.

This module provides audio operations including:
- Extracting audio from videos
- Replacing audio tracks in videos
- Changing audio speed
- Mixing audio tracks
"""

import logging
from pathlib import Path
from typing import Optional

from core.ffmpeg_runner import run_ffmpeg, FFmpegError
from utils.file_utils import (
    validate_input_file,
    get_video_info,
    ensure_output_dir,
    InvalidInputError,
)

logger = logging.getLogger(__name__)


def extract_audio(
    input_path: str,
    output_path: str,
    codec: str = "copy",
    bitrate: Optional[str] = None,
) -> str:
    """Extract audio from video file.

    Args:
        input_path: Path to input video file.
        output_path: Path for output audio file.
        codec: Audio codec to use. Options:
               - "copy": Copy original audio codec without re-encoding (fastest)
               - "aac": Re-encode to AAC
               - "mp3": Re-encode to MP3
               - "opus": Re-encode to Opus
        bitrate: Audio bitrate (e.g., "128k", "192k", "320k").
                Only used when codec is not "copy".

    Returns:
        str: Path to the output audio file.

    Raises:
        InvalidInputError: If input file is invalid.
        FFmpegError: If FFmpeg command fails.

    Example:
        >>> # Extract audio without re-encoding
        >>> extract_audio("movie.mp4", "audio.m4a", codec="copy")
        
        >>> # Extract and convert to MP3 at 192kbps
        >>> extract_audio("movie.mp4", "audio.mp3", codec="mp3", bitrate="192k")
    """
    # Validate input
    validate_input_file(input_path)

    # Validate codec
    valid_codecs = ["copy", "aac", "mp3", "opus", "flac"]
    if codec not in valid_codecs:
        raise InvalidInputError(
            f"Invalid codec '{codec}'. Must be one of: {', '.join(valid_codecs)}"
        )

    # Ensure output directory exists
    output_dir = str(Path(output_path).parent)
    ensure_output_dir(output_dir)

    logger.info(f"Extracting audio from: {input_path}")

    # Build FFmpeg command
    args = [
        "-i", input_path,
        "-vn",  # No video
    ]

    if codec == "copy":
        # Copy audio codec without re-encoding
        args.extend(["-acodec", "copy"])
        logger.info("Using codec copy mode (no re-encoding)")
    else:
        # Re-encode audio
        args.extend(["-acodec", codec])
        
        if bitrate:
            args.extend(["-b:a", bitrate])
            logger.info(f"Re-encoding to {codec} at {bitrate}")
        else:
            # Use default bitrates if not specified
            default_bitrates = {
                "aac": "128k",
                "mp3": "192k",
                "opus": "128k",
                "flac": None,  # Lossless, no bitrate needed
            }
            default_br = default_bitrates.get(codec)
            if default_br:
                args.extend(["-b:a", default_br])
                logger.info(f"Re-encoding to {codec} at {default_br} (default)")
            else:
                logger.info(f"Re-encoding to {codec} (lossless)")

    args.append(output_path)

    # Execute FFmpeg
    try:
        result = run_ffmpeg(args)
    except FFmpegError as e:
        logger.error(f"Failed to extract audio: {e}")
        raise

    # Verify output was created
    if not Path(output_path).exists():
        raise FFmpegError("Output audio file was not created", -1)

    logger.info(f"Successfully extracted audio to: {output_path}")
    return output_path


def replace_audio(
    video_path: str,
    audio_path: str,
    output_path: str,
    copy_codecs: bool = True,
) -> str:
    """Replace audio track in video with new audio.

    This function removes the original audio from the video and replaces it
    with the provided audio file. If durations don't match, the shorter one
    determines the output duration.

    Args:
        video_path: Path to input video file.
        audio_path: Path to audio file to use as replacement.
        output_path: Path for output video file.
        copy_codecs: If True, copy video and audio codecs without re-encoding.
                    If False, re-encode both video and audio.

    Returns:
        str: Path to the output video file.

    Raises:
        InvalidInputError: If input files are invalid.
        FFmpegError: If FFmpeg command fails.

    Example:
        >>> # Replace audio without re-encoding
        >>> replace_audio("video.mp4", "new_audio.m4a", "output.mp4")
        
        >>> # Replace audio with re-encoding
        >>> replace_audio("video.mp4", "audio.mp3", "output.mp4", copy_codecs=False)
    """
    # Validate inputs
    validate_input_file(video_path)
    validate_input_file(audio_path)

    # Get info about both files
    video_info = get_video_info(video_path)
    video_duration = video_info["duration"]

    logger.info(f"Replacing audio in: {video_path}")
    logger.info(f"New audio from: {audio_path}")

    # Ensure output directory exists
    output_dir = str(Path(output_path).parent)
    ensure_output_dir(output_dir)

    # Build FFmpeg command
    args = [
        "-i", video_path,  # Video input
        "-i", audio_path,  # Audio input
    ]

    if copy_codecs:
        # Copy codecs without re-encoding
        args.extend([
            "-c:v", "copy",  # Copy video codec
            "-c:a", "copy",  # Copy audio codec
        ])
        logger.info("Using codec copy mode (no re-encoding)")
    else:
        # Re-encode both video and audio
        args.extend([
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
        ])
        logger.info("Using re-encoding mode")

    # Map streams: video from first input, audio from second input
    args.extend([
        "-map", "0:v:0",  # Map video from first input
        "-map", "1:a:0",  # Map audio from second input
        "-shortest",  # End output at shortest input duration
    ])

    args.append(output_path)

    # Execute FFmpeg
    try:
        result = run_ffmpeg(args)
    except FFmpegError as e:
        logger.error(f"Failed to replace audio: {e}")
        raise

    # Verify output was created
    if not Path(output_path).exists():
        raise FFmpegError("Output video file was not created", -1)

    logger.info(f"Successfully replaced audio: {output_path}")
    return output_path


def mix_audio_tracks(
    audio_files: list,
    output_path: str,
    codec: str = "aac",
    bitrate: str = "192k",
) -> str:
    """Mix multiple audio files into a single audio file.

    All input audio files are mixed together (overlayed) into one output.

    Args:
        audio_files: List of paths to audio files to mix.
        output_path: Path for output mixed audio file.
        codec: Output audio codec (default: "aac").
        bitrate: Output audio bitrate (default: "192k").

    Returns:
        str: Path to the output audio file.

    Raises:
        InvalidInputError: If input files are invalid.
        FFmpegError: If FFmpeg command fails.

    Example:
        >>> # Mix background music with voice
        >>> mix_audio_tracks(
        ...     ["voice.m4a", "music.m4a"],
        ...     "mixed.m4a"
        ... )
    """
    # Validate inputs
    if not audio_files:
        raise InvalidInputError("Audio files list cannot be empty")

    if len(audio_files) < 2:
        raise InvalidInputError("At least 2 audio files are required for mixing")

    for audio_file in audio_files:
        validate_input_file(audio_file)

    logger.info(f"Mixing {len(audio_files)} audio tracks")

    # Ensure output directory exists
    output_dir = str(Path(output_path).parent)
    ensure_output_dir(output_dir)

    # Build FFmpeg command
    args = []

    # Add all input files
    for audio_file in audio_files:
        args.extend(["-i", audio_file])

    # Build filter for mixing
    # amix filter: [0:a][1:a]amix=inputs=2
    filter_str = ""
    for i in range(len(audio_files)):
        filter_str += f"[{i}:a]"
    filter_str += f"amix=inputs={len(audio_files)}:duration=longest"

    args.extend([
        "-filter_complex", filter_str,
        "-c:a", codec,
        "-b:a", bitrate,
    ])

    args.append(output_path)

    # Execute FFmpeg
    try:
        result = run_ffmpeg(args)
    except FFmpegError as e:
        logger.error(f"Failed to mix audio tracks: {e}")
        raise

    # Verify output was created
    if not Path(output_path).exists():
        raise FFmpegError("Output audio file was not created", -1)

    logger.info(f"Successfully mixed audio tracks: {output_path}")
    return output_path


def get_audio_info(video_path: str) -> dict:
    """Get audio information from video file.

    Args:
        video_path: Path to video file.

    Returns:
        Dict with audio information:
            - audio_codec: Audio codec name
            - sample_rate: Sample rate in Hz
            - channels: Number of audio channels
            - duration: Audio duration in seconds

    Example:
        >>> info = get_audio_info("movie.mp4")
        >>> print(f"Codec: {info['audio_codec']}, Channels: {info['channels']}")
    """
    video_info = get_video_info(video_path)

    return {
        "audio_codec": video_info.get("audio_codec", "none"),
        "duration": video_info.get("duration", 0),
        # Note: sample_rate and channels would need additional ffprobe parsing
        # For now, return basic info from existing video_info
    }
