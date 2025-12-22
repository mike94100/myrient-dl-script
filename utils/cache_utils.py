#!/usr/bin/env python3
"""
Caching utilities for myrient-dl
Cache HTTP responses and metadata to avoid repeated requests
"""

import hashlib
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import urlparse


class CacheManager:
    """Manages caching of HTTP responses and metadata"""

    def __init__(self, cache_dir: Path, expiry_hours: int = 24):
        self.cache_dir = cache_dir
        self.expiry_hours = expiry_hours
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_key(self, url: str) -> str:
        """Generate a cache key from URL"""
        # Use MD5 hash of URL for filesystem-safe key
        return hashlib.md5(url.encode('utf-8')).hexdigest()

    def _get_cache_path(self, cache_key: str) -> Path:
        """Get filesystem path for cache entry"""
        return self.cache_dir / f"{cache_key}.json"

    def _is_expired(self, cache_path: Path) -> bool:
        """Check if cache entry has expired"""
        if not cache_path.exists():
            return True

        # Check file modification time
        mtime = cache_path.stat().st_mtime
        age_hours = (time.time() - mtime) / 3600
        return age_hours > self.expiry_hours

    def get(self, url: str) -> Optional[str]:
        """Get cached content for URL"""
        cache_key = self._get_cache_key(url)
        cache_path = self._get_cache_path(cache_key)

        if self._is_expired(cache_path):
            return None

        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('content')
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            return None

    def put(self, url: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Store content in cache"""
        cache_key = self._get_cache_key(url)
        cache_path = self._get_cache_path(cache_key)

        data = {
            'url': url,
            'content': content,
            'timestamp': time.time(),
            'metadata': metadata or {}
        }

        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def clear(self) -> None:
        """Clear all cache entries"""
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()

    def cleanup_expired(self) -> int:
        """Remove expired cache entries, return count removed"""
        removed = 0
        for cache_file in self.cache_dir.glob("*.json"):
            if self._is_expired(cache_file):
                cache_file.unlink()
                removed += 1
        return removed

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_files = 0
        expired_files = 0
        total_size = 0

        for cache_file in self.cache_dir.glob("*.json"):
            total_files += 1
            total_size += cache_file.stat().st_size

            if self._is_expired(cache_file):
                expired_files += 1

        return {
            'total_files': total_files,
            'expired_files': expired_files,
            'valid_files': total_files - expired_files,
            'total_size_bytes': total_size,
            'cache_dir': str(self.cache_dir)
        }


def load_config(config_file: str = 'config.toml') -> Dict[str, Any]:
    """Load configuration from config file if it exists"""
    config_path = Path(config_file)
    if not config_path.exists():
        return {}

    try:
        import tomllib
        with open(config_path, 'rb') as f:
            return tomllib.load(f)
    except ImportError:
        # Fallback for older Python versions
        try:
            import toml
            return toml.load(config_path)
        except ImportError:
            return {}
    except Exception:
        return {}


def get_config_value(config_file: str = 'config.toml', *keys: str, default=None):
    """Get nested config value"""
    config = load_config(config_file)
    current = config

    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default

    return current


def setup_cache_from_config() -> Optional[CacheManager]:
    """Create cache manager from config settings"""
    cache_enabled = get_config_value('cache', 'enabled', default=True)
    if not cache_enabled:
        return None

    cache_dir = Path(get_config_value('cache', 'directory', default='.cache'))
    expiry_hours = get_config_value('cache', 'expiry_hours', default=24)

    return CacheManager(cache_dir, expiry_hours)
