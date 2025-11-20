"""
Logging utilities for video-tool.
Provides structured logging with rich console output and file logging.
"""

import logging
import logging.config
import yaml
import os
from pathlib import Path
from typing import Optional, Dict, Any
from contextlib import contextmanager
import threading

# Thread-local storage for operation context
_context = threading.local()


def get_config_path() -> Path:
    """Get the path to logging configuration file."""
    current_dir = Path(__file__).parent
    config_path = current_dir.parent.parent / 'configs' / 'logging.yaml'
    return config_path


def setup_logging(
    config_path: Optional[str] = None,
    verbose: bool = False,
    log_file: Optional[str] = None,
) -> None:
    """
    Setup logging configuration from YAML file.
    
    Args:
        config_path: Path to logging config YAML file (uses default if None)
        verbose: If True, set console handler to DEBUG level
        log_file: If provided, override default log file path
        
    Raises:
        FileNotFoundError: If config file not found
        yaml.YAMLError: If config file is invalid
    """
    # Get config path
    if config_path is None:
        config_path = get_config_path()
    else:
        config_path = Path(config_path)
    
    if not config_path.exists():
        # Fallback to basic logging if config not found
        logging.basicConfig(
            level=logging.DEBUG if verbose else logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        )
        logger = logging.getLogger(__name__)
        logger.warning(f"Logging config not found at {config_path}, using basic config")
        return
    
    # Load YAML config
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Ensure logs directory exists
    logs_dir = Path(__file__).parent.parent.parent / 'logs'
    logs_dir.mkdir(exist_ok=True)
    
    # Override log file path if provided
    if log_file:
        log_file_path = Path(log_file)
        # Ensure parent directory exists
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Update file handler
        if 'handlers' in config and 'file' in config['handlers']:
            config['handlers']['file']['filename'] = str(log_file_path)
    
    # Set console handler to DEBUG if verbose
    if verbose:
        if 'handlers' in config and 'console' in config['handlers']:
            config['handlers']['console']['level'] = 'DEBUG'
        # Also set all loggers to DEBUG
        if 'loggers' in config:
            for logger_config in config['loggers'].values():
                if 'level' in logger_config:
                    logger_config['level'] = 'DEBUG'
    
    # Apply configuration
    logging.config.dictConfig(config)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance.
    
    Args:
        name: Logger name (typically __name__ of the module)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


@contextmanager
def log_operation(
    operation: str,
    logger: Optional[logging.Logger] = None,
    **context
):
    """
    Context manager for logging operations with structured context.
    
    Args:
        operation: Name of the operation (e.g., "cut_video", "extract_audio")
        logger: Logger instance (uses root logger if None)
        **context: Additional context to include in logs (e.g., input_file, output_file)
        
    Usage:
        with log_operation("cut_video", logger, input_file="movie.mp4"):
            # Do operation
            pass
    """
    if logger is None:
        logger = logging.getLogger()
    
    # Store context in thread-local storage
    if not hasattr(_context, 'stack'):
        _context.stack = []
    
    _context.stack.append({
        'operation': operation,
        **context
    })
    
    # Log operation start
    context_str = ', '.join(f"{k}={v}" for k, v in context.items())
    logger.info(f"Starting operation: {operation} ({context_str})")
    
    try:
        yield
        # Log operation success
        logger.info(f"Completed operation: {operation}")
    except Exception as e:
        # Log operation failure
        logger.error(f"Failed operation: {operation} - {e}", exc_info=True)
        raise
    finally:
        # Remove context from stack
        _context.stack.pop()


def get_operation_context() -> Dict[str, Any]:
    """
    Get the current operation context from thread-local storage.
    
    Returns:
        Dictionary with current context, or empty dict if no context
    """
    if not hasattr(_context, 'stack') or not _context.stack:
        return {}
    return _context.stack[-1]


def log_ffmpeg_command(
    logger: logging.Logger,
    command: list,
    success: bool = True,
    stdout: Optional[str] = None,
    stderr: Optional[str] = None,
    execution_time: Optional[float] = None,
):
    """
    Log FFmpeg command execution.
    
    Args:
        logger: Logger instance
        command: FFmpeg command as list of strings
        success: Whether command succeeded
        stdout: Command stdout output
        stderr: Command stderr output
        execution_time: Execution time in seconds
    """
    command_str = ' '.join(command)
    
    if success:
        logger.debug(f"FFmpeg command executed: {command_str}")
        if execution_time:
            logger.debug(f"Execution time: {execution_time:.2f}s")
    else:
        logger.error(f"FFmpeg command failed: {command_str}")
    
    if stderr and logger.isEnabledFor(logging.DEBUG):
        # Log stderr at debug level (can be verbose)
        logger.debug(f"FFmpeg stderr: {stderr[:500]}...")  # First 500 chars
    
    if not success and stderr:
        # Log full stderr for errors
        logger.error(f"FFmpeg error output: {stderr}")


def log_file_operation(
    logger: logging.Logger,
    operation: str,
    input_files: list,
    output_file: Optional[str] = None,
    **kwargs
):
    """
    Log file-based operations with input/output details.
    
    Args:
        logger: Logger instance
        operation: Operation name (e.g., "cut", "concat", "extract")
        input_files: List of input file paths
        output_file: Output file path
        **kwargs: Additional context
    """
    logger.info(
        f"{operation.capitalize()} operation",
        extra={
            'operation': operation,
            'input_files': input_files,
            'output_file': output_file,
            **kwargs
        }
    )


class LoggerAdapter(logging.LoggerAdapter):
    """
    Logger adapter that adds structured context to all log messages.
    
    Usage:
        adapter = LoggerAdapter(logger, {'operation': 'cut_video'})
        adapter.info("Starting cut")  # Will include operation in log
    """
    
    def process(self, msg, kwargs):
        """Add extra context to log messages."""
        # Get operation context
        context = get_operation_context()
        
        # Merge with provided extra
        if 'extra' not in kwargs:
            kwargs['extra'] = {}
        kwargs['extra'].update(context)
        
        return msg, kwargs


def configure_verbose_logging(verbose: bool = True):
    """
    Dynamically adjust logging level for verbose mode.
    
    Args:
        verbose: If True, set all loggers to DEBUG level
    """
    level = logging.DEBUG if verbose else logging.INFO
    
    # Update root logger
    logging.getLogger().setLevel(level)
    
    # Update all existing loggers
    for name in logging.Logger.manager.loggerDict:
        logger = logging.getLogger(name)
        logger.setLevel(level)
    
    # Update console handler if it exists
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        if isinstance(handler, logging.StreamHandler):
            # Check if handler has stream with name attribute
            if hasattr(handler.stream, 'name') and handler.stream.name == '<stderr>':
                handler.setLevel(level)


def log_exception(logger: logging.Logger, message: str, exc_info: bool = True):
    """
    Log an exception with full traceback.
    
    Args:
        logger: Logger instance
        message: Error message
        exc_info: Whether to include exception info (default: True)
    """
    logger.error(message, exc_info=exc_info)


def log_performance(
    logger: logging.Logger,
    operation: str,
    duration: float,
    **metrics
):
    """
    Log performance metrics for an operation.
    
    Args:
        logger: Logger instance
        operation: Operation name
        duration: Duration in seconds
        **metrics: Additional performance metrics
    """
    metrics_str = ', '.join(f"{k}={v}" for k, v in metrics.items())
    logger.info(
        f"Performance: {operation} completed in {duration:.2f}s ({metrics_str})",
        extra={
            'operation': operation,
            'duration': duration,
            **metrics
        }
    )


# Initialize logging on module import (with default config)
try:
    setup_logging()
except Exception as e:
    # Fallback to basic logging if setup fails
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    )
    logging.getLogger(__name__).warning(f"Failed to setup logging: {e}")
