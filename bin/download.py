#!/usr/bin/env python3
"""
ROM Collection Downloader
Downloads ROM files based on JSON configuration
"""

import argparse
import json
import os
import sys
import asyncio
import aiohttp
from pathlib import Path
from urllib.parse import urlparse

class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color

class Logger:
    def __init__(self, quiet=False):
        self.quiet = quiet

    def error(self, message):
        print(f"{Colors.RED}ERROR:{Colors.NC} {message}", file=sys.stderr)

    def warn(self, message):
        print(f"{Colors.YELLOW}WARNING:{Colors.NC} {message}", file=sys.stderr)

    def info(self, message):
        if not self.quiet:
            print(f"{Colors.BLUE}INFO:{Colors.NC} {message}")

    def success(self, message):
        if not self.quiet:
            print(f"{Colors.GREEN}SUCCESS:{Colors.NC} {message}")

async def download_file(session, url, output_path, logger, semaphore):
    """Download a single file asynchronously"""
    async with semaphore:
        try:
            filename = os.path.basename(urlparse(url).path)
            logger.info(f"Downloading: {filename}")

            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                response.raise_for_status()

                with open(output_path, 'wb') as f:
                    async for chunk in response.content.iter_chunked(8192):
                        f.write(chunk)

            logger.success(f"Downloaded: {filename}")
            return True
        except Exception as e:
            logger.error(f"Failed to download {url}: {e}")
            return False

async def process_platform_async(platform_key, platform_data, output_dir, dry_run, logger, max_concurrent):
    """Process downloads for a single platform asynchronously"""
    platform_title = platform_data.get('title', platform_key)
    platform_dir = platform_data.get('directory', platform_key)
    urls = platform_data.get('urls', [])

    logger.info(f"Processing platform: {platform_title}")

    # Create platform directory
    full_platform_dir = Path(output_dir) / platform_dir
    if not dry_run:
        full_platform_dir.mkdir(parents=True, exist_ok=True)

    if not urls:
        logger.warn(f"No URLs found for platform: {platform_title}")
        return 0, 0

    download_count = 0
    error_count = 0

    if dry_run:
        for url in urls:
            if url:
                filename = os.path.basename(urlparse(url).path)
                output_file = full_platform_dir / filename
                print(f"Would download: {url} -> {output_file}")
        download_count = len([u for u in urls if u])
    else:
        # Download files asynchronously
        semaphore = asyncio.Semaphore(max_concurrent)
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; ROM Downloader)'
        }

        async with aiohttp.ClientSession(headers=headers) as session:
            tasks = []
            for url in urls:
                if url:
                    filename = os.path.basename(urlparse(url).path)
                    output_file = full_platform_dir / filename
                    tasks.append(download_file(session, url, output_file, logger, semaphore))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Download failed with exception: {result}")
                    error_count += 1
                elif result:
                    download_count += 1
                else:
                    error_count += 1

    return download_count, error_count

def main():
    parser = argparse.ArgumentParser(description="ROM Collection Downloader")
    parser.add_argument('json_file', help='Path to JSON configuration file')
    parser.add_argument('-o', '--output', help='Output directory (default: ~/Downloads)')
    parser.add_argument('-d', '--dry-run', action='store_true', help='Show what would be downloaded without downloading')
    parser.add_argument('-q', '--quiet', action='store_true', help='Suppress informational output')
    parser.add_argument('-c', '--concurrency', type=int, default=4, help='Maximum concurrent downloads (default: 4)')

    args = parser.parse_args()

    logger = Logger(quiet=args.quiet)

    # Validate JSON file
    json_path = Path(args.json_file)
    if not json_path.exists():
        logger.error(f"JSON file not found: {args.json_file}")
        return 1

    # Load and validate JSON
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON file: {e}")
        return 1

    if 'platforms' not in data:
        logger.error("Invalid JSON format: missing 'platforms' key")
        return 1

    # Set output directory
    output_dir = Path(args.output) if args.output else Path.home() / 'Downloads'
    if not args.dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)

    # Display collection info
    title = data.get('title', 'ROM Collection')
    description = data.get('description', '')

    logger.info(f"Processing collection: {title}")
    if description:
        logger.info(f"Description: {description}")

    # Count total files
    total_files = sum(len(platform.get('urls', [])) for platform in data['platforms'].values()
                     if platform.get('urls'))
    logger.info(f"Total files to process: {total_files}")

    if args.dry_run:
        logger.info("DRY RUN MODE - No files will be downloaded")

    # Process platforms asynchronously
    async def run_downloads():
        total_downloaded = 0
        total_errors = 0

        for platform_key, platform_data in data['platforms'].items():
            downloaded, errors = await process_platform_async(
                platform_key, platform_data, output_dir,
                args.dry_run, logger, args.concurrency
            )
            total_downloaded += downloaded
            total_errors += errors

        return total_downloaded, total_errors

    # Run async downloads
    total_downloaded, total_errors = asyncio.run(run_downloads())

    # Summary
    if args.dry_run:
        logger.info(f"Dry run complete. Would download {total_files} files.")
    else:
        logger.success("Download complete!")
        logger.info(f"Downloaded: {total_downloaded} files")
        if total_errors > 0:
            logger.warn(f"Errors: {total_errors} files failed")

    logger.info(f"Files saved to: {output_dir}")

    return 0 if total_errors == 0 else 1

if __name__ == '__main__':
    sys.exit(main())
