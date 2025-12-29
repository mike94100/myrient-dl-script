#!/usr/bin/env python3
"""
File parsing utilities for myrient-dl
Handles parsing various file formats and content
"""

import re
from pathlib import Path
from typing import List, Dict, Any
from urllib.parse import unquote


def parse_url_file_content(url_file: Path) -> tuple[List[str], List[str]]:
    """Parse URL file and return (included_files, excluded_files)"""
    included_files = []
    excluded_files = []

    try:
        with open(url_file, 'r', encoding='utf-8') as f:
            url_lines = [line.strip() for line in f if line.strip()]
    except Exception as e:
        from utils.log_utils import get_logger
        logger = get_logger()
        logger.error(f"Failed to read URL file {url_file}: {e}")
        return [], []

    for url_line in url_lines:
        if url_line.startswith('#'):
            # Excluded file - extract filename from commented URL
            if url_line.startswith('#http'):
                url_part = url_line[1:]  # Remove # prefix
                filename = url_part.split('/')[-1]
                if filename:
                    excluded_files.append(filename)
        else:
            # Included file - extract filename from URL
            if url_line.startswith('http'):
                filename = url_line.split('/')[-1]
                if filename:
                    included_files.append(filename)

    return included_files, excluded_files


def parse_game_info(filename: str) -> tuple:
    """Parse game name and tags from filename"""
    # Remove extension
    name = re.sub(r'\.[^.]+$', '', filename)

    # Extract game name (everything before first parenthesis)
    game_name = name
    paren_match = re.search(r'\s*\(', name)
    if paren_match:
        game_name = name[:paren_match.start()].strip()

    # Extract tags (everything in parentheses) - preserve individual groups
    tags_match = re.findall(r'\([^)]+\)', name)
    tags = ' '.join(tags_match)

    return game_name, tags


def write_readme_file(toml_file: Path, readme_content: str) -> None:
    """Write README content to file with consistent encoding and logging"""
    readme_file = toml_file.parent / "README.md"
    readme_file.write_text(readme_content, encoding='utf-8')
    from utils.log_utils import get_logger
    logger = get_logger()
    logger.info(f"Generated {readme_file}")


def organize_files_by_game(decoded_files: List[str], file_sizes: Dict[str, str]) -> Dict[str, List[Dict]]:
    """Group files by game name and return structured data"""
    # Create a mapping from decoded filenames back to original encoded filenames
    decoded_to_encoded = {unquote(f): f for f in decoded_files}

    # Group files by game name for better organization
    game_groups = {}
    for decoded_filename in decoded_files:
        encoded_filename = decoded_to_encoded.get(decoded_filename, decoded_filename)
        game_name, tags = parse_game_info(decoded_filename)
        size_bytes = 0
        size_str = file_sizes.get(decoded_filename, 'Unknown')

        # Try to parse size for sorting/grouping
        try:
            from utils.file_size_utils import parse_file_size
            if size_str != 'Unknown' and size_str != '-':
                size_bytes = parse_file_size(size_str)
        except:
            pass

        if game_name not in game_groups:
            game_groups[game_name] = []
        game_groups[game_name].append({
            'filename': encoded_filename,  # Use encoded for display
            'decoded_filename': decoded_filename,  # Use decoded for lookup
            'tags': tags,
            'size': size_str,
            'size_bytes': size_bytes
        })

    return game_groups


def build_platform_data_structure(platform_name: str, included_files: List[str],
                                excluded_files: List[str], game_groups: Dict[str, List[Dict]],
                                total_bytes: int, source_url: str) -> Dict[str, Any]:
    """Assemble final platform data structure"""
    return {
        'platform_name': platform_name,
        'included_files': included_files,
        'excluded_files': excluded_files,
        'game_groups': game_groups,
        'total_files': len(included_files),
        'total_bytes': total_bytes,
        'source_url': source_url
    }
