#!/usr/bin/env python3
"""
File size conversion utilities for myrient-dl
Convert between human-readable file sizes and bytes
"""

import re
from typing import Union, Dict


def parse_file_size(size_str: str) -> int:
    """
    Convert human-readable file size to bytes

    Handles formats:
        - With or without spaces: "56.9 KiB" or "56.9KiB"
        - With or without "B": "56.9 KiB" or "56.9 Ki"
        - SI or IEC formats: "56.9 KB" or "56.9 KiB"

    Supports prefixes: K, M, G, T, P, E, Z, Y
    Both binary (KiB) and decimal (KB) units

    Args:
        size_str: Size string

    Returns:
        Size in bytes

    Raises:
        ValueError: If size string is invalid
    """
    if not size_str or size_str == '-':
        return 0

    # Clean the string - remove spaces and convert to uppercase
    size_str = size_str.replace(' ', '').upper()

    # Strip 'B' suffix if present (handles both "KiB" and "Ki" formats)
    if size_str.endswith('B'):
        size_str = size_str[:-1]

    # Define multipliers for each prefix
    # Binary units (1024^n) - IEC format (Ki, Mi, Gi, etc.)
    binary_multipliers = {
        'YI': 1024**8, 'ZI': 1024**7, 'EI': 1024**6, 'PI': 1024**5,
        'TI': 1024**4, 'GI': 1024**3, 'MI': 1024**2, 'KI': 1024**1,
    }

    # Decimal units (1000^n) - SI format (K, M, G, etc.)
    decimal_multipliers = {
        'Y': 1000**8, 'Z': 1000**7, 'E': 1000**6, 'P': 1000**5,
        'T': 1000**4, 'G': 1000**3, 'M': 1000**2, 'K': 1000**1,
    }

    multiplier = 1

    # Check for binary units first (more specific matches)
    for unit, mult in binary_multipliers.items():
        if size_str.endswith(unit):
            multiplier = mult
            size_str = size_str[:-len(unit)]
            break

    # Then check for decimal units
    if multiplier == 1:  # Only if no binary unit was found
        for unit, mult in decimal_multipliers.items():
            if size_str.endswith(unit):
                multiplier = mult
                size_str = size_str[:-len(unit)]
                break

    try:
        # Parse the numeric value
        value = float(size_str)
        return int(value * multiplier)
    except ValueError:
        raise ValueError(f"Invalid file size format: {size_str}")


def format_file_size(size_bytes: Union[int, float], use_binary: bool = True) -> str:
    """
    Convert bytes to human-readable file size

    Formatting rules:
    - 1-2 digits: show with 1 decimal place (e.g., "56.9 KiB")
    - 3+ digits: show with no decimal (e.g., "100 KiB")

    Args:
        size_bytes: Size in bytes
        use_binary: Use binary (1024) units instead of decimal (1000)

    Returns:
        Human-readable size string
    """
    if size_bytes == 0:
        return "0 B"

    # Use binary (1024) or decimal (1000) units
    base = 1024 if use_binary else 1000
    units = ['B', 'KiB', 'MiB', 'GiB', 'TiB'] if use_binary else ['B', 'KB', 'MB', 'GB', 'TB']

    unit_index = 0
    size = float(size_bytes)

    # Find appropriate unit
    while size >= base and unit_index < len(units) - 1:
        size /= base
        unit_index += 1

    # Apply formatting rules
    if unit_index == 0:
        # Bytes - always show as integer
        return f"{int(size)} {units[unit_index]}"
    else:
        # Check if we need decimal places
        if size >= 100:
            # 3+ digits, no decimal
            return f"{int(size)} {units[unit_index]}"
        elif size >= 10:
            # 2 digits, check if we need decimal
            if size == int(size):
                return f"{int(size)} {units[unit_index]}"
            else:
                return f"{size:.1f} {units[unit_index]}"
        else:
            # 1 digit, always show decimal
            return f"{size:.1f} {units[unit_index]}"


def calculate_total_size(file_sizes: Dict[str, str]) -> int:
    """
    Calculate total size from a dictionary of file sizes

    Args:
        file_sizes: Dict mapping filename to size string

    Returns:
        Total size in bytes
    """
    total = 0
    for size_str in file_sizes.values():
        try:
            total += parse_file_size(size_str)
        except ValueError:
            # Skip invalid sizes
            pass
    return total


def format_file_size_dual(size_bytes: Union[int, float]) -> str:
    """
    Format file size in dual format: IEC (binary) and SI (decimal)

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted string like "44.8 MiB (47.0 MB)" or "Unknown" if size_bytes is 0
    """
    if size_bytes == 0:
        return "Unknown"

    iec_size = format_file_size(size_bytes, use_binary=True)   # IEC (1024-based)
    si_size = format_file_size(size_bytes, use_binary=False)   # SI (1000-based)
    return f"{iec_size} ({si_size})"
