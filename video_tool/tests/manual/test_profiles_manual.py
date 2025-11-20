#!/usr/bin/env python3
"""
Manual test script for Profile Configuration System.
Demonstrates profile loading, listing, and FFmpeg args generation.

Note: This script requires pyyaml to be installed.
Install with: pip install pyyaml (or use a virtual environment)
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from src.core.profiles import (
        load_profiles,
        get_profile,
        get_default_profile,
        list_profiles,
        apply_profile_to_ffmpeg_args,
        get_profile_summary,
        ProfileNotFoundError,
        InvalidProfileError,
    )
except ImportError as e:
    print(f"❌ Import Error: {e}")
    print("\nThis script requires pyyaml to be installed.")
    print("Please install dependencies:")
    print("  python3 -m venv venv")
    print("  source venv/bin/activate")
    print("  pip install pyyaml")
    sys.exit(1)


def print_separator(title=""):
    """Print a visual separator."""
    if title:
        print(f"\n{'='*70}")
        print(f"  {title}")
        print(f"{'='*70}\n")
    else:
        print(f"{'='*70}\n")


def test_load_profiles():
    """Test loading all profiles."""
    print_separator("TEST 1: Load All Profiles")
    
    try:
        profiles = load_profiles(force_reload=True)
        print(f"✅ Successfully loaded {len(profiles)} profiles")
        print(f"   Profile names: {', '.join(profiles.keys())}")
        return True
    except Exception as e:
        print(f"❌ Failed to load profiles: {e}")
        return False


def test_list_profiles():
    """Test listing profile names."""
    print_separator("TEST 2: List Profile Names")
    
    try:
        profile_names = list_profiles()
        print(f"✅ Found {len(profile_names)} profiles:")
        for i, name in enumerate(profile_names, 1):
            print(f"   {i}. {name}")
        return True
    except Exception as e:
        print(f"❌ Failed to list profiles: {e}")
        return False


def test_get_default_profile():
    """Test getting the default profile."""
    print_separator("TEST 3: Get Default Profile")
    
    try:
        profile = get_default_profile()
        print(f"✅ Default profile: {profile.name}")
        print(f"   Description: {profile.description}")
        print(f"   Video Codec: {profile.video_codec}")
        print(f"   Resolution: {profile.resolution}")
        return True
    except Exception as e:
        print(f"❌ Failed to get default profile: {e}")
        return False


def test_get_specific_profiles():
    """Test getting specific profiles."""
    print_separator("TEST 4: Get Specific Profiles")
    
    test_profiles = ['clip_720p', 'movie_1080p', 'web_720p', 'mobile_480p']
    success = True
    
    for profile_name in test_profiles:
        try:
            profile = get_profile(profile_name)
            print(f"✅ Profile: {profile_name}")
            print(f"   Codec: {profile.video_codec}, Resolution: {profile.resolution}")
            print(f"   Audio: {profile.audio_codec} @ {profile.audio_bitrate}")
            hw_accel = "Yes" if profile.uses_hardware_acceleration() else "No"
            print(f"   Hardware Acceleration: {hw_accel}")
            print()
        except ProfileNotFoundError as e:
            print(f"❌ Profile '{profile_name}' not found: {e}")
            success = False
            print()
        except Exception as e:
            print(f"❌ Error getting profile '{profile_name}': {e}")
            success = False
            print()
    
    return success


def test_get_invalid_profile():
    """Test getting an invalid profile (should fail gracefully)."""
    print_separator("TEST 5: Get Invalid Profile (Expected to Fail)")
    
    try:
        profile = get_profile('nonexistent_profile')
        print(f"❌ Should have raised ProfileNotFoundError but got: {profile.name}")
        return False
    except ProfileNotFoundError as e:
        print(f"✅ Correctly raised ProfileNotFoundError: {e}")
        return True
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_profile_summaries():
    """Test generating profile summaries."""
    print_separator("TEST 6: Profile Summaries")
    
    test_profiles = ['clip_720p', 'quality_high', 'fast']
    success = True
    
    for profile_name in test_profiles:
        try:
            profile = get_profile(profile_name)
            summary = get_profile_summary(profile)
            print(f"📋 {profile_name.upper()}:")
            print(summary)
            print()
        except Exception as e:
            print(f"❌ Error generating summary for '{profile_name}': {e}")
            success = False
            print()
    
    return success


def test_ffmpeg_args_generation():
    """Test generating FFmpeg arguments from profiles."""
    print_separator("TEST 7: FFmpeg Arguments Generation")
    
    test_cases = [
        ('clip_720p', 'input.mp4', 'output_720p.mp4'),
        ('movie_1080p', 'video.mp4', 'encoded_1080p.mp4'),
        ('quality_high', 'source.mp4', 'quality_output.mp4'),
        ('fast', 'test.mp4', 'fast_output.mp4'),
    ]
    
    success = True
    
    for profile_name, input_path, output_path in test_cases:
        try:
            profile = get_profile(profile_name)
            args = apply_profile_to_ffmpeg_args(profile, input_path, output_path)
            
            print(f"✅ Profile: {profile_name}")
            print(f"   Input: {input_path} → Output: {output_path}")
            print(f"   FFmpeg args: {' '.join(args)}")
            print()
        except Exception as e:
            print(f"❌ Error generating args for '{profile_name}': {e}")
            success = False
            print()
    
    return success


def test_profile_types():
    """Test different profile types (hardware vs software, CRF vs bitrate)."""
    print_separator("TEST 8: Profile Types")
    
    print("🔍 Analyzing profile characteristics:\n")
    
    profiles = load_profiles()
    
    hw_profiles = []
    sw_profiles = []
    crf_profiles = []
    bitrate_profiles = []
    
    for name, profile in profiles.items():
        if profile.uses_hardware_acceleration():
            hw_profiles.append(name)
        else:
            sw_profiles.append(name)
        
        if profile.crf is not None:
            crf_profiles.append(name)
        else:
            bitrate_profiles.append(name)
    
    print(f"🔧 Hardware-Accelerated Profiles ({len(hw_profiles)}):")
    for name in hw_profiles:
        print(f"   - {name}")
    
    print(f"\n💻 Software-Encoded Profiles ({len(sw_profiles)}):")
    for name in sw_profiles:
        print(f"   - {name}")
    
    print(f"\n📊 CRF-Based Profiles ({len(crf_profiles)}):")
    for name in crf_profiles:
        profile = profiles[name]
        print(f"   - {name} (CRF: {profile.crf})")
    
    print(f"\n📈 Bitrate-Based Profiles ({len(bitrate_profiles)}):")
    for name in bitrate_profiles:
        profile = profiles[name]
        print(f"   - {name} (Bitrate: {profile.video_bitrate})")
    
    return True


def main():
    """Run all tests."""
    print_separator("PROFILE CONFIGURATION SYSTEM - MANUAL TESTS")
    
    tests = [
        ("Load Profiles", test_load_profiles),
        ("List Profiles", test_list_profiles),
        ("Get Default Profile", test_get_default_profile),
        ("Get Specific Profiles", test_get_specific_profiles),
        ("Invalid Profile Handling", test_get_invalid_profile),
        ("Profile Summaries", test_profile_summaries),
        ("FFmpeg Args Generation", test_ffmpeg_args_generation),
        ("Profile Types Analysis", test_profile_types),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"\n❌ Test '{test_name}' crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Print summary
    print_separator("TEST SUMMARY")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    print(f"Tests Passed: {passed}/{total}\n")
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print_separator()
    
    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print(f"⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
