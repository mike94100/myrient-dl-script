#!/usr/bin/env python3
"""
TOML parsing utilities for myrient-dl
Requires Python 3.11+ for built-in TOML support
"""

import sys


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
