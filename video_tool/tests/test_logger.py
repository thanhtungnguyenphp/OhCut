"""Unit tests for logger module.

Tests logging setup, configuration, context management, and utility functions.
"""

import pytest
import logging
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open, call
import yaml

from utils.logger import (
    get_config_path,
    setup_logging,
    get_logger,
    log_operation,
    get_operation_context,
    log_ffmpeg_command,
    log_file_operation,
    LoggerAdapter,
    configure_verbose_logging,
    log_exception,
    log_performance,
)


class TestGetConfigPath:
    """Tests for get_config_path() function."""

    def test_get_config_path_returns_path(self):
        """Test that get_config_path returns a Path object."""
        result = get_config_path()
        assert isinstance(result, Path)

    def test_get_config_path_points_to_yaml(self):
        """Test that config path points to logging.yaml."""
        result = get_config_path()
        assert result.name == "logging.yaml"
        assert "configs" in str(result)


class TestSetupLogging:
    """Tests for setup_logging() function."""

    @patch("utils.logger.Path.exists")
    @patch("utils.logger.Path.mkdir")
    @patch("utils.logger.logging.config.dictConfig")
    @patch("utils.logger.open", new_callable=mock_open, read_data="version: 1\nhandlers: {}\nloggers: {}")
    def test_setup_logging_with_default_config(
        self, mock_file, mock_dictConfig, mock_mkdir, mock_exists
    ):
        """Test setup_logging with default config path."""
        mock_exists.return_value = True
        
        setup_logging()
        
        mock_dictConfig.assert_called_once()
        mock_mkdir.assert_called_once()

    @patch("utils.logger.logging.basicConfig")
    @patch("utils.logger.Path.exists")
    def test_setup_logging_missing_config_uses_fallback(
        self, mock_exists, mock_basicConfig
    ):
        """Test setup_logging falls back to basic config when file missing."""
        mock_exists.return_value = False
        
        setup_logging()
        
        mock_basicConfig.assert_called_once()
        # Check that it was called with level argument
        call_kwargs = mock_basicConfig.call_args[1]
        assert 'level' in call_kwargs

    @patch("utils.logger.Path.exists")
    @patch("utils.logger.Path.mkdir")
    @patch("utils.logger.logging.config.dictConfig")
    @patch("utils.logger.open", new_callable=mock_open, read_data="version: 1\nhandlers:\n  console:\n    level: INFO\nloggers: {}")
    def test_setup_logging_verbose_mode(
        self, mock_file, mock_dictConfig, mock_mkdir, mock_exists
    ):
        """Test setup_logging with verbose=True sets DEBUG level."""
        mock_exists.return_value = True
        
        setup_logging(verbose=True)
        
        # Verify dictConfig was called
        assert mock_dictConfig.called
        config = mock_dictConfig.call_args[0][0]
        
        # Console handler should be set to DEBUG
        assert config['handlers']['console']['level'] == 'DEBUG'

    @patch("utils.logger.Path.exists")
    @patch("utils.logger.Path.mkdir")
    @patch("utils.logger.logging.config.dictConfig")
    @patch("utils.logger.open", new_callable=mock_open, read_data="version: 1\nhandlers:\n  file:\n    filename: default.log\nloggers: {}")
    def test_setup_logging_custom_log_file(
        self, mock_file, mock_dictConfig, mock_mkdir, mock_exists
    ):
        """Test setup_logging with custom log file path."""
        mock_exists.return_value = True
        
        setup_logging(log_file="/tmp/custom.log")
        
        # Verify custom log file path was set
        config = mock_dictConfig.call_args[0][0]
        assert config['handlers']['file']['filename'] == "/tmp/custom.log"

    def test_setup_logging_with_custom_config_path(self):
        """Test setup_logging with custom config path."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({
                'version': 1,
                'handlers': {},
                'loggers': {}
            }, f)
            config_path = f.name
        
        try:
            setup_logging(config_path=config_path)
            # Should not raise an exception
        finally:
            Path(config_path).unlink()


class TestGetLogger:
    """Tests for get_logger() function."""

    def test_get_logger_returns_logger(self):
        """Test get_logger returns a Logger instance."""
        logger = get_logger("test_logger")
        assert isinstance(logger, logging.Logger)

    def test_get_logger_with_module_name(self):
        """Test get_logger with __name__ pattern."""
        logger = get_logger(__name__)
        assert isinstance(logger, logging.Logger)
        assert logger.name == __name__

    def test_get_logger_same_name_returns_same_instance(self):
        """Test that same name returns same logger instance."""
        logger1 = get_logger("test")
        logger2 = get_logger("test")
        assert logger1 is logger2


class TestLogOperation:
    """Tests for log_operation() context manager."""

    def test_log_operation_success(self, caplog):
        """Test log_operation logs start and completion."""
        logger = get_logger("test")
        
        with caplog.at_level(logging.INFO):
            with log_operation("test_operation", logger, input_file="test.mp4"):
                pass
        
        # Check logs
        assert "Starting operation: test_operation" in caplog.text
        assert "Completed operation: test_operation" in caplog.text
        assert "input_file=test.mp4" in caplog.text

    def test_log_operation_with_exception(self, caplog):
        """Test log_operation logs failure on exception."""
        logger = get_logger("test")
        
        with caplog.at_level(logging.ERROR):
            with pytest.raises(ValueError):
                with log_operation("test_operation", logger):
                    raise ValueError("Test error")
        
        assert "Failed operation: test_operation" in caplog.text
        assert "Test error" in caplog.text

    def test_log_operation_without_logger(self, caplog):
        """Test log_operation works without explicit logger."""
        with caplog.at_level(logging.INFO):
            with log_operation("test_operation"):
                pass
        
        assert "Starting operation" in caplog.text

    def test_log_operation_context_stored(self):
        """Test log_operation stores context in thread-local storage."""
        logger = get_logger("test")
        
        with log_operation("test_op", logger, key="value"):
            context = get_operation_context()
            assert context['operation'] == 'test_op'
            assert context['key'] == 'value'
        
        # Context should be cleared after
        context_after = get_operation_context()
        assert context_after == {}

    def test_log_operation_nested_contexts(self):
        """Test nested log_operation contexts."""
        logger = get_logger("test")
        
        with log_operation("outer", logger):
            outer_ctx = get_operation_context()
            assert outer_ctx['operation'] == 'outer'
            
            with log_operation("inner", logger):
                inner_ctx = get_operation_context()
                assert inner_ctx['operation'] == 'inner'
            
            # After inner completes, should be back to outer
            outer_ctx_again = get_operation_context()
            assert outer_ctx_again['operation'] == 'outer'


class TestGetOperationContext:
    """Tests for get_operation_context() function."""

    def test_get_operation_context_empty_initially(self):
        """Test get_operation_context returns empty dict initially."""
        context = get_operation_context()
        assert context == {}

    def test_get_operation_context_with_active_operation(self):
        """Test get_operation_context returns context during operation."""
        logger = get_logger("test")
        
        with log_operation("test", logger, param="value"):
            context = get_operation_context()
            assert 'operation' in context
            assert context['param'] == 'value'


class TestLogFFmpegCommand:
    """Tests for log_ffmpeg_command() function."""

    def test_log_ffmpeg_command_success(self, caplog):
        """Test logging successful FFmpeg command."""
        logger = get_logger("test")
        command = ["ffmpeg", "-i", "input.mp4", "output.mp4"]
        
        with caplog.at_level(logging.DEBUG):
            log_ffmpeg_command(logger, command, success=True, execution_time=1.5)
        
        assert "FFmpeg command executed" in caplog.text
        assert "ffmpeg -i input.mp4 output.mp4" in caplog.text
        assert "1.50s" in caplog.text

    def test_log_ffmpeg_command_failure(self, caplog):
        """Test logging failed FFmpeg command."""
        logger = get_logger("test")
        command = ["ffmpeg", "-i", "input.mp4"]
        stderr = "Error: invalid file"
        
        with caplog.at_level(logging.ERROR):
            log_ffmpeg_command(logger, command, success=False, stderr=stderr)
        
        assert "FFmpeg command failed" in caplog.text
        assert "Error: invalid file" in caplog.text

    def test_log_ffmpeg_command_with_stderr_debug(self, caplog):
        """Test logging FFmpeg stderr at debug level."""
        logger = get_logger("test")
        command = ["ffmpeg", "-i", "input.mp4"]
        stderr = "Some debug output"
        
        with caplog.at_level(logging.DEBUG):
            log_ffmpeg_command(logger, command, success=True, stderr=stderr)
        
        # stderr should be logged at DEBUG level
        assert "FFmpeg stderr" in caplog.text or stderr in caplog.text


class TestLogFileOperation:
    """Tests for log_file_operation() function."""

    def test_log_file_operation(self, caplog):
        """Test logging file operations."""
        logger = get_logger("test")
        
        with caplog.at_level(logging.INFO):
            log_file_operation(
                logger,
                "cut",
                input_files=["input.mp4"],
                output_file="output.mp4",
                duration=11
            )
        
        assert "Cut operation" in caplog.text


class TestLoggerAdapter:
    """Tests for LoggerAdapter class."""

    def test_logger_adapter_adds_context(self, caplog):
        """Test LoggerAdapter adds structured context."""
        logger = get_logger("test")
        adapter = LoggerAdapter(logger, {'operation': 'test_op'})
        
        with caplog.at_level(logging.INFO):
            adapter.info("Test message")
        
        assert "Test message" in caplog.text

    def test_logger_adapter_with_operation_context(self, caplog):
        """Test LoggerAdapter merges with operation context."""
        logger = get_logger("test")
        adapter = LoggerAdapter(logger, {'key': 'value'})
        
        with log_operation("test_op", logger):
            with caplog.at_level(logging.INFO):
                adapter.info("Message")
            
            # Adapter should merge operation context
            assert "Message" in caplog.text


class TestConfigureVerboseLogging:
    """Tests for configure_verbose_logging() function."""

    def test_configure_verbose_logging_enables_debug(self):
        """Test configure_verbose_logging sets DEBUG level."""
        configure_verbose_logging(verbose=True)
        
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

    def test_configure_verbose_logging_disables_debug(self):
        """Test configure_verbose_logging can disable verbose mode."""
        configure_verbose_logging(verbose=False)
        
        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO

    def test_configure_verbose_logging_affects_all_loggers(self):
        """Test configure_verbose_logging updates all existing loggers."""
        # Create some loggers
        logger1 = get_logger("test1")
        logger2 = get_logger("test2")
        
        configure_verbose_logging(verbose=True)
        
        assert logger1.level == logging.DEBUG
        assert logger2.level == logging.DEBUG


class TestLogException:
    """Tests for log_exception() function."""

    def test_log_exception_logs_error(self, caplog):
        """Test log_exception logs error message."""
        logger = get_logger("test")
        
        try:
            raise ValueError("Test error")
        except ValueError:
            with caplog.at_level(logging.ERROR):
                log_exception(logger, "An error occurred")
        
        assert "An error occurred" in caplog.text

    def test_log_exception_includes_traceback(self, caplog):
        """Test log_exception includes exception traceback."""
        logger = get_logger("test")
        
        try:
            raise RuntimeError("Test runtime error")
        except RuntimeError:
            with caplog.at_level(logging.ERROR):
                log_exception(logger, "Runtime error occurred", exc_info=True)
        
        assert "Runtime error occurred" in caplog.text
        # Traceback should be included
        assert "RuntimeError" in caplog.text


class TestLogPerformance:
    """Tests for log_performance() function."""

    def test_log_performance(self, caplog):
        """Test logging performance metrics."""
        logger = get_logger("test")
        
        with caplog.at_level(logging.INFO):
            log_performance(
                logger,
                "cut_video",
                duration=5.25,
                fps=30,
                size_mb=150
            )
        
        assert "Performance" in caplog.text
        assert "cut_video" in caplog.text
        assert "5.25s" in caplog.text
        assert "fps=30" in caplog.text
        assert "size_mb=150" in caplog.text

    def test_log_performance_minimal_metrics(self, caplog):
        """Test logging performance with minimal metrics."""
        logger = get_logger("test")
        
        with caplog.at_level(logging.INFO):
            log_performance(logger, "concat", duration=2.5)
        
        assert "concat" in caplog.text
        assert "2.50s" in caplog.text


# Integration-style tests
class TestLoggerIntegration:
    """Integration tests for logger module."""

    def test_complete_logging_workflow(self, caplog):
        """Test complete logging workflow with operations."""
        logger = get_logger("integration_test")
        
        with caplog.at_level(logging.INFO):
            with log_operation("video_cut", logger, input="movie.mp4"):
                logger.info("Processing video")
                log_ffmpeg_command(
                    logger,
                    ["ffmpeg", "-i", "movie.mp4", "part1.mp4"],
                    success=True,
                    execution_time=3.5
                )
                log_performance(logger, "video_cut", duration=3.5, size_mb=100)
        
        # Verify all log messages
        assert "Starting operation: video_cut" in caplog.text
        assert "Processing video" in caplog.text
        assert "Completed operation: video_cut" in caplog.text

    def test_error_handling_workflow(self, caplog):
        """Test logging workflow with error handling."""
        logger = get_logger("error_test")
        
        with caplog.at_level(logging.ERROR):
            try:
                with log_operation("failing_operation", logger):
                    log_ffmpeg_command(
                        logger,
                        ["ffmpeg", "-i", "bad.mp4"],
                        success=False,
                        stderr="File not found"
                    )
                    raise ValueError("Operation failed")
            except ValueError:
                pass
        
        assert "FFmpeg command failed" in caplog.text
        assert "Failed operation: failing_operation" in caplog.text


# Edge cases and error conditions
class TestLoggerEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_log_operation_reentrant_safe(self):
        """Test log_operation is reentrant safe."""
        logger = get_logger("test")
        
        with log_operation("op1", logger):
            ctx1 = get_operation_context()
            with log_operation("op2", logger):
                ctx2 = get_operation_context()
                assert ctx2['operation'] == 'op2'
            ctx1_after = get_operation_context()
            assert ctx1_after['operation'] == 'op1'

    def test_empty_ffmpeg_command(self, caplog):
        """Test logging empty FFmpeg command."""
        logger = get_logger("test")
        
        with caplog.at_level(logging.DEBUG):
            log_ffmpeg_command(logger, [], success=True)
        
        # Should not crash
        assert "FFmpeg command executed" in caplog.text

    def test_log_performance_zero_duration(self, caplog):
        """Test logging performance with zero duration."""
        logger = get_logger("test")
        
        with caplog.at_level(logging.INFO):
            log_performance(logger, "instant_op", duration=0.0)
        
        assert "0.00s" in caplog.text
