# TASK 1.8: Profile Configuration System - COMPLETE ✅

**Completed:** 2025-11-19  
**Time Spent:** 1 session

## Deliverables

### 1. Configuration File: `configs/profiles.yaml`
- **Lines:** 135 lines
- **Profiles:** 11 encoding profiles covering multiple use cases
- **Categories:**
  - **Movie profiles:** movie_1080p, movie_720p (high quality for full-length movies)
  - **Clip profiles:** clip_720p, clip_480p (optimized for 11-minute segments)
  - **Web profiles:** web_1080p, web_720p (H.264 for maximum compatibility)
  - **Mobile profiles:** mobile_720p, mobile_480p (efficient for mobile devices)
  - **Quality profiles:** quality_high, quality_medium (CRF-based variable bitrate)
  - **Fast profile:** fast (quick turnaround encoding)

**Key Features:**
- Hardware acceleration support (VideoToolbox on macOS)
- Software encoding fallback (libx264, libx265)
- Bitrate-based and CRF-based encoding
- Comprehensive codec options (hevc_videotoolbox, libx264, libx265, aac, mp3, opus)
- Resolution and FPS control
- Preset configuration for software codecs

### 2. Core Module: `src/core/profiles.py`
- **Lines:** 415 lines
- **Components:**
  - `Profile` dataclass with validation
  - Exception classes: `ProfileError`, `ProfileNotFoundError`, `InvalidProfileError`
  - 8 core functions

**Functions Implemented:**
1. `load_profiles()` - Load and cache all profiles from YAML
2. `get_profile(name)` - Get specific profile by name
3. `get_default_profile()` - Get default profile (clip_720p)
4. `list_profiles()` - List all available profile names
5. `validate_profile(profile)` - Validate profile configuration
6. `apply_profile_to_ffmpeg_args()` - Convert profile to FFmpeg arguments
7. `get_profile_summary()` - Generate human-readable profile summary
8. `get_profiles_path()` - Locate profiles.yaml file

**Profile Dataclass Features:**
- Comprehensive validation (codecs, presets, CRF, resolution, FPS)
- Resolution parsing (`get_resolution_tuple()`)
- Hardware acceleration detection (`uses_hardware_acceleration()`)
- Dictionary conversion (`to_dict()`)
- Support for both bitrate and CRF-based encoding

### 3. Unit Tests: `tests/test_profiles.py`
- **Lines:** 458 lines
- **Test Classes:** 5 classes with 26 test methods
- **Coverage Areas:**
  - Profile dataclass creation and validation
  - Invalid codec/preset/CRF/resolution handling
  - Profile loading and caching
  - Getting profiles (valid/invalid names)
  - Default profile retrieval
  - Profile listing
  - FFmpeg arguments generation
  - Profile summaries
  - Hardware vs software detection
  - CRF vs bitrate profiles

**Test Classes:**
1. `TestProfileDataclass` - 11 tests for Profile validation
2. `TestProfileLoading` - 6 tests for loading profiles
3. `TestValidateProfile` - 2 tests for validation function
4. `TestApplyProfileToFFmpegArgs` - 5 tests for FFmpeg args
5. `TestGetProfileSummary` - 2 tests for summary generation

### 4. Manual Test Script: `tests/manual/test_profiles_manual.py`
- **Lines:** 284 lines (executable script)
- **Tests:** 8 comprehensive test functions

**Test Functions:**
1. Load all profiles from YAML
2. List profile names
3. Get default profile
4. Get specific profiles (clip_720p, movie_1080p, web_720p, mobile_480p)
5. Invalid profile handling
6. Profile summaries (clip_720p, quality_high, fast)
7. FFmpeg arguments generation for multiple profiles
8. Profile types analysis (hardware vs software, CRF vs bitrate)

## Profile Configuration Details

### Hardware-Accelerated Profiles (macOS VideoToolbox)
```yaml
movie_1080p:  4M bitrate, 1920x1080, hevc_videotoolbox
movie_720p:   2500k bitrate, 1280x720, hevc_videotoolbox
clip_720p:    2M bitrate, 1280x720, hevc_videotoolbox (default)
clip_480p:    1200k bitrate, 854x480, hevc_videotoolbox
```

### Software-Encoded Profiles (H.264)
```yaml
web_1080p:    3500k bitrate, 1920x1080, libx264, preset=fast
web_720p:     2M bitrate, 1280x720, libx264, preset=fast
mobile_720p:  1500k bitrate, 1280x720, libx264, preset=veryfast
mobile_480p:  800k bitrate, 854x480, libx264, preset=veryfast
fast:         3M bitrate, source resolution, libx264, preset=ultrafast
```

### Quality-Based Profiles (CRF)
```yaml
quality_high:   CRF=20, source resolution, libx265, preset=medium
quality_medium: CRF=24, source resolution, libx265, preset=medium
```

## Testing Instructions

### Option 1: Run with Dependencies Installed

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux

# Install dependencies
pip install pyyaml

# Run manual test script
python3 tests/manual/test_profiles_manual.py
```

**Expected Output:**
```
======================================================================
  PROFILE CONFIGURATION SYSTEM - MANUAL TESTS
======================================================================

======================================================================
  TEST 1: Load All Profiles
======================================================================

✅ Successfully loaded 11 profiles
   Profile names: movie_1080p, movie_720p, clip_720p, ...

[... 8 tests ...]

======================================================================
  TEST SUMMARY
======================================================================

Tests Passed: 8/8

✅ PASS: Load Profiles
✅ PASS: List Profiles
✅ PASS: Get Default Profile
✅ PASS: Get Specific Profiles
✅ PASS: Invalid Profile Handling
✅ PASS: Profile Summaries
✅ PASS: FFmpeg Args Generation
✅ PASS: Profile Types Analysis

======================================================================

🎉 All tests passed!
```

### Option 2: Run Unit Tests with pytest

```bash
# With virtual environment activated
pip install pytest pyyaml

# Run all profile tests
pytest tests/test_profiles.py -v

# Run specific test class
pytest tests/test_profiles.py::TestProfileDataclass -v

# Run with coverage
pytest tests/test_profiles.py --cov=src.core.profiles
```

**Expected Results:**
- 26 unit tests should all pass
- Tests cover validation, loading, FFmpeg args generation, and error handling

### Option 3: Quick Verification (Python REPL)

```python
import sys
sys.path.insert(0, '.')

from src.core.profiles import load_profiles, get_profile, list_profiles

# Load all profiles
profiles = load_profiles()
print(f"Loaded {len(profiles)} profiles")

# List profile names
print("Available profiles:", list_profiles())

# Get specific profile
clip = get_profile('clip_720p')
print(f"Profile: {clip.name}")
print(f"Codec: {clip.video_codec}")
print(f"Resolution: {clip.resolution}")
print(f"Hardware Accel: {clip.uses_hardware_acceleration()}")

# Generate FFmpeg args
from src.core.profiles import apply_profile_to_ffmpeg_args
args = apply_profile_to_ffmpeg_args(clip, 'input.mp4', 'output.mp4')
print("FFmpeg args:", ' '.join(args))
```

## Usage Examples

### Example 1: Get Profile and Generate FFmpeg Command

```python
from src.core.profiles import get_profile, apply_profile_to_ffmpeg_args

# Get the clip_720p profile
profile = get_profile('clip_720p')

# Generate FFmpeg arguments
args = apply_profile_to_ffmpeg_args(
    profile,
    input_path='movie.mp4',
    output_path='clip_01.mp4'
)

# FFmpeg command would be:
# ffmpeg -i movie.mp4 -c:v hevc_videotoolbox -b:v 2M -s 1280x720 \
#        -c:a aac -b:a 128k clip_01.mp4
```

### Example 2: List All Available Profiles

```python
from src.core.profiles import list_profiles, get_profile

profiles = list_profiles()
for name in profiles:
    profile = get_profile(name)
    print(f"{name}: {profile.description}")
```

### Example 3: Get Profile Summary

```python
from src.core.profiles import get_profile, get_profile_summary

profile = get_profile('movie_1080p')
summary = get_profile_summary(profile)
print(summary)

# Output:
# Profile: movie_1080p
# Description: High-quality 1080p profile for full-length movies (H.265/HEVC)
#
# Video:
#   Codec: hevc_videotoolbox
#   Bitrate: 4M
#   Resolution: 1920x1080
#   FPS: source
#   Hardware Accel: videotoolbox
#
# Audio:
#   Codec: aac
#   Bitrate: 192k
```

### Example 4: Check Hardware Acceleration

```python
from src.core.profiles import get_profile

profile = get_profile('web_720p')
if profile.uses_hardware_acceleration():
    print("Using hardware acceleration")
else:
    print("Using software encoding")
```

## Integration with Other Modules

The profile system integrates with:

1. **video_ops.py** - Can use profiles for cutting and encoding videos
2. **audio_ops.py** - Can use audio settings from profiles
3. **CLI** (future) - Will allow users to specify profiles by name
4. **Pipelines** (future) - Movie-to-clips pipeline will use profiles

## Next Steps

### Immediate (TASK 1.9): CLI Commands
- Integrate profile system into CLI
- Add `--profile` flag to commands
- Implement `video-tool profiles list` command
- Add `video-tool profiles show <name>` command

### Future Enhancements:
- Custom profile creation via CLI
- Profile inheritance (e.g., extend base profiles)
- Dynamic profile selection based on input video properties
- Profile validation against system capabilities (check for hardware encoders)

## Notes

- **Default Profile:** `clip_720p` (optimized for 11-minute segments)
- **Hardware Acceleration:** VideoToolbox profiles only work on macOS
- **Fallback Strategy:** CLI should detect if hardware encoder unavailable and suggest software alternative
- **Profile Caching:** Profiles are loaded once and cached for performance
- **Validation:** All profiles are validated on load (invalid profiles will raise exceptions)

## Files Modified/Created

```
video_tool/
├── configs/
│   └── profiles.yaml              (NEW - 135 lines)
├── src/
│   └── core/
│       └── profiles.py            (NEW - 415 lines)
└── tests/
    ├── test_profiles.py           (NEW - 458 lines)
    └── manual/
        └── test_profiles_manual.py (NEW - 284 lines, executable)
```

**Total:** 1,292 lines of code and configuration

---

## Status: ✅ COMPLETE

All deliverables completed:
- ✅ profiles.yaml with 11 comprehensive profiles
- ✅ profiles.py with Profile dataclass and 8 functions
- ✅ test_profiles.py with 26 unit tests
- ✅ test_profiles_manual.py with 8 manual test functions
- ✅ Comprehensive validation and error handling
- ✅ FFmpeg arguments generation
- ✅ Hardware acceleration support
- ✅ Documentation and usage examples

**Ready for integration with CLI (TASK 1.9).**
