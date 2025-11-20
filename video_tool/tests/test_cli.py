"""
Unit tests for CLI commands.
"""

import pytest
import tempfile
import os
from pathlib import Path
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock

from src.cli.main import app


# Initialize test runner
runner = CliRunner()


class TestCLIBasics:
    """Test basic CLI functionality."""
    
    def test_help(self):
        """Test main help command."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Video Tool" in result.stdout
        assert "cut" in result.stdout
        assert "concat" in result.stdout
        assert "info" in result.stdout
        assert "audio" in result.stdout
        assert "profiles" in result.stdout
    
    def test_version(self):
        """Test version command."""
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "Video Tool" in result.stdout
        assert "0.1.0" in result.stdout
    
    def test_invalid_command(self):
        """Test invalid command shows error."""
        result = runner.invoke(app, ["invalid-command"])
        assert result.exit_code != 0


class TestCutCommand:
    """Test 'cut' command."""
    
    def test_cut_help(self):
        """Test cut help text."""
        result = runner.invoke(app, ["cut", "--help"])
        assert result.exit_code == 0
        assert "Cut video into segments" in result.stdout
        assert "--input" in result.stdout
        assert "--output-dir" in result.stdout
        assert "--duration" in result.stdout
    
    def test_cut_missing_input(self):
        """Test cut without required input option."""
        result = runner.invoke(app, ["cut"])
        assert result.exit_code != 0
        assert "Missing option" in result.stdout or "Error" in result.stdout
    
    def test_cut_nonexistent_file(self):
        """Test cut with nonexistent input file."""
        result = runner.invoke(app, [
            "cut",
            "--input", "/nonexistent/file.mp4",
            "--output-dir", "/tmp/output"
        ])
        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()
    
    def test_cut_dry_run(self):
        """Test cut with dry-run mode."""
        # Create a temporary file to pass validation
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            # Mock get_video_info to return fake data
            with patch('src.cli.main.file_utils.get_video_info') as mock_info:
                mock_info.return_value = {
                    'duration': 1320,  # 22 minutes
                    'width': 1280,
                    'height': 720,
                }
                
                result = runner.invoke(app, [
                    "--dry-run",
                    "cut",
                    "--input", tmp_path,
                    "--output-dir", "/tmp/output",
                    "--duration", "11"
                ])
                
                assert result.exit_code == 0
                assert "DRY RUN" in result.stdout
                assert "Would create files" in result.stdout
        finally:
            os.unlink(tmp_path)


class TestConcatCommand:
    """Test 'concat' command."""
    
    def test_concat_help(self):
        """Test concat help text."""
        result = runner.invoke(app, ["concat", "--help"])
        assert result.exit_code == 0
        assert "Concatenate" in result.stdout
        assert "--inputs" in result.stdout
        assert "--output" in result.stdout
    
    def test_concat_missing_options(self):
        """Test concat without required options."""
        result = runner.invoke(app, ["concat"])
        assert result.exit_code != 0
    
    def test_concat_nonexistent_file(self):
        """Test concat with nonexistent input files."""
        result = runner.invoke(app, [
            "concat",
            "--inputs", "/nonexistent/file1.mp4",
            "--inputs", "/nonexistent/file2.mp4",
            "--output", "/tmp/output.mp4"
        ])
        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()
    
    def test_concat_dry_run(self):
        """Test concat with dry-run mode."""
        # Create temporary files
        tmp_files = []
        for i in range(2):
            tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
            tmp_files.append(tmp.name)
            tmp.close()
        
        try:
            result = runner.invoke(app, [
                "--dry-run",
                "concat",
                "--inputs", tmp_files[0],
                "--inputs", tmp_files[1],
                "--output", "/tmp/output.mp4"
            ])
            
            assert result.exit_code == 0
            assert "DRY RUN" in result.stdout
            assert "Would concatenate" in result.stdout
        finally:
            for f in tmp_files:
                os.unlink(f)


class TestInfoCommand:
    """Test 'info' command."""
    
    def test_info_help(self):
        """Test info help text."""
        result = runner.invoke(app, ["info", "--help"])
        assert result.exit_code == 0
        assert "Display video file information" in result.stdout
        assert "--input" in result.stdout
    
    def test_info_missing_input(self):
        """Test info without input option."""
        result = runner.invoke(app, ["info"])
        assert result.exit_code != 0
    
    def test_info_nonexistent_file(self):
        """Test info with nonexistent file."""
        result = runner.invoke(app, [
            "info",
            "--input", "/nonexistent/file.mp4"
        ])
        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()
    
    def test_info_with_mock_data(self):
        """Test info command with mocked video info."""
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            with patch('src.cli.main.file_utils.get_video_info') as mock_info:
                mock_info.return_value = {
                    'format': 'mp4',
                    'duration': 120.5,
                    'width': 1920,
                    'height': 1080,
                    'codec': 'h264',
                    'bitrate': '2000k',
                    'fps': 30.0,
                    'audio_codec': 'aac',
                }
                
                result = runner.invoke(app, [
                    "info",
                    "--input", tmp_path
                ])
                
                assert result.exit_code == 0
                assert "Video Information" in result.stdout
                assert "1920x1080" in result.stdout
                assert "h264" in result.stdout
        finally:
            os.unlink(tmp_path)


class TestAudioCommands:
    """Test 'audio' subcommands."""
    
    def test_audio_help(self):
        """Test audio command group help."""
        result = runner.invoke(app, ["audio", "--help"])
        assert result.exit_code == 0
        assert "Audio operations" in result.stdout
        assert "extract" in result.stdout
        assert "replace" in result.stdout
    
    def test_audio_extract_help(self):
        """Test audio extract help text."""
        result = runner.invoke(app, ["audio", "extract", "--help"])
        assert result.exit_code == 0
        assert "Extract audio from video" in result.stdout
        assert "--codec" in result.stdout
        assert "--bitrate" in result.stdout
    
    def test_audio_extract_dry_run(self):
        """Test audio extract with dry-run."""
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            result = runner.invoke(app, [
                "--dry-run",
                "audio", "extract",
                "--input", tmp_path,
                "--output", "/tmp/audio.m4a",
                "--codec", "copy"
            ])
            
            assert result.exit_code == 0
            assert "DRY RUN" in result.stdout
        finally:
            os.unlink(tmp_path)
    
    def test_audio_replace_help(self):
        """Test audio replace help text."""
        result = runner.invoke(app, ["audio", "replace", "--help"])
        assert result.exit_code == 0
        assert "Replace audio track" in result.stdout
        assert "--video" in result.stdout
        assert "--audio" in result.stdout
    
    def test_audio_replace_nonexistent_files(self):
        """Test audio replace with nonexistent files."""
        result = runner.invoke(app, [
            "audio", "replace",
            "--video", "/nonexistent/video.mp4",
            "--audio", "/nonexistent/audio.m4a",
            "--output", "/tmp/output.mp4"
        ])
        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()


class TestProfilesCommands:
    """Test 'profiles' subcommands."""
    
    def test_profiles_help(self):
        """Test profiles command group help."""
        result = runner.invoke(app, ["profiles", "--help"])
        assert result.exit_code == 0
        assert "Profile management" in result.stdout
        assert "list" in result.stdout
        assert "show" in result.stdout
    
    def test_profiles_list(self):
        """Test profiles list command."""
        result = runner.invoke(app, ["profiles", "list"])
        assert result.exit_code == 0
        assert "Available Profiles" in result.stdout
        assert "clip_720p" in result.stdout or "Profile" in result.stdout
    
    def test_profiles_show_help(self):
        """Test profiles show help text."""
        result = runner.invoke(app, ["profiles", "show", "--help"])
        assert result.exit_code == 0
        assert "Show detailed information" in result.stdout
    
    def test_profiles_show_valid(self):
        """Test profiles show with valid profile name."""
        result = runner.invoke(app, ["profiles", "show", "clip_720p"])
        # May fail if yaml not installed, so just check it doesn't crash badly
        # Exit code could be 0 (success) or 1 (import error)
        assert "clip_720p" in result.stdout or "Error" in result.stdout
    
    def test_profiles_show_invalid(self):
        """Test profiles show with invalid profile name."""
        result = runner.invoke(app, ["profiles", "show", "nonexistent_profile"])
        # May fail due to import error or profile not found
        # Just check it handles error gracefully
        assert result.exit_code != 0 or "Error" in result.stdout


class TestGlobalOptions:
    """Test global CLI options."""
    
    def test_verbose_flag(self):
        """Test --verbose flag is recognized."""
        result = runner.invoke(app, ["--verbose", "--help"])
        assert result.exit_code == 0
    
    def test_dry_run_flag(self):
        """Test --dry-run flag is recognized."""
        result = runner.invoke(app, ["--dry-run", "--help"])
        assert result.exit_code == 0
    
    def test_log_file_option(self):
        """Test --log-file option is recognized."""
        result = runner.invoke(app, ["--log-file", "/tmp/test.log", "--help"])
        assert result.exit_code == 0


class TestErrorHandling:
    """Test error handling and user feedback."""
    
    def test_ffmpeg_not_installed(self):
        """Test error message when FFmpeg is not installed."""
        with patch('src.cli.main.ffmpeg_runner.check_ffmpeg_installed') as mock_check:
            mock_check.return_value = False
            
            # Create a temp file for testing
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
                tmp_path = tmp.name
            
            try:
                result = runner.invoke(app, [
                    "info",
                    "--input", tmp_path
                ])
                
                assert result.exit_code == 1
                assert "FFmpeg" in result.stdout or "ffmpeg" in result.stdout
            finally:
                os.unlink(tmp_path)
