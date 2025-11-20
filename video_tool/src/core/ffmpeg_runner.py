"""FFmpeg runner module for executing FFmpeg commands.

This module provides a wrapper around FFmpeg command-line tool with:
- Command execution with error handling
- Progress parsing from stderr
- Logging of all commands and outputs
- Timeout mechanism
"""

import logging
import re
import shutil
import subprocess
from pathlib import Path
from typing import Callable, Dict, Optional

logger = logging.getLogger(__name__)


class FFmpegError(Exception):
    """Exception raised when FFmpeg command fails."""

    def __init__(self, message: str, returncode: int, stderr: str = ""):
        self.message = message
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(self.message)


class FFmpegNotFoundError(Exception):
    """Exception raised when FFmpeg is not installed or not found in PATH."""

    pass


def check_ffmpeg_installed() -> bool:
    """Check if FFmpeg is installed and available in PATH.

    Returns:
        bool: True if FFmpeg is installed, False otherwise.

    Example:
        >>> if check_ffmpeg_installed():
        ...     print("FFmpeg is ready")
    """
    return shutil.which("ffmpeg") is not None


def check_ffprobe_installed() -> bool:
    """Check if ffprobe is installed and available in PATH.

    Returns:
        bool: True if ffprobe is installed, False otherwise.
    """
    return shutil.which("ffprobe") is not None


def get_ffmpeg_version() -> str:
    """Get the installed FFmpeg version.

    Returns:
        str: FFmpeg version string.

    Raises:
        FFmpegNotFoundError: If FFmpeg is not installed.

    Example:
        >>> version = get_ffmpeg_version()
        >>> print(f"FFmpeg version: {version}")
    """
    if not check_ffmpeg_installed():
        raise FFmpegNotFoundError("FFmpeg is not installed or not found in PATH")

    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        # Extract version from first line: "ffmpeg version X.Y.Z ..."
        first_line = result.stdout.split("\n")[0]
        match = re.search(r"ffmpeg version ([\d.]+)", first_line)
        if match:
            return match.group(1)
        return first_line.strip()
    except subprocess.TimeoutExpired:
        raise FFmpegError("FFmpeg version check timed out", -1)
    except Exception as e:
        raise FFmpegError(f"Failed to get FFmpeg version: {str(e)}", -1)


def parse_ffmpeg_progress(stderr_line: str) -> Optional[Dict[str, any]]:
    """Parse progress information from FFmpeg stderr output.

    FFmpeg outputs progress in lines like:
    frame=  123 fps= 45 q=28.0 size=    1024kB time=00:00:05.00 bitrate=1677.7kbits/s speed=1.5x

    Args:
        stderr_line: A line from FFmpeg stderr output.

    Returns:
        Dict with parsed progress info or None if line doesn't contain progress.
        Keys: frame, fps, size_kb, time_seconds, bitrate, speed

    Example:
        >>> line = "frame=  100 fps=30 size=1024kB time=00:00:04.00 bitrate=2000kbits/s speed=1.0x"
        >>> progress = parse_ffmpeg_progress(line)
        >>> print(f"Progress: {progress['time_seconds']}s")
    """
    if not stderr_line or "frame=" not in stderr_line:
        return None

    progress = {}

    # Extract frame number
    frame_match = re.search(r"frame=\s*(\d+)", stderr_line)
    if frame_match:
        progress["frame"] = int(frame_match.group(1))

    # Extract fps
    fps_match = re.search(r"fps=\s*([\d.]+)", stderr_line)
    if fps_match:
        progress["fps"] = float(fps_match.group(1))

    # Extract size in KB
    size_match = re.search(r"size=\s*([\d.]+)kB", stderr_line)
    if size_match:
        progress["size_kb"] = float(size_match.group(1))

    # Extract time in format HH:MM:SS.ms
    time_match = re.search(r"time=(\d{2}):(\d{2}):(\d{2}\.\d{2})", stderr_line)
    if time_match:
        hours = int(time_match.group(1))
        minutes = int(time_match.group(2))
        seconds = float(time_match.group(3))
        progress["time_seconds"] = hours * 3600 + minutes * 60 + seconds

    # Extract bitrate
    bitrate_match = re.search(r"bitrate=\s*([\d.]+)kbits/s", stderr_line)
    if bitrate_match:
        progress["bitrate"] = float(bitrate_match.group(1))

    # Extract speed multiplier
    speed_match = re.search(r"speed=\s*([\d.]+)x", stderr_line)
    if speed_match:
        progress["speed"] = float(speed_match.group(1))

    return progress if progress else None


def run_ffmpeg(
    args: list,
    progress_callback: Optional[Callable[[Dict], None]] = None,
    timeout: Optional[int] = None,
) -> Dict[str, any]:
    """Execute FFmpeg command with given arguments.

    Args:
        args: List of FFmpeg arguments (without 'ffmpeg' itself).
        progress_callback: Optional callback function called with progress dict.
        timeout: Optional timeout in seconds. None means no timeout.

    Returns:
        Dict with execution results:
            - success (bool): Whether command succeeded
            - stdout (str): Standard output
            - stderr (str): Standard error output
            - returncode (int): Process return code

    Raises:
        FFmpegNotFoundError: If FFmpeg is not installed.
        FFmpegError: If FFmpeg command fails or times out.

    Example:
        >>> result = run_ffmpeg(["-i", "input.mp4", "-c", "copy", "output.mp4"])
        >>> if result["success"]:
        ...     print("Success!")
    """
    if not check_ffmpeg_installed():
        raise FFmpegNotFoundError("FFmpeg is not installed or not found in PATH")

    # Build full command
    cmd = ["ffmpeg"] + args

    # Log the command
    logger.info(f"Executing FFmpeg command: {' '.join(cmd)}")

    try:
        # Run FFmpeg process
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # Line buffered
        )

        stdout_lines = []
        stderr_lines = []

        # Read stderr line by line for progress updates
        if process.stderr:
            for line in iter(process.stderr.readline, ""):
                if not line:
                    break
                stderr_lines.append(line)

                # Parse and report progress if callback provided
                if progress_callback:
                    progress = parse_ffmpeg_progress(line)
                    if progress:
                        try:
                            progress_callback(progress)
                        except Exception as e:
                            logger.warning(f"Progress callback error: {e}")

        # Wait for process to complete
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            raise FFmpegError(
                f"FFmpeg command timed out after {timeout} seconds",
                -1,
                "".join(stderr_lines),
            )

        # Read any remaining output
        if process.stdout:
            stdout_lines = process.stdout.read().splitlines()

        stdout = "\n".join(stdout_lines) if stdout_lines else ""
        stderr = "".join(stderr_lines) if stderr_lines else ""
        returncode = process.returncode

        result = {
            "success": returncode == 0,
            "stdout": stdout,
            "stderr": stderr,
            "returncode": returncode,
        }

        if returncode != 0:
            error_msg = f"FFmpeg command failed with return code {returncode}"
            logger.error(f"{error_msg}\nCommand: {' '.join(cmd)}\nStderr: {stderr}")
            raise FFmpegError(error_msg, returncode, stderr)

        logger.info(f"FFmpeg command completed successfully")
        return result

    except FFmpegError:
        raise
    except Exception as e:
        error_msg = f"Unexpected error executing FFmpeg: {str(e)}"
        logger.error(error_msg)
        raise FFmpegError(error_msg, -1)


def run_ffprobe(args: list, timeout: Optional[int] = 30) -> Dict[str, any]:
    """Execute ffprobe command with given arguments.

    Args:
        args: List of ffprobe arguments (without 'ffprobe' itself).
        timeout: Optional timeout in seconds. Default is 30.

    Returns:
        Dict with execution results:
            - success (bool): Whether command succeeded
            - stdout (str): Standard output
            - stderr (str): Standard error output
            - returncode (int): Process return code

    Raises:
        FFmpegNotFoundError: If ffprobe is not installed.
        FFmpegError: If ffprobe command fails.

    Example:
        >>> result = run_ffprobe(["-v", "error", "-show_format", "input.mp4"])
        >>> if result["success"]:
        ...     print(result["stdout"])
    """
    if not check_ffprobe_installed():
        raise FFmpegNotFoundError("ffprobe is not installed or not found in PATH")

    cmd = ["ffprobe"] + args
    logger.info(f"Executing ffprobe command: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        response = {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }

        if result.returncode != 0:
            error_msg = f"ffprobe command failed with return code {result.returncode}"
            logger.error(f"{error_msg}\nStderr: {result.stderr}")
            raise FFmpegError(error_msg, result.returncode, result.stderr)

        logger.info("ffprobe command completed successfully")
        return response

    except subprocess.TimeoutExpired:
        raise FFmpegError(f"ffprobe command timed out after {timeout} seconds", -1)
    except FFmpegError:
        raise
    except Exception as e:
        error_msg = f"Unexpected error executing ffprobe: {str(e)}"
        logger.error(error_msg)
        raise FFmpegError(error_msg, -1)
