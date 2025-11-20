#!/usr/bin/env python3
"""
Generate sample video files for integration testing.

This script uses FFmpeg to create small test videos with various formats
for testing video operations without requiring large real video files.
"""

import os
import subprocess
import sys
from pathlib import Path


def check_ffmpeg():
    """Check if FFmpeg is installed."""
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def generate_sample_720p(output_path: Path):
    """
    Generate a 10-second 720p H.264 video with AAC audio.
    
    Size: ~500KB
    """
    print(f"Generating 720p sample: {output_path}")
    
    cmd = [
        "ffmpeg",
        "-f", "lavfi",
        "-i", "testsrc=duration=10:size=1280x720:rate=30",  # Test pattern video
        "-f", "lavfi",
        "-i", "sine=frequency=1000:duration=10",  # Sine wave audio
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "28",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        "-y",  # Overwrite if exists
        str(output_path),
    ]
    
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"✅ Created: {output_path.name} ({output_path.stat().st_size / 1024:.1f} KB)")


def generate_sample_1080p(output_path: Path):
    """
    Generate a 10-second 1080p H.265 video with AAC audio.
    
    Size: ~800KB
    """
    print(f"Generating 1080p sample: {output_path}")
    
    cmd = [
        "ffmpeg",
        "-f", "lavfi",
        "-i", "testsrc=duration=10:size=1920x1080:rate=30",
        "-f", "lavfi",
        "-i", "sine=frequency=440:duration=10",
        "-c:v", "libx265",
        "-preset", "ultrafast",
        "-crf", "28",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        "-y",
        str(output_path),
    ]
    
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"✅ Created: {output_path.name} ({output_path.stat().st_size / 1024:.1f} KB)")
    except subprocess.CalledProcessError:
        # Fallback to H.264 if H.265 not available
        print("⚠️  H.265 not available, using H.264 instead")
        cmd[9] = "libx264"  # Replace libx265 with libx264
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"✅ Created: {output_path.name} ({output_path.stat().st_size / 1024:.1f} KB)")


def generate_sample_480p(output_path: Path):
    """
    Generate a 10-second 480p H.264 video with AAC audio.
    
    Size: ~300KB
    """
    print(f"Generating 480p sample: {output_path}")
    
    cmd = [
        "ffmpeg",
        "-f", "lavfi",
        "-i", "testsrc=duration=10:size=854x480:rate=30",
        "-f", "lavfi",
        "-i", "sine=frequency=880:duration=10",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "28",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "96k",
        "-y",
        str(output_path),
    ]
    
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"✅ Created: {output_path.name} ({output_path.stat().st_size / 1024:.1f} KB)")


def generate_sample_audio(output_path: Path):
    """
    Generate a 5-second AAC audio file.
    
    Size: ~40KB
    """
    print(f"Generating audio sample: {output_path}")
    
    cmd = [
        "ffmpeg",
        "-f", "lavfi",
        "-i", "sine=frequency=440:duration=5",
        "-c:a", "aac",
        "-b:a", "128k",
        "-y",
        str(output_path),
    ]
    
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"✅ Created: {output_path.name} ({output_path.stat().st_size / 1024:.1f} KB)")


def generate_short_video(output_path: Path):
    """
    Generate a 3-second video for quick tests.
    
    Size: ~150KB
    """
    print(f"Generating short video sample: {output_path}")
    
    cmd = [
        "ffmpeg",
        "-f", "lavfi",
        "-i", "testsrc=duration=3:size=640x480:rate=30",
        "-f", "lavfi",
        "-i", "sine=frequency=1000:duration=3",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "28",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        "-y",
        str(output_path),
    ]
    
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"✅ Created: {output_path.name} ({output_path.stat().st_size / 1024:.1f} KB)")


def generate_color_video(output_path: Path, color: str = "blue"):
    """
    Generate a 5-second solid color video for concat testing.
    
    Size: ~100KB
    """
    print(f"Generating {color} video: {output_path}")
    
    cmd = [
        "ffmpeg",
        "-f", "lavfi",
        "-i", f"color=c={color}:size=1280x720:duration=5:rate=30",
        "-f", "lavfi",
        "-i", "anullsrc=channel_layout=stereo:sample_rate=44100:duration=5",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "28",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        "-y",
        str(output_path),
    ]
    
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"✅ Created: {output_path.name} ({output_path.stat().st_size / 1024:.1f} KB)")


def main():
    """Generate all sample files."""
    # Get the fixtures directory
    fixtures_dir = Path(__file__).parent
    
    # Check FFmpeg
    if not check_ffmpeg():
        print("❌ Error: FFmpeg is not installed or not in PATH")
        print("\nPlease install FFmpeg:")
        print("  macOS: brew install ffmpeg")
        print("  Linux: sudo apt install ffmpeg")
        sys.exit(1)
    
    print("🎬 Generating sample video files for testing...\n")
    
    # Generate samples
    try:
        generate_sample_720p(fixtures_dir / "sample_720p.mp4")
        generate_sample_1080p(fixtures_dir / "sample_1080p.mp4")
        generate_sample_480p(fixtures_dir / "sample_480p.mp4")
        generate_sample_audio(fixtures_dir / "sample_audio.m4a")
        generate_short_video(fixtures_dir / "sample_short.mp4")
        
        # Generate color videos for concat testing
        generate_color_video(fixtures_dir / "sample_red.mp4", "red")
        generate_color_video(fixtures_dir / "sample_green.mp4", "green")
        generate_color_video(fixtures_dir / "sample_blue.mp4", "blue")
        
        print("\n✅ All sample files generated successfully!")
        print(f"\nTotal files: 8")
        
        # Calculate total size
        total_size = sum(
            f.stat().st_size
            for f in fixtures_dir.glob("sample_*")
            if f.is_file()
        )
        print(f"Total size: {total_size / 1024:.1f} KB ({total_size / 1024 / 1024:.2f} MB)")
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error generating samples: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
