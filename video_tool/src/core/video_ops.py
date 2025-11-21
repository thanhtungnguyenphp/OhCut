"""Video operations module for cutting, concatenating, and manipulating videos.

This module provides core video operations including:
- Cutting videos into segments
- Concatenating multiple videos
- Adding intro/outro clips
- Inserting advertisements
"""

import logging
import math
from pathlib import Path
from typing import List, Optional

from .ffmpeg_runner import run_ffmpeg, FFmpegError
from .profiles import get_profile, ProfileNotFoundError
from .database import Database, JobStatus
from ..utils.file_utils import (
    validate_input_file,
    get_video_info,
    ensure_output_dir,
    check_disk_space,
    InvalidInputError,
)

logger = logging.getLogger(__name__)


def cut_by_duration(
    input_path: str,
    output_dir: str,
    segment_duration: int,
    copy_codec: bool = True,
    prefix: str = "part",
    start_number: int = 1,
    profile_name: Optional[str] = None,
    track_job: bool = False,
) -> List[str]:
    """Cut video into segments by duration.

    This function splits a video into multiple segments of specified duration.
    The last segment may be shorter if the video duration is not evenly divisible.

    Args:
        input_path: Path to input video file.
        output_dir: Directory where output segments will be saved.
        segment_duration: Duration of each segment in seconds.
        copy_codec: If True, copy codecs without re-encoding (faster).
                   If False, re-encode the video.
        prefix: Prefix for output filenames (default: "part").
        start_number: Starting number for segment numbering (default: 1).
        profile_name: Encoding profile name to use when copy_codec=False.
                     If None, uses default encoding settings.
        track_job: If True, create job record in database and track progress.
                  If False, operate without job tracking (default).

    Returns:
        List[str]: List of paths to created segment files.

    Raises:
        InvalidInputError: If input file is invalid or segment_duration <= 0.
        FFmpegError: If FFmpeg command fails.

    Example:
        >>> segments = cut_by_duration(
        ...     "movie.mp4",
        ...     "/output",
        ...     660,  # 11 minutes
        ...     prefix="movie"
        ... )
        >>> print(f"Created {len(segments)} segments")
        Created 10 segments
    """
    # Initialize job tracking if requested
    job_id = None
    db = None
    if track_job:
        db = Database()
        job_id = db.create_job(
            job_type="cut",
            input_files=[input_path],
            config={
                "segment_duration": segment_duration,
                "copy_codec": copy_codec,
                "prefix": prefix,
                "profile_name": profile_name,
            }
        )
        db.update_job_status(job_id, JobStatus.RUNNING)
        logger.info(f"Created job {job_id} for cut operation")
    
    # Validate inputs
    validate_input_file(input_path)

    if segment_duration <= 0:
        raise InvalidInputError(f"Segment duration must be positive, got: {segment_duration}")

    # Get video info
    logger.info(f"Getting video info for: {input_path}")
    video_info = get_video_info(input_path)
    total_duration = video_info["duration"]

    if total_duration <= 0:
        raise InvalidInputError(f"Video has invalid duration: {total_duration}")

    # Calculate number of segments
    num_segments = math.ceil(total_duration / segment_duration)
    logger.info(
        f"Splitting {total_duration}s video into {num_segments} segments "
        f"of {segment_duration}s each"
    )

    # Ensure output directory exists
    ensure_output_dir(output_dir)

    # Check disk space (estimate 1.2x input size for safety)
    from utils.file_utils import get_file_size

    input_size = get_file_size(input_path)
    required_space = int(input_size * 1.2)
    check_disk_space(required_space, output_dir, buffer_gb=1.0)

    # Prepare output pattern
    # FFmpeg segment format: prefix_001.mp4, prefix_002.mp4, etc.
    input_ext = Path(input_path).suffix
    output_pattern = str(Path(output_dir) / f"{prefix}_%03d{input_ext}")

    # Build FFmpeg command
    args = [
        "-i", input_path,
        "-f", "segment",  # Use segment muxer
        "-segment_time", str(segment_duration),  # Duration per segment
        "-segment_start_number", str(start_number),  # Starting number
        "-reset_timestamps", "1",  # Reset timestamps for each segment
    ]

    if copy_codec:
        # Copy codecs without re-encoding (fast)
        args.extend(["-c", "copy"])
        logger.info("Using codec copy mode (no re-encoding)")
    else:
        # Re-encode with profile or default settings
        if profile_name:
            # Use specified profile
            try:
                profile = get_profile(profile_name)
                logger.info(f"Using profile: {profile_name}")
                
                # Apply profile settings
                args.extend(["-c:v", profile.video_codec])
                
                # Video quality settings
                if profile.crf is not None:
                    args.extend(["-crf", str(profile.crf)])
                elif profile.video_bitrate:
                    args.extend(["-b:v", profile.video_bitrate])
                
                # Preset
                if profile.preset:
                    args.extend(["-preset", profile.preset])
                
                # Resolution
                if profile.resolution != 'source':
                    resolution_tuple = profile.get_resolution_tuple()
                    if resolution_tuple:
                        width, height = resolution_tuple
                        args.extend(["-s", f"{width}x{height}"])
                
                # FPS
                if profile.fps and profile.fps != 'source':
                    args.extend(["-r", str(profile.fps)])
                
                # Audio settings
                args.extend(["-c:a", profile.audio_codec])
                if profile.audio_codec != 'copy':
                    args.extend(["-b:a", profile.audio_bitrate])
                
            except ProfileNotFoundError as e:
                logger.error(f"Profile error: {e}")
                raise InvalidInputError(str(e))
        else:
            # Use default re-encoding settings
            args.extend([
                "-c:v", "libx264",  # H.264 video
                "-preset", "medium",  # Encoding preset
                "-crf", "23",  # Quality (lower = better, 18-28 reasonable)
                "-c:a", "aac",  # AAC audio
                "-b:a", "128k",  # Audio bitrate
            ])
            logger.info("Using default re-encoding settings")

    args.append(output_pattern)

    # Execute FFmpeg
    logger.info(f"Starting video segmentation...")
    try:
        result = run_ffmpeg(args)
    except FFmpegError as e:
        logger.error(f"Failed to cut video: {e}")
        if track_job and job_id and db:
            db.update_job_status(
                job_id,
                JobStatus.FAILED,
                error_message=str(e)
            )
        raise

    # Collect output files
    output_files = []
    output_dir_path = Path(output_dir)

    for i in range(num_segments):
        segment_num = start_number + i
        segment_file = output_dir_path / f"{prefix}_{segment_num:03d}{input_ext}"

        if segment_file.exists():
            output_files.append(str(segment_file))
            logger.debug(f"Created segment {segment_num}: {segment_file.name}")
        else:
            logger.warning(f"Expected segment not found: {segment_file}")

    if not output_files:
        error = FFmpegError("No output segments were created", -1)
        if track_job and job_id and db:
            db.update_job_status(
                job_id,
                JobStatus.FAILED,
                error_message=str(error)
            )
        raise error

    # Mark job as completed if tracking
    if track_job and job_id and db:
        db.update_job_status(
            job_id,
            JobStatus.COMPLETED,
            progress=100.0,
            output_files=output_files
        )
        logger.info(f"Job {job_id} completed successfully")

    logger.info(f"Successfully created {len(output_files)} segments")
    return output_files


def cut_by_timestamps(
    input_path: str,
    output_dir: str,
    timestamps: List[tuple],
    copy_codec: bool = True,
    prefix: str = "part",
    profile_name: Optional[str] = None,
) -> List[str]:
    """Cut video into segments by specific timestamps.

    Args:
        input_path: Path to input video file.
        output_dir: Directory where output segments will be saved.
        timestamps: List of (start, end) tuples in seconds.
                   Example: [(0, 60), (60, 120), (120, 180)]
        copy_codec: If True, copy codecs without re-encoding.
        prefix: Prefix for output filenames.
        profile_name: Encoding profile name to use when copy_codec=False.
                     If None, uses default encoding settings.

    Returns:
        List[str]: List of paths to created segment files.

    Raises:
        InvalidInputError: If input file or timestamps are invalid.
        FFmpegError: If FFmpeg command fails.

    Example:
        >>> segments = cut_by_timestamps(
        ...     "movie.mp4",
        ...     "/output",
        ...     [(0, 300), (300, 600), (600, 900)],  # 3x 5-minute segments
        ...     prefix="clip"
        ... )
    """
    # Validate inputs
    validate_input_file(input_path)

    if not timestamps:
        raise InvalidInputError("Timestamps list cannot be empty")

    # Validate timestamps
    for i, (start, end) in enumerate(timestamps):
        if start < 0 or end < 0:
            raise InvalidInputError(f"Timestamp {i}: negative values not allowed")
        if end <= start:
            raise InvalidInputError(f"Timestamp {i}: end must be greater than start")

    # Ensure output directory exists
    ensure_output_dir(output_dir)

    # Get input file extension
    input_ext = Path(input_path).suffix
    output_files = []

    # Process each timestamp
    for i, (start, end) in enumerate(timestamps, 1):
        duration = end - start
        output_file = Path(output_dir) / f"{prefix}_{i:03d}{input_ext}"

        logger.info(f"Cutting segment {i}: {start}s to {end}s (duration: {duration}s)")

        # Build FFmpeg command
        args = [
            "-i", input_path,
            "-ss", str(start),  # Start time
            "-t", str(duration),  # Duration
        ]

        if copy_codec:
            args.extend(["-c", "copy"])
        else:
            # Re-encode with profile or default settings
            if profile_name:
                try:
                    profile = get_profile(profile_name)
                    # Apply profile settings
                    args.extend(["-c:v", profile.video_codec])
                    if profile.crf is not None:
                        args.extend(["-crf", str(profile.crf)])
                    elif profile.video_bitrate:
                        args.extend(["-b:v", profile.video_bitrate])
                    if profile.preset:
                        args.extend(["-preset", profile.preset])
                    if profile.resolution != 'source':
                        resolution_tuple = profile.get_resolution_tuple()
                        if resolution_tuple:
                            width, height = resolution_tuple
                            args.extend(["-s", f"{width}x{height}"])
                    if profile.fps and profile.fps != 'source':
                        args.extend(["-r", str(profile.fps)])
                    args.extend(["-c:a", profile.audio_codec])
                    if profile.audio_codec != 'copy':
                        args.extend(["-b:a", profile.audio_bitrate])
                except ProfileNotFoundError as e:
                    logger.error(f"Profile error: {e}")
                    raise InvalidInputError(str(e))
            else:
                args.extend([
                    "-c:v", "libx264",
                    "-preset", "medium",
                    "-crf", "23",
                    "-c:a", "aac",
                    "-b:a", "128k",
                ])

        args.append(str(output_file))

        # Execute FFmpeg
        try:
            result = run_ffmpeg(args)
            if output_file.exists():
                output_files.append(str(output_file))
                logger.debug(f"Created: {output_file.name}")
            else:
                logger.warning(f"Output file not created: {output_file}")
        except FFmpegError as e:
            logger.error(f"Failed to create segment {i}: {e}")
            raise

    if not output_files:
        raise FFmpegError("No output segments were created", -1)

    logger.info(f"Successfully created {len(output_files)} segments")
    return output_files


def concat_videos(
    input_files: List[str],
    output_path: str,
    copy_codec: bool = True,
    validate_compatibility: bool = True,
    profile_name: Optional[str] = None,
) -> str:
    """Concatenate multiple videos into a single video.

    This function merges multiple video files into one output file.
    For best results, all input videos should have the same:
    - Codec
    - Resolution
    - Frame rate
    - Audio settings

    Args:
        input_files: List of paths to input video files (in order).
        output_path: Path for the output concatenated video.
        copy_codec: If True, copy codecs without re-encoding (faster).
                   If False, re-encode all videos.
        validate_compatibility: If True, check that all videos have compatible
                               codecs/settings. If False, skip validation.
        profile_name: Encoding profile name to use when copy_codec=False.
                     If None, uses default encoding settings.

    Returns:
        str: Path to the output file.

    Raises:
        InvalidInputError: If input files are invalid or incompatible.
        FFmpegError: If FFmpeg command fails.

    Example:
        >>> output = concat_videos(
        ...     ["part1.mp4", "part2.mp4", "part3.mp4"],
        ...     "complete.mp4"
        ... )
        >>> print(f"Created: {output}")
    """
    # Validate inputs
    if not input_files:
        raise InvalidInputError("Input files list cannot be empty")

    if len(input_files) < 2:
        raise InvalidInputError("At least 2 input files are required for concatenation")

    # Validate all input files
    for input_file in input_files:
        validate_input_file(input_file)

    logger.info(f"Concatenating {len(input_files)} videos")

    # Check compatibility if requested
    if validate_compatibility:
        logger.info("Checking video compatibility...")
        first_video_info = get_video_info(input_files[0])
        first_codec = first_video_info["codec"]
        first_resolution = (first_video_info["width"], first_video_info["height"])

        for i, input_file in enumerate(input_files[1:], 1):
            video_info = get_video_info(input_file)
            if video_info["codec"] != first_codec:
                logger.warning(
                    f"Video {i} has different codec: {video_info['codec']} "
                    f"vs {first_codec}. Consider re-encoding."
                )
                if copy_codec:
                    raise InvalidInputError(
                        f"Videos have incompatible codecs. "
                        f"Use copy_codec=False to re-encode, or ensure all videos "
                        f"have the same codec."
                    )

            current_resolution = (video_info["width"], video_info["height"])
            if current_resolution != first_resolution:
                logger.warning(
                    f"Video {i} has different resolution: "
                    f"{current_resolution} vs {first_resolution}"
                )

    # Ensure output directory exists
    output_dir = str(Path(output_path).parent)
    ensure_output_dir(output_dir)

    # Create concat demuxer file list
    from utils.file_utils import generate_temp_filename, cleanup_temp_files

    concat_file = generate_temp_filename("concat_", ".txt")

    try:
        # Write file list in FFmpeg concat format
        with open(concat_file, "w") as f:
            for input_file in input_files:
                # Use absolute paths to avoid issues
                abs_path = str(Path(input_file).resolve())
                # Escape single quotes in path
                escaped_path = abs_path.replace("'", "'\\''")
                f.write(f"file '{escaped_path}'\n")

        logger.debug(f"Created concat file list: {concat_file}")

        # Build FFmpeg command
        args = [
            "-f", "concat",  # Use concat demuxer
            "-safe", "0",  # Allow absolute paths
            "-i", concat_file,  # Input is the concat file
        ]

        if copy_codec:
            # Copy codecs without re-encoding (fast)
            args.extend(["-c", "copy"])
            logger.info("Using codec copy mode (no re-encoding)")
        else:
            # Re-encode with profile or default settings
            if profile_name:
                try:
                    profile = get_profile(profile_name)
                    logger.info(f"Using profile: {profile_name}")
                    # Apply profile settings
                    args.extend(["-c:v", profile.video_codec])
                    if profile.crf is not None:
                        args.extend(["-crf", str(profile.crf)])
                    elif profile.video_bitrate:
                        args.extend(["-b:v", profile.video_bitrate])
                    if profile.preset:
                        args.extend(["-preset", profile.preset])
                    if profile.resolution != 'source':
                        resolution_tuple = profile.get_resolution_tuple()
                        if resolution_tuple:
                            width, height = resolution_tuple
                            args.extend(["-s", f"{width}x{height}"])
                    if profile.fps and profile.fps != 'source':
                        args.extend(["-r", str(profile.fps)])
                    args.extend(["-c:a", profile.audio_codec])
                    if profile.audio_codec != 'copy':
                        args.extend(["-b:a", profile.audio_bitrate])
                except ProfileNotFoundError as e:
                    logger.error(f"Profile error: {e}")
                    raise InvalidInputError(str(e))
            else:
                # Use default re-encoding settings
                args.extend([
                    "-c:v", "libx264",
                    "-preset", "medium",
                    "-crf", "23",
                    "-c:a", "aac",
                    "-b:a", "128k",
                ])
                logger.info("Using default re-encoding settings")

        args.append(output_path)

        # Execute FFmpeg
        logger.info(f"Starting video concatenation...")
        result = run_ffmpeg(args)

        # Verify output was created
        if not Path(output_path).exists():
            raise FFmpegError("Output file was not created", -1)

        logger.info(f"Successfully concatenated {len(input_files)} videos")
        return output_path

    finally:
        # Cleanup temp concat file
        cleanup_temp_files(concat_file)


def get_segment_info(video_path: str, segment_duration: int) -> dict:
    """Get information about how a video will be segmented.

    This is a utility function to preview segmentation without actually cutting.

    Args:
        video_path: Path to video file.
        segment_duration: Duration of each segment in seconds.

    Returns:
        Dict with segmentation info:
            - total_duration: Total video duration
            - segment_duration: Duration per segment
            - num_segments: Number of segments that will be created
            - last_segment_duration: Duration of the last segment

    Example:
        >>> info = get_segment_info("movie.mp4", 660)
        >>> print(f"Will create {info['num_segments']} segments")
        >>> print(f"Last segment: {info['last_segment_duration']}s")
    """
    video_info = get_video_info(video_path)
    total_duration = video_info["duration"]

    num_segments = math.ceil(total_duration / segment_duration)
    last_segment_duration = total_duration % segment_duration
    if last_segment_duration == 0:
        last_segment_duration = segment_duration

    return {
        "total_duration": total_duration,
        "segment_duration": segment_duration,
        "num_segments": num_segments,
        "last_segment_duration": last_segment_duration,
        "video_info": video_info,
    }
