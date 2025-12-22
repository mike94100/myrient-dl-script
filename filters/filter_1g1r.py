#!/usr/bin/env python3
"""
1G1R Filter - Python implementation
Simple ROM filtering with deduplication for USA/World releases
"""

import re
from typing import List, Dict, Tuple


class Filter1G1R:
    """1G1R (One Game One ROM) filter for Myrient ROMs"""

    def __init__(self, keep_all_revisions: bool = False):
        """
        Initialize filter

        Args:
            keep_all_revisions: If True, keep all revisions instead of deduplicating
        """
        self.keep_all_revisions = keep_all_revisions

    def filter_files(self, files: List[str]) -> List[str]:
        """
        Filter list of filenames

        Args:
            files: List of filenames to filter

        Returns:
            Filtered list with excluded files prefixed with '#'
        """
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

            # Apply exclusion filters
            if self._should_exclude(filename):
                filtered.append(f"#{filename}")
                continue

            # Handle deduplication
            if self.keep_all_revisions:
                filtered.append(filename)
            else:
                self._deduplicate(filename, filtered, games, base_to_index)

        return filtered

    def _should_exclude(self, filename: str) -> bool:
        """Check if file should be excluded"""
        # Development/unreleased content
        if any(pattern in filename for pattern in [
            '(Beta', '(Demo', '(Tech Demo', '(Proto', 'Proto)', '(Sample', '(Program'
        ]):
            return True

        # Unauthorized content
        if any(pattern in filename for pattern in [
            '(Pirate', '(Unl', '(Hack'
        ]):
            return True

        # Technical files
        if '[BIOS]' in filename or '(Test Program' in filename:
            return True

        # Non-English
        if '(Ja)' in filename:
            return True

        # Must be USA, World, or English
        if not any(region in filename for region in ['(USA', '(World', '(En']):
            return True

        return False

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


def filter_apply_1g1r(files: List[str], keep_all_revisions: bool = False) -> List[str]:
    """
    Apply 1G1R filter to list of files

    Args:
        files: List of filenames
        keep_all_revisions: Keep all revisions instead of deduplicating

    Returns:
        Filtered list
    """
    filter_obj = Filter1G1R(keep_all_revisions)
    return filter_obj.filter_files(files)
