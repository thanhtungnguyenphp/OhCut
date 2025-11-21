#!/usr/bin/env python3
"""
Video Tool CLI
Command-line interface for video and audio processing.
"""

import sys
import os
from pathlib import Path
from typing import List, Optional
import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich import print as rprint

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core import ffmpeg_runner, video_ops, audio_ops, profiles
from src.core.database import Database, JobStatus
from src.utils import file_utils

# Initialize Typer app
app = typer.Typer(
    name="video-tool",
    help="Video and audio processing tool using FFmpeg",
    add_completion=False,
)

# Create subcommands
audio_app = typer.Typer(help="Audio operations")
profiles_app = typer.Typer(help="Profile management")
jobs_app = typer.Typer(help="Job management")
worker_app = typer.Typer(help="Worker management")

app.add_typer(audio_app, name="audio")
app.add_typer(profiles_app, name="profiles")
app.add_typer(jobs_app, name="jobs")
app.add_typer(worker_app, name="worker")

# Rich console for output
console = Console()


# Global state for options
class GlobalState:
    verbose: bool = False
    dry_run: bool = False
    log_file: Optional[str] = None


state = GlobalState()


@app.callback()
def main(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be done without executing"
    ),
    log_file: Optional[str] = typer.Option(None, "--log-file", help="Path to log file"),
):
    """
    Video Tool - Process videos and audio with FFmpeg

    A powerful command-line tool for video and audio processing tasks including
    cutting, concatenating, audio extraction/replacement, and more.
    """
    state.verbose = verbose
    state.dry_run = dry_run
    state.log_file = log_file

    # Check FFmpeg installation
    if not dry_run:
        if not ffmpeg_runner.check_ffmpeg_installed():
            console.print("[red]❌ Error: FFmpeg is not installed or not found in PATH[/red]")
            console.print("\nPlease install FFmpeg:")
            console.print("  macOS: brew install ffmpeg")
            console.print("  Linux: sudo apt install ffmpeg")
            raise typer.Exit(code=1)


@app.command()
def cut(
    input: str = typer.Option(..., "--input", "-i", help="Input video file"),
    output_dir: str = typer.Option(..., "--output-dir", "-o", help="Output directory for segments"),
    duration: int = typer.Option(
        11, "--duration", "-d", help="Duration of each segment in minutes"
    ),
    prefix: str = typer.Option("part", "--prefix", "-p", help="Prefix for output filenames"),
    no_copy: bool = typer.Option(False, "--no-copy", help="Force re-encode instead of codec copy"),
    profile: Optional[str] = typer.Option(
        None, "--profile", help="Encoding profile to use (if re-encoding)"
    ),
    track_job: bool = typer.Option(
        False, "--track-job", help="Track job in database for history and monitoring"
    ),
    async_mode: bool = typer.Option(
        False, "--async", help="Submit job to queue for background processing"
    ),
):
    """
    Cut video into segments by duration.

    Example:
        video-tool cut -i movie.mp4 -o ./output -d 11
    """
    console.print(f"\n[bold cyan]🎬 Cutting Video[/bold cyan]")
    console.print(f"Input: {input}")
    console.print(f"Duration: {duration} minutes per segment")
    console.print(f"Output: {output_dir}")

    # Validate input
    if not os.path.exists(input):
        console.print(f"[red]❌ Error: Input file not found: {input}[/red]")
        raise typer.Exit(code=1)

    if state.dry_run:
        console.print("\n[yellow]🔍 DRY RUN - No files will be created[/yellow]")

        # Get video info
        try:
            info = file_utils.get_video_info(input)
            duration_sec = info["duration"]
            segment_duration_sec = duration * 60
            num_segments = (duration_sec + segment_duration_sec - 1) // segment_duration_sec

            console.print(f"\nVideo duration: {duration_sec:.1f} seconds")
            console.print(f"Segment duration: {segment_duration_sec} seconds")
            console.print(f"Number of segments: {num_segments}")
            console.print(f"\nWould create files:")
            for i in range(num_segments):
                console.print(f"  - {output_dir}/{prefix}_{i+1:03d}.mp4")
        except Exception as e:
            console.print(f"[red]❌ Error getting video info: {e}[/red]")
            raise typer.Exit(code=1)

        return

    # Handle async mode
    if async_mode:
        try:
            db = Database()
            job_id = db.create_job(
                job_type="cut",
                input_files=[input],
                config={
                    "output_dir": output_dir,
                    "segment_duration": duration * 60,
                    "copy_codec": not no_copy,
                    "prefix": prefix,
                    "profile_name": profile,
                },
            )

            console.print(f"\n[green]✅ Job submitted successfully![/green]")
            console.print(f"Job ID: [cyan]{job_id}[/cyan]")
            console.print(f"\nTo monitor progress:")
            console.print(f"  video-tool jobs show {job_id}")
            console.print(f"  video-tool jobs logs {job_id}")
            console.print(
                f"\n[yellow]Note: Make sure workers are running with 'video-tool worker start'[/yellow]\n"
            )

        except Exception as e:
            console.print(f"\n[red]❌ Error submitting job: {e}[/red]")
            if state.verbose:
                import traceback

                console.print(traceback.format_exc())
            raise typer.Exit(code=1)
        return

    # Execute cut synchronously
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Cutting video...", total=None)

            def progress_callback(info: dict):
                if "percent" in info:
                    progress.update(task, completed=info["percent"], total=100)

            output_files = video_ops.cut_by_duration(
                input_path=input,
                output_dir=output_dir,
                segment_duration=duration * 60,  # Convert to seconds
                copy_codec=not no_copy,
                prefix=prefix,
                profile_name=profile,
                track_job=track_job,
            )

        console.print(f"\n[green]✅ Success! Created {len(output_files)} segments:[/green]")
        for f in output_files:
            console.print(f"  ✓ {f}")

        if track_job:
            console.print(
                f"\n[cyan]ℹ️  Job tracked in database. Use 'video-tool jobs list' to view.[/cyan]"
            )

    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]")
        if state.verbose:
            import traceback

            console.print(traceback.format_exc())
        raise typer.Exit(code=1)


@app.command()
def concat(
    inputs: List[str] = typer.Option(
        ..., "--inputs", "-i", help="Input video files (can specify multiple times)"
    ),
    output: str = typer.Option(..., "--output", "-o", help="Output video file"),
    no_copy: bool = typer.Option(False, "--no-copy", help="Force re-encode instead of codec copy"),
    no_validate: bool = typer.Option(
        False, "--no-validate", help="Skip codec compatibility validation"
    ),
    profile: Optional[str] = typer.Option(
        None, "--profile", help="Encoding profile to use (if re-encoding)"
    ),
    async_mode: bool = typer.Option(
        False, "--async", help="Submit job to queue for background processing"
    ),
):
    """
    Concatenate multiple videos into one.

    Example:
        video-tool concat -i part1.mp4 -i part2.mp4 -i part3.mp4 -o final.mp4
    """
    console.print(f"\n[bold cyan]🎬 Concatenating Videos[/bold cyan]")
    console.print(f"Input files ({len(inputs)}):")
    for i, f in enumerate(inputs, 1):
        console.print(f"  {i}. {f}")
    console.print(f"Output: {output}")

    # Validate inputs
    for input_file in inputs:
        if not os.path.exists(input_file):
            console.print(f"[red]❌ Error: Input file not found: {input_file}[/red]")
            raise typer.Exit(code=1)

    if state.dry_run:
        console.print("\n[yellow]🔍 DRY RUN - No files will be created[/yellow]")
        console.print(f"\nWould concatenate {len(inputs)} files into: {output}")
        return

    # Handle async mode
    if async_mode:
        try:
            db = Database()
            job_id = db.create_job(
                job_type="concat",
                input_files=list(inputs),
                config={
                    "output_path": output,
                    "copy_codec": not no_copy,
                    "validate_compatibility": not no_validate,
                    "profile_name": profile,
                },
            )

            console.print(f"\n[green]✅ Job submitted successfully![/green]")
            console.print(f"Job ID: [cyan]{job_id}[/cyan]")
            console.print(f"\nTo monitor progress:")
            console.print(f"  video-tool jobs show {job_id}")
            console.print(f"  video-tool jobs logs {job_id}")
            console.print(
                f"\n[yellow]Note: Make sure workers are running with 'video-tool worker start'[/yellow]\n"
            )

        except Exception as e:
            console.print(f"\n[red]❌ Error submitting job: {e}[/red]")
            if state.verbose:
                import traceback

                console.print(traceback.format_exc())
            raise typer.Exit(code=1)
        return

    # Execute concat synchronously
    try:
        with console.status("[bold green]Concatenating videos..."):
            video_ops.concat_videos(
                input_files=inputs,
                output_path=output,
                copy_codec=not no_copy,
                validate_compatibility=not no_validate,
                profile_name=profile,
            )

        console.print(f"\n[green]✅ Success! Created: {output}[/green]")

    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]")
        if state.verbose:
            import traceback

            console.print(traceback.format_exc())
        raise typer.Exit(code=1)


@app.command()
def info(
    input: str = typer.Option(..., "--input", "-i", help="Input video file"),
):
    """
    Display video file information.

    Example:
        video-tool info -i movie.mp4
    """
    # Validate input
    if not os.path.exists(input):
        console.print(f"[red]❌ Error: Input file not found: {input}[/red]")
        raise typer.Exit(code=1)

    # Get video info
    try:
        info_dict = file_utils.get_video_info(input)

        # Create table
        table = Table(title=f"Video Information: {Path(input).name}", show_header=False)
        table.add_column("Property", style="cyan", no_wrap=True)
        table.add_column("Value", style="green")

        # Add rows
        table.add_row("File", input)
        table.add_row("Format", info_dict.get("format", "N/A"))

        # Duration
        duration = info_dict.get("duration", 0)
        hours = int(duration // 3600)
        minutes = int((duration % 3600) // 60)
        seconds = int(duration % 60)
        duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        table.add_row("Duration", f"{duration_str} ({duration:.1f}s)")

        # Video
        width = info_dict.get("width") or 0
        height = info_dict.get("height") or 0
        table.add_row("Resolution", f"{width}x{height}")
        table.add_row("Video Codec", str(info_dict.get("codec", "N/A")))
        table.add_row("Video Bitrate", str(info_dict.get("bitrate", "N/A")))
        fps_val = info_dict.get("fps") or 0
        table.add_row("FPS", f"{float(fps_val):.2f}" if fps_val else "N/A")

        # Audio
        table.add_row("Audio Codec", info_dict.get("audio_codec", "N/A"))

        # File size
        file_size = os.path.getsize(input)
        size_mb = file_size / (1024 * 1024)
        table.add_row("File Size", f"{size_mb:.2f} MB")

        console.print()
        console.print(table)
        console.print()

    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]")
        if state.verbose:
            import traceback

            console.print(traceback.format_exc())
        raise typer.Exit(code=1)


@audio_app.command("extract")
def audio_extract(
    input: str = typer.Option(..., "--input", "-i", help="Input video file"),
    output: str = typer.Option(..., "--output", "-o", help="Output audio file"),
    codec: str = typer.Option(
        "copy", "--codec", "-c", help="Audio codec (copy, aac, mp3, opus, flac)"
    ),
    bitrate: Optional[str] = typer.Option(
        None, "--bitrate", "-b", help="Audio bitrate (e.g., 192k, 128k)"
    ),
):
    """
    Extract audio from video.

    Example:
        video-tool audio extract -i movie.mp4 -o audio.m4a --codec copy
        video-tool audio extract -i movie.mp4 -o audio.mp3 --codec mp3 --bitrate 192k
    """
    console.print(f"\n[bold cyan]🎵 Extracting Audio[/bold cyan]")
    console.print(f"Input: {input}")
    console.print(f"Output: {output}")
    console.print(f"Codec: {codec}")
    if bitrate:
        console.print(f"Bitrate: {bitrate}")

    # Validate input
    if not os.path.exists(input):
        console.print(f"[red]❌ Error: Input file not found: {input}[/red]")
        raise typer.Exit(code=1)

    if state.dry_run:
        console.print("\n[yellow]🔍 DRY RUN - No files will be created[/yellow]")
        return

    # Execute extract
    try:
        with console.status("[bold green]Extracting audio..."):
            audio_ops.extract_audio(
                input_path=input,
                output_path=output,
                codec=codec,
                bitrate=bitrate,
            )

        console.print(f"\n[green]✅ Success! Created: {output}[/green]")

    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]")
        if state.verbose:
            import traceback

            console.print(traceback.format_exc())
        raise typer.Exit(code=1)


@audio_app.command("replace")
def audio_replace(
    video: str = typer.Option(..., "--video", "-v", help="Input video file"),
    audio: str = typer.Option(..., "--audio", "-a", help="Input audio file"),
    output: str = typer.Option(..., "--output", "-o", help="Output video file"),
):
    """
    Replace audio track in video.

    Example:
        video-tool audio replace -v video.mp4 -a new_audio.m4a -o output.mp4
    """
    console.print(f"\n[bold cyan]🎵 Replacing Audio[/bold cyan]")
    console.print(f"Video: {video}")
    console.print(f"Audio: {audio}")
    console.print(f"Output: {output}")

    # Validate inputs
    if not os.path.exists(video):
        console.print(f"[red]❌ Error: Video file not found: {video}[/red]")
        raise typer.Exit(code=1)

    if not os.path.exists(audio):
        console.print(f"[red]❌ Error: Audio file not found: {audio}[/red]")
        raise typer.Exit(code=1)

    if state.dry_run:
        console.print("\n[yellow]🔍 DRY RUN - No files will be created[/yellow]")
        return

    # Execute replace
    try:
        with console.status("[bold green]Replacing audio track..."):
            audio_ops.replace_audio(
                video_path=video,
                audio_path=audio,
                output_path=output,
            )

        console.print(f"\n[green]✅ Success! Created: {output}[/green]")

    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]")
        if state.verbose:
            import traceback

            console.print(traceback.format_exc())
        raise typer.Exit(code=1)


@profiles_app.command("list")
def profiles_list():
    """
    List all available encoding profiles.

    Example:
        video-tool profiles list
    """
    try:
        profile_names = profiles.list_profiles()
        default = profiles.get_default_profile()

        console.print(f"\n[bold cyan]📋 Available Profiles ({len(profile_names)})[/bold cyan]\n")

        # Create table
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Profile", style="cyan", no_wrap=True)
        table.add_column("Description", style="white")
        table.add_column("Resolution", style="green")
        table.add_column("Video", style="yellow")
        table.add_column("HW Accel", style="blue")

        for name in profile_names:
            profile = profiles.get_profile(name)
            is_default = " [bold green](default)[/bold green]" if name == default.name else ""
            hw_accel = "✓" if profile.uses_hardware_acceleration() else "✗"

            table.add_row(
                f"{name}{is_default}",
                profile.description,
                profile.resolution,
                profile.video_codec,
                hw_accel,
            )

        console.print(table)
        console.print()

    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]")
        if state.verbose:
            import traceback

            console.print(traceback.format_exc())
        raise typer.Exit(code=1)


@profiles_app.command("show")
def profiles_show(
    name: str = typer.Argument(..., help="Profile name"),
):
    """
    Show detailed information about a profile.

    Example:
        video-tool profiles show clip_720p
    """
    try:
        profile = profiles.get_profile(name)
        summary = profiles.get_profile_summary(profile)

        console.print()
        console.print(summary)
        console.print()

    except profiles.ProfileNotFoundError as e:
        console.print(f"\n[red]❌ {e}[/red]")
        console.print("\nUse 'video-tool profiles list' to see available profiles.")
        raise typer.Exit(code=1)

    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]")
        if state.verbose:
            import traceback

            console.print(traceback.format_exc())
        raise typer.Exit(code=1)


@jobs_app.command("list")
def jobs_list(
    status: Optional[str] = typer.Option(
        None, "--status", "-s", help="Filter by status (pending, running, completed, failed)"
    ),
    limit: int = typer.Option(20, "--limit", "-n", help="Maximum number of jobs to show"),
):
    """
    List jobs with optional status filter.

    Example:
        video-tool jobs list
        video-tool jobs list --status failed
        video-tool jobs list --limit 50
    """
    try:
        db = Database()

        # Parse status if provided
        status_filter = None
        if status:
            try:
                status_filter = JobStatus(status.lower())
            except ValueError:
                console.print(f"[red]❌ Invalid status: {status}[/red]")
                console.print("Valid statuses: pending, running, completed, failed")
                raise typer.Exit(code=1)

        jobs = db.list_jobs(status=status_filter, limit=limit)

        if not jobs:
            console.print("\n[yellow]No jobs found.[/yellow]\n")
            return

        # Create table
        title = f"Jobs ({len(jobs)}"
        if status_filter:
            title += f", status: {status}"
        title += ")"

        console.print(f"\n[bold cyan]📋 {title}[/bold cyan]\n")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Type", style="blue")
        table.add_column("Status", style="white")
        table.add_column("Progress", style="green")
        table.add_column("Created", style="yellow")
        table.add_column("Duration", style="magenta")

        for job in jobs:
            # Color code status
            if job.status == JobStatus.COMPLETED:
                status_text = "[green]✓ completed[/green]"
            elif job.status == JobStatus.FAILED:
                status_text = "[red]✗ failed[/red]"
            elif job.status == JobStatus.RUNNING:
                status_text = "[yellow]▶ running[/yellow]"
            else:
                status_text = "[dim]○ pending[/dim]"

            # Calculate duration
            duration_text = "-"
            if job.completed_at and job.started_at:
                duration_sec = (job.completed_at - job.started_at).total_seconds()
                if duration_sec < 60:
                    duration_text = f"{duration_sec:.0f}s"
                elif duration_sec < 3600:
                    duration_text = f"{duration_sec / 60:.1f}m"
                else:
                    duration_text = f"{duration_sec / 3600:.1f}h"
            elif job.started_at:
                duration_text = "running..."

            table.add_row(
                str(job.id),
                job.job_type,
                status_text,
                f"{job.progress:.0f}%",
                job.created_at.strftime("%Y-%m-%d %H:%M"),
                duration_text,
            )

        console.print(table)
        console.print()

    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]")
        if state.verbose:
            import traceback

            console.print(traceback.format_exc())
        raise typer.Exit(code=1)


@jobs_app.command("show")
def jobs_show(
    job_id: int = typer.Argument(..., help="Job ID"),
):
    """
    Show detailed information about a specific job.

    Example:
        video-tool jobs show 1
    """
    try:
        db = Database()
        job = db.get_job(job_id)

        if not job:
            console.print(f"\n[red]❌ Job {job_id} not found.[/red]\n")
            raise typer.Exit(code=1)

        console.print(f"\n[bold cyan]📋 Job #{job.id}[/bold cyan]\n")

        # Create details table
        table = Table(show_header=False, box=None)
        table.add_column("Property", style="bold cyan", no_wrap=True)
        table.add_column("Value", style="white")

        # Status with color
        if job.status == JobStatus.COMPLETED:
            status_text = "[green]✓ completed[/green]"
        elif job.status == JobStatus.FAILED:
            status_text = "[red]✗ failed[/red]"
        elif job.status == JobStatus.RUNNING:
            status_text = "[yellow]▶ running[/yellow]"
        else:
            status_text = "[dim]○ pending[/dim]"

        table.add_row("Type", job.job_type)
        table.add_row("Status", status_text)
        table.add_row("Progress", f"{job.progress:.1f}%")
        table.add_row("Created", job.created_at.strftime("%Y-%m-%d %H:%M:%S"))

        if job.started_at:
            table.add_row("Started", job.started_at.strftime("%Y-%m-%d %H:%M:%S"))

        if job.completed_at:
            table.add_row("Completed", job.completed_at.strftime("%Y-%m-%d %H:%M:%S"))
            duration_sec = (job.completed_at - job.started_at).total_seconds()
            table.add_row("Duration", f"{duration_sec:.1f}s")

        if job.retry_count > 0:
            table.add_row("Retries", str(job.retry_count))

        table.add_row("Input Files", f"{len(job.input_files)} file(s)")
        for i, f in enumerate(job.input_files, 1):
            table.add_row("", f"  {i}. {f}")

        if job.output_files:
            table.add_row("Output Files", f"{len(job.output_files)} file(s)")
            for i, f in enumerate(job.output_files, 1):
                table.add_row("", f"  {i}. {f}")

        if job.config:
            import json

            config_str = json.dumps(job.config, indent=2)
            table.add_row("Config", config_str)

        if job.error_message:
            table.add_row("Error", f"[red]{job.error_message}[/red]")

        console.print(table)
        console.print()

    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]")
        if state.verbose:
            import traceback

            console.print(traceback.format_exc())
        raise typer.Exit(code=1)


@jobs_app.command("logs")
def jobs_logs(
    job_id: int = typer.Argument(..., help="Job ID"),
):
    """
    Show log entries for a specific job.

    Example:
        video-tool jobs logs 1
    """
    try:
        db = Database()
        job = db.get_job(job_id)

        if not job:
            console.print(f"\n[red]❌ Job {job_id} not found.[/red]\n")
            raise typer.Exit(code=1)

        logs = db.get_job_logs(job_id)

        if not logs:
            console.print(f"\n[yellow]No logs found for job {job_id}.[/yellow]\n")
            return

        console.print(f"\n[bold cyan]📝 Logs for Job #{job_id} ({len(logs)} entries)[/bold cyan]\n")

        # Create logs table
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Time", style="yellow", no_wrap=True)
        table.add_column("Level", style="blue", no_wrap=True)
        table.add_column("Message", style="white")

        for log in logs:
            # Color code log level
            level = log["level"]
            if level == "ERROR":
                level_text = "[red]ERROR[/red]"
            elif level == "WARNING":
                level_text = "[yellow]WARN[/yellow]"
            else:
                level_text = "[green]INFO[/green]"

            # Parse timestamp
            from datetime import datetime

            try:
                ts = datetime.fromisoformat(log["timestamp"])
                time_str = ts.strftime("%H:%M:%S")
            except:
                time_str = log["timestamp"]

            table.add_row(
                time_str,
                level_text,
                log["message"],
            )

        console.print(table)
        console.print()

    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]")
        if state.verbose:
            import traceback

            console.print(traceback.format_exc())
        raise typer.Exit(code=1)


@jobs_app.command("retry")
def jobs_retry(
    job_id: int = typer.Argument(..., help="Job ID"),
):
    """
    Retry a failed job.

    Example:
        video-tool jobs retry 1
    """
    try:
        db = Database()
        job = db.get_job(job_id)

        if not job:
            console.print(f"\n[red]❌ Job {job_id} not found.[/red]\n")
            raise typer.Exit(code=1)

        if job.status != JobStatus.FAILED:
            console.print(
                f"\n[yellow]⚠ Job {job_id} is not in failed status (current: {job.status.value}).[/yellow]\n"
            )
            console.print("Only failed jobs can be retried.")
            raise typer.Exit(code=1)

        console.print(f"\n[bold cyan]🔄 Retrying Job #{job_id}[/bold cyan]")
        console.print(f"Type: {job.job_type}")
        console.print(f"Previous error: {job.error_message}")
        console.print()

        # Reset job status
        db.increment_retry_count(job_id)
        db.update_job_status(job_id, JobStatus.PENDING, progress=0.0)

        console.print(f"[green]✅ Job {job_id} reset to pending status.[/green]")
        console.print(
            "\n[yellow]Note: Job will need to be executed manually with the original command.[/yellow]\n"
        )

    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]")
        if state.verbose:
            import traceback

            console.print(traceback.format_exc())
        raise typer.Exit(code=1)


@jobs_app.command("clean")
def jobs_clean(
    older_than: int = typer.Option(
        30, "--older-than", "-d", help="Remove completed jobs older than N days"
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompt"),
):
    """
    Clean up old completed jobs from the database.

    Example:
        video-tool jobs clean
        video-tool jobs clean --older-than 90
        video-tool jobs clean --force
    """
    try:
        db = Database()

        if not force:
            confirm = typer.confirm(
                f"\nRemove completed jobs older than {older_than} days?", abort=True
            )

        console.print(f"\n[bold cyan]🧹 Cleaning up old jobs...[/bold cyan]\n")

        deleted_count = db.cleanup_old_jobs(days=older_than)

        if deleted_count > 0:
            console.print(f"[green]✅ Removed {deleted_count} old job(s).[/green]\n")
        else:
            console.print(f"[yellow]No jobs found older than {older_than} days.[/yellow]\n")

    except typer.Abort:
        console.print("\n[yellow]Cancelled.[/yellow]\n")

    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]")
        if state.verbose:
            import traceback

            console.print(traceback.format_exc())
        raise typer.Exit(code=1)


# ============================================================================
# Worker Commands
# ============================================================================


@worker_app.command("start")
def worker_start(
    workers: int = typer.Option(2, "--workers", "-w", help="Number of worker processes"),
    check_interval: int = typer.Option(
        5, "--check-interval", help="Queue check interval in seconds"
    ),
):
    """
    Start worker pool for background job processing.

    Workers will run in foreground and process pending jobs from the queue.
    Press Ctrl+C to stop workers gracefully.

    Example:
        video-tool worker start
        video-tool worker start --workers 4
    """
    try:
        from core.queue import WorkerPool

        # Check if already running
        if os.path.exists(".worker_pool.pid"):
            try:
                with open(".worker_pool.pid", "r") as f:
                    pid = int(f.read().strip())
                # Check if process exists
                os.kill(pid, 0)
                console.print(f"\n[yellow]⚠ Worker pool already running (PID: {pid})[/yellow]")
                console.print("Use 'video-tool worker stop' to stop it first.\n")
                raise typer.Exit(code=1)
            except (OSError, ValueError):
                # Process doesn't exist, remove stale PID file
                os.remove(".worker_pool.pid")

        console.print(f"\n[bold cyan]🚀 Starting Worker Pool[/bold cyan]")
        console.print(f"Workers: {workers}")
        console.print(f"Check interval: {check_interval}s")
        console.print("\nPress Ctrl+C to stop workers gracefully.\n")

        pool = WorkerPool(num_workers=workers, check_interval=check_interval)
        pool.start()

        # Keep running until interrupted
        import time

        try:
            while pool.is_running():
                time.sleep(1)
        except KeyboardInterrupt:
            console.print("\n\n[yellow]⏹ Stopping workers...[/yellow]")
            pool.stop()
            console.print("[green]✅ Workers stopped successfully.[/green]\n")

    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]")
        if state.verbose:
            import traceback

            console.print(traceback.format_exc())
        raise typer.Exit(code=1)


@worker_app.command("stop")
def worker_stop():
    """
    Stop running worker pool.

    Sends SIGTERM to worker pool process for graceful shutdown.

    Example:
        video-tool worker stop
    """
    try:
        if not os.path.exists(".worker_pool.pid"):
            console.print("\n[yellow]No worker pool running.[/yellow]\n")
            return

        with open(".worker_pool.pid", "r") as f:
            pid = int(f.read().strip())

        console.print(f"\n[bold cyan]⏹ Stopping Worker Pool[/bold cyan]")
        console.print(f"PID: {pid}\n")

        # Send SIGTERM for graceful shutdown
        import signal

        os.kill(pid, signal.SIGTERM)

        # Wait for shutdown
        import time

        for i in range(30):
            try:
                os.kill(pid, 0)
                time.sleep(1)
            except OSError:
                break

        # Check if still running
        try:
            os.kill(pid, 0)
            console.print("[yellow]⚠ Worker pool didn't stop, sending SIGKILL...[/yellow]")
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass

        console.print("[green]✅ Worker pool stopped.[/green]\n")

    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]")
        if state.verbose:
            import traceback

            console.print(traceback.format_exc())
        raise typer.Exit(code=1)


@worker_app.command("status")
def worker_status():
    """
    Show worker pool status.

    Displays worker pool and individual worker information.

    Example:
        video-tool worker status
    """
    try:
        if not os.path.exists(".worker_pool.pid"):
            console.print("\n[yellow]No worker pool running.[/yellow]\n")
            return

        with open(".worker_pool.pid", "r") as f:
            pid = int(f.read().strip())

        # Check if process exists
        try:
            os.kill(pid, 0)
        except OSError:
            console.print("\n[yellow]Worker pool PID file exists but process not running.[/yellow]")
            console.print("Removing stale PID file...\n")
            os.remove(".worker_pool.pid")
            return

        console.print(f"\n[bold cyan]📊 Worker Pool Status[/bold cyan]")
        console.print(f"PID: {pid}")
        console.print(f"Status: [green]Running[/green]\n")

        # Get job statistics
        from core.database import Database, JobStatus

        db = Database()

        pending_jobs = len(db.list_jobs(status=JobStatus.PENDING, limit=1000))
        running_jobs = len(db.list_jobs(status=JobStatus.RUNNING, limit=1000))

        console.print(f"[bold]Queue Statistics:[/bold]")
        console.print(f"  Pending jobs: {pending_jobs}")
        console.print(f"  Running jobs: {running_jobs}")
        console.print()

    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]")
        if state.verbose:
            import traceback

            console.print(traceback.format_exc())
        raise typer.Exit(code=1)


@worker_app.command("restart")
def worker_restart(
    workers: int = typer.Option(2, "--workers", "-w", help="Number of worker processes"),
):
    """
    Restart worker pool.

    Stops running workers and starts new ones.

    Example:
        video-tool worker restart
        video-tool worker restart --workers 4
    """
    console.print("\n[bold cyan]🔄 Restarting Worker Pool[/bold cyan]\n")

    # Stop if running
    if os.path.exists(".worker_pool.pid"):
        worker_stop()
        import time

        time.sleep(2)

    # Start new pool
    worker_start(workers=workers)


@app.command()
def version():
    """Show version information."""
    console.print("\n[bold cyan]Video Tool[/bold cyan] version [green]0.1.0[/green]")

    # Check FFmpeg version
    try:
        ffmpeg_version = ffmpeg_runner.get_ffmpeg_version()
        console.print(f"FFmpeg: [green]{ffmpeg_version}[/green]")
    except:
        console.print("FFmpeg: [red]Not found[/red]")

    console.print()


if __name__ == "__main__":
    app()
