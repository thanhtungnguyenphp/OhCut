"""Manual test script for file_utils module."""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from utils.file_utils import (
    validate_input_file,
    ensure_output_dir,
    generate_temp_filename,
    get_file_size,
    get_free_disk_space,
    get_safe_filename,
    cleanup_temp_files,
    InvalidInputError,
)


def main():
    print("=" * 60)
    print("File Utilities Module - Manual Test")
    print("=" * 60)

    # Test 1: Create temp file and validate
    print("\n[Test 1] Testing validate_input_file...")
    temp_file = Path(tempfile.mktemp(suffix=".mp4"))
    try:
        validate_input_file(str(temp_file))
        print("✗ Should have raised error for non-existent file")
    except InvalidInputError:
        print("✓ Correctly raised error for non-existent file")

    # Create actual file
    temp_file.write_text("test content")
    try:
        validate_input_file(str(temp_file))
        print(f"✓ File validated: {temp_file}")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")

    # Test 2: Get file size
    print("\n[Test 2] Testing get_file_size...")
    try:
        size = get_file_size(str(temp_file))
        print(f"✓ File size: {size} bytes")
    except Exception as e:
        print(f"✗ Error: {e}")

    # Test 3: Ensure output directory
    print("\n[Test 3] Testing ensure_output_dir...")
    test_dir = Path(tempfile.mkdtemp()) / "test" / "output"
    try:
        ensure_output_dir(str(test_dir))
        if test_dir.exists():
            print(f"✓ Directory created: {test_dir}")
        else:
            print("✗ Directory was not created")
    except Exception as e:
        print(f"✗ Error: {e}")

    # Test 4: Generate temp filename
    print("\n[Test 4] Testing generate_temp_filename...")
    try:
        temp_name = generate_temp_filename("test", ".mp4")
        print(f"✓ Temp filename generated: {Path(temp_name).name}")
        # Cleanup
        Path(temp_name).unlink(missing_ok=True)
    except Exception as e:
        print(f"✗ Error: {e}")

    # Test 5: Get free disk space
    print("\n[Test 5] Testing get_free_disk_space...")
    try:
        free_space = get_free_disk_space()
        free_gb = free_space / 1024 / 1024 / 1024
        print(f"✓ Free disk space: {free_gb:.2f} GB")
    except Exception as e:
        print(f"✗ Error: {e}")

    # Test 6: Get safe filename
    print("\n[Test 6] Testing get_safe_filename...")
    test_cases = [
        ('My Video: Part "1".mp4', "My Video_ Part _1_.mp4"),
        ("folder/file\\name.mp4", "folder_file_name.mp4"),
        ("  .test.mp4..  ", "test.mp4"),
    ]

    all_passed = True
    for original, expected in test_cases:
        safe = get_safe_filename(original)
        if safe == expected:
            print(f"✓ '{original}' → '{safe}'")
        else:
            print(f"✗ '{original}' → '{safe}' (expected '{expected}')")
            all_passed = False

    if all_passed:
        print("✓ All safe filename tests passed")

    # Test 7: Cleanup temp files
    print("\n[Test 7] Testing cleanup_temp_files...")
    test_file1 = Path(tempfile.mktemp(suffix=".mp4"))
    test_file2 = Path(tempfile.mktemp(suffix=".mp4"))
    test_file1.write_text("test1")
    test_file2.write_text("test2")

    cleanup_temp_files(str(test_file1), str(test_file2))

    if not test_file1.exists() and not test_file2.exists():
        print("✓ Temp files cleaned up successfully")
    else:
        print("✗ Some files were not deleted")

    # Cleanup test file
    temp_file.unlink(missing_ok=True)

    print("\n" + "=" * 60)
    print("All manual tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
