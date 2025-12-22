#!/usr/bin/env python3
"""
Progress utilities for myrient-dl
"""

import sys
from utils.log_utils import disable_console_logging, enable_console_logging


def show_progress(current: int, total: int, message: str = "", width: int = 30, force: bool = False) -> None:
    """Display enhanced progress bar with ETA"""
    if (not sys.stdout.isatty() and not force) or total == 0:
        return

    import time

    # Disable console logging while showing progress bar
    if current == 0:
        disable_console_logging()

    progress = current * 100 // total
    filled = progress * width // 100
    empty = width - filled

    bar = "█" * filled + "░" * empty

    # Calculate ETA if possible
    eta_str = ""
    if hasattr(show_progress, '_start_time') and current > 0:
        elapsed = time.time() - show_progress._start_time
        rate = current / elapsed
        remaining = (total - current) / rate
        eta_str = f" ETA: {remaining:.0f}s"
    elif current == 0:
        show_progress._start_time = time.time()

    line = f"\r{message} [{bar}] {progress:3d}% ({current}/{total}){eta_str}"
    print(line, end="", flush=True)

    if current >= total:
        print()
        if hasattr(show_progress, '_start_time'):
            delattr(show_progress, '_start_time')
        # Note: Console logging is re-enabled by the caller after batch processing completes


def clear_progress() -> None:
    """Clear progress line"""
    if sys.stdout.isatty():
        print("\r\033[K", end="", flush=True)
        # Note: Console logging is re-enabled by the caller after batch processing completes


def show_spinner(message: str = "Working") -> None:
    """Show simple spinner"""
    print(f"{message} |", end="", flush=True)
