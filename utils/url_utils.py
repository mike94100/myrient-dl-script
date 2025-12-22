#!/usr/bin/env python3
"""
URL encoding/decoding utilities for myrient-dl
Pure Python implementation compatible with urllib.parse
"""

import html
import re
from urllib.parse import quote, unquote

def validate_directory_path(path):
    """
    Validate and format directory path for Myrient URLs

    Args:
        path (str): Directory path to validate

    Returns:
        str: Formatted path starting and ending with /

    Raises:
        ValueError: If path is invalid
    """
    if not path:
        raise ValueError("Directory path missing")

    # Check if it looks like a URL or hostname
    if "://" in path or re.match(r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', path):
        raise ValueError(f"Directory path cannot be a host or URL: {path}")

    # Check if file (has an extension)
    if re.search(r'\.[a-zA-Z0-9]+$', path):
        raise ValueError(f"Directory path cannot be a file: {path}")

    # Ensure path starts and ends with slash "/path/"
    if not path.startswith('/'):
        path = '/' + path
    if not path.endswith('/'):
        path = path + '/'

    return path


def construct_url(base_url, path_directory, filename=None):
    """
    Construct a full URL for Myrient (directory or file download)

    Args:
        base_url (str): Base Myrient URL
        path_directory (str): Directory path
        filename (str, optional): Filename to download. If None, returns directory URL

    Returns:
        str: Full URL
    """
    # Ensure base_url doesn't end with /
    base_url = base_url.rstrip('/')

    # Ensure path_directory starts and ends with /
    path_directory = validate_directory_path(path_directory)

    # Construct full path
    if filename:
        # Decode HTML entities first, then construct path
        decoded_filename = html.unescape(filename)
        full_path = path_directory + decoded_filename
    else:
        full_path = path_directory

    # URL encode the path
    encoded_path = quote(full_path, safe='/')

    return f"{base_url}{encoded_path}"
