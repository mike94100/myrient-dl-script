#!/usr/bin/env python3
"""
Progress utilities for myrient-dl
"""

import sys
import time
import itertools
import threading
from utils.log_utils import disable_console_logging, enable_console_logging

# Global spinner state
_spinner_state = {
    'active': False,
    'thread': None,
    'message': '',
    'bar': '',
    'progress': 0,
    'current': 0,
    'total': 0,
    'speed_str': '',
    'eta_str': '',
    'completed': False,
    'lock': threading.Lock()
}


def get_spinner_char() -> str:
    """Get next spinner character for animation"""
    spinner_chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    if not hasattr(get_spinner_char, 'spinner_cycle'):
        get_spinner_char.spinner_cycle = itertools.cycle(spinner_chars)
    return next(get_spinner_char.spinner_cycle)


def show_progress(current: int, total: int, message: str = "", width: int = 30, force: bool = False,
                 files_processed: int = None, total_files: int = None, show_spinner: bool = False) -> None:
    """Display enhanced progress bar with ETA, speed metrics, and optional continuously animated spinner"""
    if (not sys.stdout.isatty() and not force) or total == 0:
        return

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

    # Handle spinner animation
    if show_spinner:
        # Update global spinner state
        with _spinner_state['lock']:
            _spinner_state['message'] = message
            _spinner_state['bar'] = bar
            _spinner_state['progress'] = progress
            _spinner_state['current'] = current
            _spinner_state['total'] = total
            _spinner_state['speed_str'] = speed_str
            _spinner_state['eta_str'] = eta_str
            _spinner_state['completed'] = current >= total

        # Start spinner thread if not already running
        if not _spinner_state['active']:
            _spinner_state['active'] = True
            _spinner_state['thread'] = threading.Thread(target=_continuous_spinner_worker, daemon=True)
            _spinner_state['thread'].start()

        # Don't print here - the background thread handles all display updates
        return
    else:
        # Stop any active spinner
        _spinner_state['active'] = False
        if _spinner_state['thread'] and _spinner_state['thread'].is_alive():
            _spinner_state['thread'].join(timeout=0.1)

    # Format progress line (for non-spinner mode)
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


def _continuous_spinner_worker():
    """Background worker that continuously animates spinner and updates display"""
    import os

    while _spinner_state['active']:
        try:
            with _spinner_state['lock']:
                if _spinner_state['completed']:
                    # Print final line and exit
                    line = f"\r{_spinner_state['message']} [{_spinner_state['bar']}] {_spinner_state['progress']:3d}% ({_spinner_state['current']}/{_spinner_state['total']}){_spinner_state['speed_str']}{_spinner_state['eta_str']}"
                    print(line, flush=True)
                    break

                # Update display with new spinner character
                spinner_char = get_spinner_char()
                line = f"\r{_spinner_state['message']} [{_spinner_state['bar']}] {_spinner_state['progress']:3d}% ({_spinner_state['current']}/{_spinner_state['total']}){_spinner_state['speed_str']}{_spinner_state['eta_str']} {spinner_char}"

                print(line, end="", flush=True)

                # Additional flush for stubborn terminals
                try:
                    os.fsync(sys.stdout.fileno())
                except (OSError, AttributeError):
                    pass

            time.sleep(0.1)  # Update every 100ms

        except Exception:
            break

    # Clean up when done
    _spinner_state['active'] = False
    print()  # Move to next line


def clear_progress() -> None:
    """Clear progress line"""
    if sys.stdout.isatty():
        print("\r\033[K", end="", flush=True)
        # Note: Console logging is re-enabled by the caller after batch processing completes


def show_spinner(message: str = "Working", duration: float = None, stop_event=None) -> None:
    """Show animated spinner for the specified duration or indefinitely until interrupted or stop_event is set"""
    if not sys.stdout.isatty():
        print(f"{message}...")
        return

    import os

    try:
        start_time = time.time()
        while True:
            # Check if stop event is set
            if stop_event and stop_event.is_set():
                break

            spinner_char = get_spinner_char()
            line = f"\r{message} {spinner_char}"

            print(line, end="", flush=True)

            # Check duration if specified
            if duration and (time.time() - start_time) >= duration:
                break

            # Check for keyboard interrupt
            try:
                time.sleep(0.1)
            except KeyboardInterrupt:
                print(f"\r{message} interrupted")
                return

    except KeyboardInterrupt:
        print(f"\r{message} interrupted")
        return
    finally:
        print()  # Move to next line when done
