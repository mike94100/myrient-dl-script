#!/usr/bin/env python3
"""
TOML parsing utilities for myrient-dl
Requires Python 3.11+ for built-in TOML support
"""

import sys
from typing import List


# Require Python 3.11+
if sys.version_info < (3, 11):
    raise RuntimeError("Python 3.11+ required for built-in TOML support")

import tomllib


def parse_toml_file(file_path):
    """
    Parse a TOML file and return a dictionary

    Args:
        file_path (str): Path to the TOML file

    Returns:
        dict: Parsed TOML data

    Raises:
        FileNotFoundError: If the file doesn't exist
        Exception: If TOML parsing fails
    """
    try:
        with open(file_path, "rb") as f:
            return tomllib.load(f)
    except Exception as e:
        raise Exception(f"Failed to parse TOML file '{file_path}': {e}")


def write_toml_file(file_path, data):
    """
    Write data to a TOML file

    Args:
        file_path (str): Path to write the TOML file
        data (dict): Data to write

    Note: This is a basic implementation. For complex TOML writing,
    consider using a dedicated library like tomli-w
    """
    def _write_value(f, key, value, indent=0):
        indent_str = "    " * indent

        if isinstance(value, dict):
            f.write(f"{indent_str}{key} = {{\n")
            for k, v in value.items():
                _write_value(f, k, v, indent + 1)
            f.write(f"{indent_str}}}\n")
        elif isinstance(value, list):
            f.write(f"{indent_str}{key} = [\n")
            for item in value:
                if isinstance(item, str):
                    f.write(f'{indent_str}    "{item}",\n')
                else:
                    f.write(f"{indent_str}    {item},\n")
            f.write(f"{indent_str}]\n")
        elif isinstance(value, str):
            f.write(f'{indent_str}{key} = "{value}"\n')
        else:
            f.write(f"{indent_str}{key} = {value}\n")

    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            for key, value in data.items():
                _write_value(f, key, value)
                f.write("\n")

    except Exception as e:
        raise Exception(f"Failed to write TOML file '{file_path}': {e}")


def get_config_value(config, key, default=None):
    """
    Get a value from config with optional default

    Args:
        config (dict): Configuration dictionary
        key (str): Key to retrieve
        default: Default value if key not found

    Returns:
        Value from config or default
    """
    return config.get(key, default)


def filter_valid_files(files: list) -> list:
    """
    Filter out commented files (starting with #) and return valid files list

    Args:
        files: List of file names

    Returns:
        List of valid (non-commented) file names
    """
    return [f for f in files if not f.startswith('#')]


def parse_platforms_from_config(config: dict) -> dict:
    """
    Parse platforms from collection TOML config (roms/bios sections)

    Args:
        config: Parsed TOML configuration dictionary

    Returns:
        Dictionary mapping platform names to platform configurations
    """
    platforms = {}

    # Process ROMs section
    if 'roms' in config:
        for name, platform_config in config['roms'].items():
            platforms[name] = {
                'type': 'roms',
                'name': name,
                **platform_config
            }

    # Process BIOS section
    if 'bios' in config:
        for name, platform_config in config['bios'].items():
            platforms[name] = {
                'type': 'bios',
                'name': name,
                **platform_config
            }

    return platforms


def parse_platforms_from_file(file_path) -> dict:
    """
    Parse platforms from collection TOML file (convenience wrapper)

    Args:
        file_path: Path to TOML file (string or Path object)

    Returns:
        Dictionary mapping platform names to platform configurations
    """
    config = parse_toml_file(str(file_path))
    return parse_platforms_from_config(config)


def discover_and_organize_platforms(collection_path: str) -> tuple[List[str], List[str]]:
    """Discover platforms and separate filter from nofilter platforms"""
    from filters.filter_collection import CollectionFilter, get_all_platforms

    filter_obj = CollectionFilter(collection_path)
    all_platforms = get_all_platforms(collection_path)

    nofilter_platforms = []
    filter_platforms = []

    for platform_name in all_platforms:
        if filter_obj.should_skip_filtering(platform_name):
            nofilter_platforms.append(platform_name)
        else:
            filter_platforms.append(platform_name)

    return filter_platforms, nofilter_platforms


def get_url_file_path(collection_path: str, platform_name: str):
    """Get the URL file path for a platform from its urllist configuration"""
    from filters.filter_collection import CollectionFilter
    from pathlib import Path

    filter_obj = CollectionFilter(collection_path)
    platform_config = filter_obj.get_platform_config(platform_name)
    if not platform_config or 'urllist' not in platform_config:
        raise ValueError(f"Platform {platform_name} is missing required 'urllist' field")
    return Path(platform_config['urllist'])
