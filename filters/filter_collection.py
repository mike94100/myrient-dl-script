#!/usr/bin/env python3
"""
Collection-based Filter - Python implementation
Filtering and URL generation based on collection.toml configuration
"""

import re
from typing import List, Dict, Any, Optional
from urllib.parse import unquote
import toml


class CollectionFilter:
    """Filter for Myrient ROMs based on collection.toml configuration"""

    def __init__(self, collection_path: str):
        """
        Initialize filter from collection.toml

        Args:
            collection_path: Path to collection.toml file
        """
        with open(collection_path, 'r', encoding='utf-8') as f:
            self.config = toml.load(f)

        self.global_filters = self.config.get('filters', {})
        self.platforms = self.config.get('platforms', {})

    def get_platform_config(self, platform_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific platform"""
        return self.platforms.get(platform_name)

    def get_platform_filters(self, platform_name: str) -> Dict[str, Any]:
        """Get merged filters for a platform (global + platform overrides)"""
        platform_config = self.get_platform_config(platform_name)
        if not platform_config:
            return self.global_filters.copy()

        # Start with global filters
        filters = self.global_filters.copy()

        # Override with platform-specific filters
        for key in ['include', 'exclude', 'deduplicate']:
            if key in platform_config:
                filters[key] = platform_config[key]

        return filters

    def should_skip_filtering(self, platform_name: str) -> bool:
        """Check if filtering should be skipped for this platform"""
        platform_config = self.get_platform_config(platform_name)
        return platform_config.get('skip_filtering', False) if platform_config else False

    def filter_files(self, platform_name: str, files: List[str]) -> List[str]:
        """
        Filter list of filenames for a specific platform

        Args:
            platform_name: Name of the platform
            files: List of filenames to filter

        Returns:
            Filtered list with excluded files prefixed with '#'
        """
        if self.should_skip_filtering(platform_name):
            return files  # Return all files unfiltered

        filters = self.get_platform_filters(platform_name)

        filtered = []
        seen = set()
        games = {}  # base_name -> {'filename': str, 'version': str}
        base_to_index = {}  # base_name -> index in filtered list

        for filename in files:
            # Skip already excluded files
            if filename.startswith('#'):
                filtered.append(filename)
                continue

            # Exact deduplication
            if filename in seen:
                continue
            seen.add(filename)

            # Apply inclusion/exclusion filters
            if not self._should_include(filename, filters):
                filtered.append(f"#{filename}")
                continue

            # Handle deduplication
            if not filters.get('deduplicate', True):
                filtered.append(filename)
            else:
                self._deduplicate(filename, filtered, games, base_to_index)

        return filtered

    def _should_include(self, filename: str, filters: Dict[str, Any]) -> bool:
        """Check if file should be included based on filters"""
        include_patterns = filters.get('include', [])
        exclude_patterns = filters.get('exclude', [])

        # Check exclusions first
        for pattern in exclude_patterns:
            if pattern in filename:
                return False

        # If include patterns specified, must match at least one
        if include_patterns:
            for pattern in include_patterns:
                if pattern in filename:
                    return True
            return False  # No include pattern matched

        return True  # No include patterns = include all

    def _deduplicate(self, filename: str, filtered: List[str],
                            games: Dict[str, Dict], base_to_index: Dict[str, int]) -> None:
        """Handle deduplication logic"""
        base_name = self._extract_base_name(filename)

        if base_name in games:
            # Compare versions
            existing_version = games[base_name]['version']
            current_version = self._extract_version(filename)

            if self._is_better_version(current_version, existing_version):
                # This version is better - exclude old one
                old_index = base_to_index[base_name]
                filtered[old_index] = f"#{filtered[old_index]}"
                games[base_name] = {'filename': filename, 'version': current_version}
                base_to_index[base_name] = len(filtered)
                filtered.append(filename)
            else:
                # This version is worse - exclude it
                filtered.append(f"#{filename}")
        else:
            # First occurrence
            games[base_name] = {'filename': filename, 'version': self._extract_version(filename)}
            base_to_index[base_name] = len(filtered)
            filtered.append(filename)

    def _extract_base_name(self, filename: str) -> str:
        """Extract base game name (everything before first parenthesis)"""
        # Remove file extension
        filename = re.sub(r'\.[^.]+$', '', filename)

        # Extract everything before first parenthesis
        match = re.search(r'\s*\(', filename)
        if match:
            filename = filename[:match.start()]

        # Clean up spaces
        return ' '.join(filename.split()).strip()

    def _extract_version(self, filename: str) -> str:
        """Extract version info for comparison"""
        # Rev versions
        match = re.search(r'\(Rev (\d+)\)', filename)
        if match:
            return f"rev{match.group(1)}"

        # v versions
        match = re.search(r'\(v([\d.]+)\)', filename)
        if match:
            return f"v{match.group(1)}"

        return ""  # No version = lowest priority

    def _is_better_version(self, new_ver: str, old_ver: str) -> bool:
        """Compare two versions, return True if new_ver is better"""
        # Empty version is worse than any version
        if old_ver == "":
            return True
        if new_ver == "":
            return False

        # Rev versions are better than v versions
        if new_ver.startswith('rev') and old_ver.startswith('v'):
            return True
        if new_ver.startswith('v') and old_ver.startswith('rev'):
            return False

        # Compare same type versions
        if new_ver.startswith('rev') and old_ver.startswith('rev'):
            return int(new_ver[3:]) > int(old_ver[3:])
        if new_ver.startswith('v') and old_ver.startswith('v'):
            return new_ver > old_ver

        return False


def filter_collection_apply(collection_path: str, platform_name: str, files: List[str]) -> List[str]:
    """
    Apply collection-based filter to list of files

    Args:
        collection_path: Path to collection.toml
        platform_name: Name of the platform
        files: List of filenames

    Returns:
        Filtered list
    """
    filter_obj = CollectionFilter(collection_path)
    return filter_obj.filter_files(platform_name, files)


def get_platform_url(collection_path: str, platform_name: str) -> Optional[str]:
    """Get the URL for a platform from collection.toml"""
    filter_obj = CollectionFilter(collection_path)
    platform_config = filter_obj.get_platform_config(platform_name)
    return platform_config.get('url') if platform_config else None


def get_platform_directory(collection_path: str, platform_name: str) -> Optional[str]:
    """Get the directory for a platform from collection.toml"""
    filter_obj = CollectionFilter(collection_path)
    platform_config = filter_obj.get_platform_config(platform_name)
    return platform_config.get('directory') if platform_config else None


def get_all_platforms(collection_path: str) -> List[str]:
    """Get list of all platform names from collection.toml"""
    filter_obj = CollectionFilter(collection_path)
    return list(filter_obj.platforms.keys())
