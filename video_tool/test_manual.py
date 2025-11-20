"""Manual test script to verify FFmpeg runner functionality."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.ffmpeg_runner import (
    check_ffmpeg_installed,
    check_ffprobe_installed,
    get_ffmpeg_version,
    parse_ffmpeg_progress,
)

def main():
    print("=" * 60)
    print("FFmpeg Runner Module - Manual Test")
    print("=" * 60)
    
    # Test 1: Check FFmpeg installation
    print("\n[Test 1] Checking FFmpeg installation...")
    if check_ffmpeg_installed():
        print("✓ FFmpeg is installed")
    else:
        print("✗ FFmpeg is NOT installed")
        return
    
    # Test 2: Check ffprobe installation
    print("\n[Test 2] Checking ffprobe installation...")
    if check_ffprobe_installed():
        print("✓ ffprobe is installed")
    else:
        print("✗ ffprobe is NOT installed")
    
    # Test 3: Get FFmpeg version
    print("\n[Test 3] Getting FFmpeg version...")
    try:
        version = get_ffmpeg_version()
        print(f"✓ FFmpeg version: {version}")
    except Exception as e:
        print(f"✗ Error getting version: {e}")
    
    # Test 4: Parse progress line
    print("\n[Test 4] Testing progress parsing...")
    test_lines = [
        "frame=  100 fps=30.0 size=    1024kB time=00:00:04.00 bitrate=2000.5kbits/s speed=1.0x",
        "frame=  500 time=00:01:30.50 bitrate=1500kbits/s",
        "frame=1000 time=01:15:30.00",
    ]
    
    for i, line in enumerate(test_lines, 1):
        progress = parse_ffmpeg_progress(line)
        if progress:
            print(f"✓ Test line {i} parsed successfully:")
            print(f"  {progress}")
        else:
            print(f"✗ Test line {i} failed to parse")
    
    print("\n" + "=" * 60)
    print("All manual tests completed!")
    print("=" * 60)

if __name__ == "__main__":
    main()
