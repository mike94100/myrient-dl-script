#!/usr/bin/env python3
"""
Logging utilities for myrient-dl
Uses Python's built-in logging module
"""

import logging
import sys
from pathlib import Path


def init_logger(log_file=None, verbose=True, level=logging.INFO):
    """
    Initialize logging for myrient-dl

    Args:
        log_file (str, optional): Path to log file
        verbose (bool): Whether to print to console
        level: Logging level (default: INFO)

    Returns:
        logging.Logger: Configured logger
    """
    # Create logger
    logger = logging.getLogger('myrient-dl')
    logger.setLevel(level)

    # Clear any existing handlers
    logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler - stored as attribute so we can disable/enable it
    if verbose:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        logger.console_handler = console_handler
    else:
        logger.console_handler = None

    # File handler
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Clear log file
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write("")

        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.file_handler = file_handler
    else:
        logger.file_handler = None

    return logger


def get_logger():
    """Get the myrient-dl logger"""
    return logging.getLogger('myrient-dl')


def disable_console_logging():
    """Temporarily disable console logging (useful during progress bars)"""
    logger = get_logger()
    if hasattr(logger, 'console_handler') and logger.console_handler:
        logger.removeHandler(logger.console_handler)


def enable_console_logging():
    """Re-enable console logging after it was disabled"""
    logger = get_logger()
    if hasattr(logger, 'console_handler') and logger.console_handler and logger.console_handler not in logger.handlers:
        logger.addHandler(logger.console_handler)


# Custom success level
SUCCESS_LEVEL = 25
logging.addLevelName(SUCCESS_LEVEL, 'SUCCESS')


def success(self, message, *args, **kwargs):
    """Log success message"""
    if self.isEnabledFor(SUCCESS_LEVEL):
        self._log(SUCCESS_LEVEL, message, args, **kwargs)


# Add success method to Logger class
logging.Logger.success = success
