#!/usr/bin/env python3
"""
Progress utilities for myrient-dl
"""

import sys
from utils.log_utils import disable_console_logging, enable_console_logging


def show_progress(current: int, total: int, message: str = "", width: int = 30, force: bool = False,
                 files_processed: int = None, total_files: int = None) -> None:
    """Display enhanced progress bar with ETA, speed metrics, and file statistics"""
    if (not sys.stdout.isatty() and not force) or total == 0:
        return

    import time
    import os

    # Disable console logging while showing progress bar
    if current == 0:
        disable_console_logging()

    progress = current * 100 // total
    filled = progress * width // 100
    empty = width - filled

    bar = "█" * filled + "░" * empty

    # Calculate timing and speed metrics
    current_time = time.time()

    if not hasattr(show_progress, '_start_time'):
        show_progress._start_time = current_time
        show_progress._last_update = current_time
        show_progress._last_count = 0

    elapsed = current_time - show_progress._start_time

    # Calculate rates and ETA
    eta_str = ""
    speed_str = ""
    if elapsed > 0 and current > 0:
        # Overall rate (platforms/second)
        overall_rate = current / elapsed

        # Speed metrics
        if files_processed is not None and total_files is not None:
            speed_str = f" {files_processed}/{total_files} files"
        else:
            speed_str = f" {overall_rate:.1f} plat/s"

        # ETA calculation
        if current < total:
            remaining = (total - current) / overall_rate
            if remaining < 60:
                eta_str = f" ETA: {remaining:.0f}s"
            elif remaining < 3600:
                eta_str = f" ETA: {remaining/60:.1f}m"
            else:
                eta_str = f" ETA: {remaining/3600:.1f}h"

    # Format progress line
    line = f"\r{message} [{bar}] {progress:3d}% ({current}/{total}){speed_str}{eta_str}"

    # Force immediate output regardless of terminal buffering
    print(line, end="", flush=True)

    # Additional flush for stubborn terminals
    try:
        os.fsync(sys.stdout.fileno())
    except (OSError, AttributeError):
        pass  # Some terminals don't support fsync

    if current >= total:
        print()
        if hasattr(show_progress, '_start_time'):
            delattr(show_progress, '_start_time')
        if hasattr(show_progress, '_last_update'):
            delattr(show_progress, '_last_update')
        if hasattr(show_progress, '_last_count'):
            delattr(show_progress, '_last_count')
        # Note: Console logging is re-enabled by the caller after batch processing completes


def clear_progress() -> None:
    """Clear progress line"""
    if sys.stdout.isatty():
        print("\r\033[K", end="", flush=True)
        # Note: Console logging is re-enabled by the caller after batch processing completes


def show_spinner(message: str = "Working") -> None:
    """Show simple spinner"""
    print(f"{message} |", end="", flush=True)
