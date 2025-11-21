# 📚 VIDEO TOOL - COMMAND REFERENCE

**Version:** 0.1.0  
**Date:** 2025-11-21  
**FFmpeg:** 8.0

---

## 🚀 SETUP & ACTIVATION

### Activate Environment
```bash
cd /Users/Shared/jerry/tools/flim_tool/video_tool
source .venv/bin/activate
```

### Check Installation
```bash
video-tool --help
video-tool version
ffmpeg -version
```

---

## 📋 GLOBAL OPTIONS

Các options này có thể dùng với mọi command:

### Verbose Mode
```bash
video-tool --verbose <command>
video-tool -v <command>
```
Enables DEBUG logging với full FFmpeg output

### Dry-run Mode
```bash
video-tool --dry-run <command>
```
Preview operations without execution

### Custom Log File
```bash
video-tool --log-file /path/to/custom.log <command>
```
Specify custom log file location

### Combined Options
```bash
video-tool --verbose --dry-run --log-file debug.log cut -i movie.mp4 -o ./output -d 11
```

---

## 🎬 VIDEO OPERATIONS

### 1. VIDEO INFO

#### Basic Info
```bash
video-tool info -i movie.mp4
video-tool info --input /path/to/video.mp4
```

#### Verbose Info
```bash
video-tool --verbose info -i movie.mp4
```

#### Example với Video thực tế
```bash
# Video 1 (39 phút, 720p)
video-tool info -i ../../source_video/sekiraras-escape-a-road-trip-with-a-shady-girl-720p.mp4

# Video 2 (2h 12min, 480p)
video-tool info -i ../../source_video/swingers-online-streaming-video-at-private-vod-store-with-free-previews.mp4
```

**Output Example:**
```
┌───────────────┬────────────────────────────────────┐
│ File          │ movie.mp4                          │
│ Format        │ mov,mp4,m4a,3gp,3g2,mj2            │
│ Duration      │ 00:39:26 (2366.5s)                 │
│ Resolution    │ 1280x720                           │
│ Video Codec   │ h264                               │
│ Video Bitrate │ 3106005                            │
│ FPS           │ 30.00                              │
│ Audio Codec   │ aac                                │
│ File Size     │ 876.25 MB                          │
└───────────────┴────────────────────────────────────┘
```

---

### 2. CUT VIDEO

#### Cut by Duration (Minutes)
```bash
# Cut into 11-minute segments
video-tool cut -i movie.mp4 -o ./output -d 11

# Cut with custom prefix
video-tool cut -i movie.mp4 -o ./clips -d 15 --prefix segment

# Cut into 5-minute segments
video-tool cut --input video.mp4 --output-dir ./parts --duration 5 --prefix part
```

#### Dry-run (Preview)
```bash
video-tool --dry-run cut -i movie.mp4 -o ./output -d 11
```

#### With Re-encoding ✅ PRODUCTION READY
```bash
# Re-encode with hardware acceleration (HEVC, fastest)
video-tool cut -i movie.mp4 -o ./output -d 11 --no-copy --profile clip_720p

# Re-encode with software encoding (H.264, maximum compatibility)
video-tool cut -i movie.mp4 -o ./output -d 11 --no-copy --profile web_720p

# Re-encode 480p for mobile (use software profiles for 480p)
video-tool cut -i movie.mp4 -o ./output -d 11 --no-copy --profile mobile_480p
```

**Performance Comparison:**
```bash
# Codec copy (baseline): ~2-5 seconds
video-tool cut -i movie.mp4 -o ./output -d 11

# Hardware re-encode (clip_720p): ~8 min for 39-min video (4.3x realtime)
video-tool cut -i movie.mp4 -o ./output -d 11 --no-copy --profile clip_720p
# Result: 23% size reduction (876 MB → 672 MB), HEVC codec

# Software re-encode (web_720p): slower but more compatible
video-tool cut -i movie.mp4 -o ./output -d 11 --no-copy --profile web_720p
# Result: H.264 codec, works everywhere
```

**⚠️ Important Notes:**
- Hardware profiles (hevc_videotoolbox) work best with 720p+ resolutions
- For 480p or lower, use software profiles (web_480p, mobile_480p)
- Re-encoding takes longer but reduces file size 20-30%

#### Example với Video thực tế
```bash
# Cut video 39 phút thành 11-minute segments (sẽ có 4 segments)
video-tool cut \
  -i ../../source_video/sekiraras-escape-a-road-trip-with-a-shady-girl-720p.mp4 \
  -o ./sekiraras_clips \
  -d 11 \
  --prefix sekiraras

# Cut video 2h12min thành 15-minute segments (sẽ có 9 segments)
video-tool cut \
  -i ../../source_video/swingers-online-streaming-video-at-private-vod-store-with-free-previews.mp4 \
  -o ./swingers_clips \
  -d 15 \
  --prefix swingers
```

**Output Files:**
```
sekiraras_clips/
├── sekiraras_001.mp4  (11 min)
├── sekiraras_002.mp4  (11 min)
├── sekiraras_003.mp4  (11 min)
└── sekiraras_004.mp4  (~6.5 min)
```

---

### 3. CONCATENATE VIDEOS

#### Basic Concat
```bash
# Concat 2 videos
video-tool concat -i part1.mp4 -i part2.mp4 -o final.mp4

# Concat multiple videos
video-tool concat \
  -i clip1.mp4 \
  -i clip2.mp4 \
  -i clip3.mp4 \
  -o combined.mp4
```

#### Concat with Wildcard (Shell Expansion)
```bash
video-tool concat -i clips/*.mp4 -o final.mp4
video-tool concat -i clips/part_*.mp4 -o merged.mp4
```

#### Skip Codec Validation
```bash
video-tool concat \
  -i video1.mp4 \
  -i video2.mkv \
  -o output.mp4 \
  --no-validate
```

#### Force Re-encoding ✅ PRODUCTION READY
```bash
# Re-encode with profile (H.264 for web compatibility)
video-tool concat \
  -i part1.mp4 \
  -i part2.mp4 \
  -o final.mp4 \
  --no-copy \
  --profile web_720p

# Re-encode with hardware acceleration (HEVC, smaller files)
video-tool concat \
  -i segment1.mp4 \
  -i segment2.mp4 \
  -o combined.mp4 \
  --no-copy \
  --profile clip_720p

# Re-encode for mobile delivery
video-tool concat \
  -i clip*.mp4 \
  -o mobile_version.mp4 \
  --no-copy \
  --profile mobile_720p
```

**Example: Concat re-encoded segments**
```bash
# After cutting with clip_720p profile, concat them with web_720p
video-tool concat \
  -i test_reencode/test_720p_001.mp4 \
  -i test_reencode/test_720p_002.mp4 \
  -o final_h264.mp4 \
  --no-copy \
  --profile web_720p

# Result: 22:00 duration, 1280x720, H.264, ~2M bitrate
```

#### Example: Nối lại clips đã cắt
```bash
# Sau khi cut, nối lại tất cả clips
video-tool concat \
  -i ./sekiraras_clips/sekiraras_001.mp4 \
  -i ./sekiraras_clips/sekiraras_002.mp4 \
  -i ./sekiraras_clips/sekiraras_003.mp4 \
  -i ./sekiraras_clips/sekiraras_004.mp4 \
  -o sekiraras_full.mp4
```

---

## 🔊 AUDIO OPERATIONS

### 1. EXTRACT AUDIO

#### Codec Copy (Fastest - No Re-encoding)
```bash
# Extract AAC audio
video-tool audio extract -i movie.mp4 -o audio.m4a --codec copy

# Short syntax
video-tool audio extract -i video.mp4 -o audio.aac -c copy
```

#### Convert to MP3
```bash
# High quality (320k)
video-tool audio extract \
  -i movie.mp4 \
  -o audio.mp3 \
  --codec mp3 \
  --bitrate 320k

# Standard quality (192k)
video-tool audio extract -i video.mp4 -o audio.mp3 -c mp3 -b 192k

# Lower quality (128k)
video-tool audio extract -i video.mp4 -o audio.mp3 -c mp3 -b 128k
```

#### Convert to OPUS (Most Efficient)
```bash
video-tool audio extract -i movie.mp4 -o audio.opus -c opus -b 128k
video-tool audio extract -i video.mp4 -o audio.opus -c opus -b 96k
```

#### Convert to FLAC (Lossless)
```bash
video-tool audio extract -i movie.mp4 -o audio.flac -c flac
```

#### Example với Video thực tế
```bash
# Extract từ video 1 (39 phút)
video-tool audio extract \
  -i ../../source_video/sekiraras-escape-a-road-trip-with-a-shady-girl-720p.mp4 \
  -o sekiraras-audio.m4a \
  --codec copy

# Extract và convert sang MP3
video-tool audio extract \
  -i ../../source_video/sekiraras-escape-a-road-trip-with-a-shady-girl-720p.mp4 \
  -o sekiraras-audio.mp3 \
  --codec mp3 \
  --bitrate 192k

# Extract từ video 2 (2h 12min) sang OPUS
video-tool audio extract \
  -i ../../source_video/swingers-online-streaming-video-at-private-vod-store-with-free-previews.mp4 \
  -o swingers-audio.opus \
  --codec opus \
  --bitrate 128k
```

---

### 2. REPLACE AUDIO

#### Basic Replace (Codec Copy)
```bash
video-tool audio replace \
  -v video.mp4 \
  -a new_audio.m4a \
  -o output.mp4
```

#### Replace with Short Syntax
```bash
video-tool audio replace -v movie.mp4 -a soundtrack.mp3 -o final.mp4
```

#### Example Workflow
```bash
# Step 1: Extract audio từ video 1
video-tool audio extract \
  -i ../../source_video/sekiraras-escape-a-road-trip-with-a-shady-girl-720p.mp4 \
  -o temp_audio.m4a \
  --codec copy

# Step 2: Thay audio của video 2 bằng audio từ video 1
video-tool audio replace \
  -v ../../source_video/swingers-online-streaming-video-at-private-vod-store-with-free-previews.mp4 \
  -a temp_audio.m4a \
  -o video_with_new_audio.mp4

# Step 3: Verify
video-tool info -i video_with_new_audio.mp4
```

---

## 📋 PROFILE MANAGEMENT

### List All Profiles
```bash
video-tool profiles list
```

**Output:**
```
📋 Available Profiles (11)

┏━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┓
┃ Profile             ┃ Description     ┃ Resolution ┃ Video Codec    ┃
┡━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━┩
│ movie_1080p         │ High-quality    │ 1920x1080  │ hevc_videotoo… │
│ movie_720p          │ Standard 720p   │ 1280x720   │ hevc_videotoo… │
│ clip_720p (default) │ Optimized 720p  │ 1280x720   │ hevc_videotoo… │
│ clip_480p           │ Lower-quality   │ 854x480    │ hevc_videotoo… │
│ web_1080p           │ Web-optimized   │ 1920x1080  │ libx264        │
│ web_720p            │ Web-optimized   │ 1280x720   │ libx264        │
│ mobile_720p         │ Mobile-optimized│ 1280x720   │ libx264        │
│ mobile_480p         │ Mobile-optimized│ 854x480    │ libx264        │
│ quality_high        │ Quality-based   │ source     │ libx265        │
│ quality_medium      │ Quality-based   │ source     │ libx265        │
│ fast                │ Fast encoding   │ source     │ libx264        │
└─────────────────────┴─────────────────┴────────────┴────────────────┘
```

### Show Profile Details
```bash
# Show specific profile
video-tool profiles show clip_720p
video-tool profiles show movie_1080p
video-tool profiles show web_720p
```

**Output Example:**
```
Profile: clip_720p

┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Property         ┃ Value                                      ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Description      │ Optimized 720p profile for 11-minute clips │
│ Video Codec      │ hevc_videotoolbox                          │
│ Video Bitrate    │ 2M                                         │
│ Resolution       │ 1280x720                                   │
│ Audio Codec      │ aac                                        │
│ Audio Bitrate    │ 128k                                       │
│ FPS              │ source                                     │
│ HW Acceleration  │ videotoolbox                               │
└──────────────────┴────────────────────────────────────────────┘
```

### Available Profiles

| Profile | Resolution | Codec | Use Case | Status |
|---------|-----------|-------|----------|--------|
| `movie_1080p` | 1920x1080 | HEVC (HW) | High-quality movies | ✅ |
| `movie_720p` | 1280x720 | HEVC (HW) | Standard movies | ✅ |
| `clip_720p` | 1280x720 | HEVC (HW) | 11-minute clips (default) | ✅ |
| `clip_480p` | 854x480 | HEVC (HW) | Smaller clips | ⚠️ HW limitation* |
| `web_1080p` | 1920x1080 | H.264 (SW) | Web streaming | ✅ |
| `web_720p` | 1280x720 | H.264 (SW) | Web streaming | ✅ |
| `mobile_720p` | 1280x720 | H.264 (SW) | Mobile devices | ✅ |
| `mobile_480p` | 854x480 | H.264 (SW) | Mobile devices | ✅ |
| `quality_high` | source | HEVC (SW) | CRF 20 (high quality) | ✅ |
| `quality_medium` | source | HEVC (SW) | CRF 24 (medium) | ✅ |
| `fast` | source | H.264 (SW) | Quick encoding | ✅ |

**Legend:**
- HW = Hardware accelerated (VideoToolbox on macOS)
- SW = Software encoding (libx264, libx265)
- ⚠️ *VideoToolbox fails on 480p resolution, use mobile_480p or web_480p instead

**Performance Guide:**
- Hardware profiles (HEVC): 4-5x realtime speed, 20-30% size reduction
- Software profiles (H.264): 2-3x realtime speed, maximum compatibility

---

## 🔧 COMPLETE WORKFLOW EXAMPLES

### Workflow 1: Process Movie into Clips

```bash
# Step 1: Check video info
video-tool info -i ../../source_video/sekiraras-escape-a-road-trip-with-a-shady-girl-720p.mp4

# Step 2: Preview cut operation
video-tool --dry-run cut \
  -i ../../source_video/sekiraras-escape-a-road-trip-with-a-shady-girl-720p.mp4 \
  -o ./sekiraras_clips \
  -d 11

# Step 3: Execute cut
video-tool cut \
  -i ../../source_video/sekiraras-escape-a-road-trip-with-a-shady-girl-720p.mp4 \
  -o ./sekiraras_clips \
  -d 11 \
  --prefix sekiraras_part

# Step 4: Verify output
ls -lh ./sekiraras_clips/
video-tool info -i ./sekiraras_clips/sekiraras_part_001.mp4
```

---

### Workflow 2: Extract and Replace Audio

```bash
# Step 1: Extract audio from original
video-tool audio extract \
  -i ../../source_video/sekiraras-escape-a-road-trip-with-a-shady-girl-720p.mp4 \
  -o original_audio.m4a \
  --codec copy

# Step 2: [Edit audio externally with Audacity, etc.]

# Step 3: Replace with edited audio
video-tool audio replace \
  -v ../../source_video/sekiraras-escape-a-road-trip-with-a-shady-girl-720p.mp4 \
  -a edited_audio.m4a \
  -o video_with_new_audio.mp4

# Step 4: Verify
video-tool info -i video_with_new_audio.mp4
```

---

### Workflow 3: Cut, Process, and Concat

```bash
# Step 1: Cut into segments
video-tool cut \
  -i ../../source_video/swingers-online-streaming-video-at-private-vod-store-with-free-previews.mp4 \
  -o ./temp_clips \
  -d 15 \
  --prefix temp

# Step 2: Extract audio from each segment
for i in ./temp_clips/temp_*.mp4; do
  basename="${i%.mp4}"
  video-tool audio extract -i "$i" -o "${basename}.mp3" -c mp3 -b 192k
done

# Step 3: [Process audio files]

# Step 4: Replace audio back
for i in ./temp_clips/temp_*.mp4; do
  basename="${i%.mp4}"
  audio_file="${basename}.mp3"
  output="${basename}_processed.mp4"
  video-tool audio replace -v "$i" -a "$audio_file" -o "$output"
done

# Step 5: Concatenate all processed clips
video-tool concat \
  -i ./temp_clips/temp_*_processed.mp4 \
  -o final_output.mp4
```

---

### Workflow 4: Re-encoding for Size Optimization

```bash
# Step 1: Check original video info
video-tool info -i ../../source_video/sekiraras-escape-a-road-trip-with-a-shady-girl-720p.mp4
# Original: 876 MB, 39:26, 1280x720 H.264

# Step 2: Cut with hardware re-encoding (HEVC for smaller size)
video-tool cut \
  -i ../../source_video/sekiraras-escape-a-road-trip-with-a-shady-girl-720p.mp4 \
  -o ./optimized_clips \
  -d 11 \
  --no-copy \
  --profile clip_720p \
  --prefix optimized
# Result: 4 segments @ ~169 MB each (672 MB total, 23% smaller)

# Step 3: Verify output
video-tool info -i ./optimized_clips/optimized_001.mp4
# Output: 169 MB, 11:00, 1280x720 HEVC, ~2M bitrate

# Step 4: (Optional) Convert to H.264 for compatibility
video-tool concat \
  -i ./optimized_clips/optimized_*.mp4 \
  -o final_h264.mp4 \
  --no-copy \
  --profile web_720p
# Result: 22:00, H.264, works everywhere
```

**Use Cases:**
- Reduce storage: 20-30% smaller files
- Archive videos: HEVC uses less space
- Prepare for web: Convert to H.264

---

### Workflow 5: Add Intro/Outro (using concat)

```bash
# Prepare intro.mp4 and outro.mp4 first

# Add intro only
video-tool concat \
  -i intro.mp4 \
  -i ../../source_video/sekiraras-escape-a-road-trip-with-a-shady-girl-720p.mp4 \
  -o movie_with_intro.mp4

# Add both intro and outro
video-tool concat \
  -i intro.mp4 \
  -i ../../source_video/sekiraras-escape-a-road-trip-with-a-shady-girl-720p.mp4 \
  -i outro.mp4 \
  -o movie_with_intro_outro.mp4
```

---

## 🐛 TROUBLESHOOTING COMMANDS

### Check FFmpeg Installation
```bash
which ffmpeg
ffmpeg -version
ffprobe -version
```

### Check video-tool Installation
```bash
which video-tool
video-tool version
pip show video-tool
```

### Debug Mode
```bash
# Run with maximum verbosity
video-tool --verbose --log-file debug.log info -i movie.mp4

# Check log file
tail -f debug.log
tail -100 debug.log

# Check default log location
tail -f logs/video_tool.log
```

### Test with Small File
```bash
# Create test video (60 seconds)
ffmpeg -f lavfi -i testsrc=duration=60:size=1280x720:rate=30 \
       -f lavfi -i sine=frequency=1000:duration=60 \
       -pix_fmt yuv420p test_video.mp4

# Test operations
video-tool info -i test_video.mp4
video-tool cut -i test_video.mp4 -o ./test_output -d 1
video-tool audio extract -i test_video.mp4 -o test_audio.m4a -c copy
```

### Check Disk Space
```bash
df -h .
df -h /Users/Shared/jerry/tools/
```

### Validate Output Files
```bash
# Use ffprobe to check output
ffprobe -v error -show_format -show_streams output.mp4

# Play with ffplay
ffplay output.mp4

# Get file size
ls -lh output.mp4
du -sh output.mp4
```

---

## 📊 PERFORMANCE TIPS

### Fast Operations (Codec Copy)
```bash
# Always use codec copy when possible (no quality loss, very fast)
video-tool cut -i movie.mp4 -o ./output -d 11
video-tool concat -i part*.mp4 -o final.mp4
video-tool audio extract -i movie.mp4 -o audio.m4a -c copy
```

### Speed Comparison
- **Codec Copy:** ~1-5 seconds for any duration (just copying streams)
- **Re-encoding:** ~Real-time or slower (depends on hardware)

### Monitor Progress
```bash
# Use verbose mode to see progress
video-tool --verbose cut -i large_video.mp4 -o ./output -d 11
```

---

## 📝 QUICK REFERENCE

### Most Common Commands
```bash
# Check info
video-tool info -i movie.mp4

# Cut into 11-min segments
video-tool cut -i movie.mp4 -o ./clips -d 11

# Concat videos
video-tool concat -i part1.mp4 -i part2.mp4 -o final.mp4

# Extract audio
video-tool audio extract -i movie.mp4 -o audio.m4a -c copy

# Replace audio
video-tool audio replace -v video.mp4 -a audio.m4a -o output.mp4

# List profiles
video-tool profiles list
```

### Shorthand Syntax
```bash
-i = --input
-o = --output
-d = --duration
-c = --codec
-b = --bitrate
-v = --verbose (global) or --video (audio replace)
-a = --audio
```

---

## 📄 FILES & DIRECTORIES

### Project Structure
```
video_tool/
├── src/           # Source code
├── tests/         # Tests
├── configs/       # Configuration (profiles.yaml, logging.yaml)
├── logs/          # Log files (gitignored)
├── .venv/         # Virtual environment
├── cmd.md         # This file
└── README.md      # Documentation
```

### Log Files
```bash
# Default log location
logs/video_tool.log

# View logs
tail -f logs/video_tool.log
less logs/video_tool.log

# Custom log file
video-tool --log-file custom.log <command>
```

### Configuration Files
```bash
# Profiles configuration
configs/profiles.yaml

# Logging configuration
configs/logging.yaml

# View profiles
cat configs/profiles.yaml
```

---

## 🔗 RELATED COMMANDS

### FFmpeg Direct Commands (if needed)
```bash
# Get video info
ffprobe -v quiet -print_format json -show_format -show_streams movie.mp4

# Cut video manually
ffmpeg -i movie.mp4 -c copy -t 00:11:00 part1.mp4

# Extract audio manually
ffmpeg -i movie.mp4 -vn -acodec copy audio.m4a
```

### System Commands
```bash
# Find video files
find . -name "*.mp4" -type f

# Get file sizes
du -sh *.mp4

# Count files
ls *.mp4 | wc -l

# Rename files (slug format)
# See: rename script or manual mv commands
```

---

**Last Updated:** 2025-11-21  
**Maintained By:** Jerry  
**Status:** Phase 1 Complete - Production Ready
