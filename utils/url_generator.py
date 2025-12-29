#!/usr/bin/env python3
"""
Myrient URL Generator
Generate URL files from collection.toml configuration by scraping Myrient pages
"""

import asyncio
import logging
from pathlib import Path
from typing import List
from urllib.parse import quote

# Import utilities
from utils import wget_install
from utils.log_utils import get_logger, disable_console_logging, enable_console_logging
from utils.wget_utils import wget_check
from utils.progress_utils import show_progress, clear_progress
from utils.cache_utils import setup_cache_from_config
from utils.toml_utils import discover_and_organize_platforms, get_url_file_path
from filters.filter_collection import CollectionFilter


async def scrape_platform_html(url: str, cache_manager=None, session=None) -> str:
    """Scrape HTML content from a platform URL with caching using aiohttp"""
    import aiohttp

    # Check cache first
    if cache_manager:
        cached_content = cache_manager.get(url)
        if cached_content:
            return cached_content

    if session is None:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={'User-Agent': 'Mozilla/5.0 (compatible; MyrientDL/1.0)'}
        ) as session:
            return await scrape_platform_html(url, cache_manager, session)

    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
            response.raise_for_status()
            html = await response.text()

            # Cache the result
            if cache_manager and html:
                cache_manager.put(url, html)

            return html
    except Exception as e:
        raise Exception(f"Failed to scrape HTML from {url}: {e}")


def scrape_zip_filenames(html: str) -> list:
    """Scrape .zip filenames from Myrient HTML directory listing using BeautifulSoup"""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, 'html.parser')
    seen = set()
    files = []

    # Find all links with href ending in .zip
    for link in soup.find_all('a', href=lambda href: href and href.endswith('.zip')):
        filename = link.get_text().strip()
        if filename and filename not in seen:
            files.append(filename)
            seen.add(filename)

    return sorted(files)


def generate_urls_from_files(files: List[str], base_url: str) -> List[str]:
    """Generate full URLs from filtered files and base URL with proper encoding"""
    urls = []
    for filename in files:
        # Remove the # prefix for URL generation if present
        clean_filename = filename.lstrip('#')
        # URL encode the filename and append to the directory URL
        encoded_filename = quote(clean_filename)
        full_url = base_url.rstrip('/') + '/' + encoded_filename
        # Keep the # prefix for excluded files
        if filename.startswith('#'):
            full_url = '#' + full_url
        urls.append(full_url)
    return urls


def write_url_file(urls: List[str], file_path: Path) -> None:
    """Write URL list to file with optimized I/O"""
    # Use buffered writing for better performance
    import io
    with io.open(file_path, 'w', encoding='utf-8', buffering=8192) as f:
        # Write all URLs at once with trailing newline
        f.write('\n'.join(urls))
        f.write('\n')


async def process_platforms_async(collection_path: str, platforms: List[str], cache_manager=None) -> int:
    """
    Process multiple platforms asynchronously with true concurrency
    """
    import aiohttp
    import asyncio

    logger = get_logger()

    # Get rate limiting settings from config (if available)
    try:
        from utils.cache_utils import get_config_value, load_config
        config = load_config()
        request_delay = get_config_value('scraping', 'request_delay', default=1.0)
        max_concurrent = get_config_value('generation', 'max_parallel_workers', default=min(4, len(platforms)))
    except:
        request_delay = 1.0
        max_concurrent = min(4, len(platforms))

    logger.info(f"Processing {len(platforms)} platforms with {max_concurrent} concurrent requests...")

    # Create semaphore to limit concurrent requests
    semaphore = asyncio.Semaphore(max_concurrent)

    # Disable console logging during parallel processing to show progress cleanly
    disable_console_logging()

    try:
        completed = 0
        success_count = 0
        last_progress_update = 0

        async def process_single_platform(platform_name: str, session) -> tuple[str, bool, str]:
            """Process a single platform with semaphore limiting"""
            async with semaphore:
                try:
                    # Add rate limiting delay
                    await asyncio.sleep(request_delay)

                    success = await generate_platform_urls(collection_path, platform_name, cache_manager, session)
                    return platform_name, success, ""
                except Exception as e:
                    return platform_name, False, str(e)

        async def update_progress():
            """Update progress bar, throttled to avoid spam"""
            nonlocal last_progress_update
            current_time = asyncio.get_event_loop().time()
            # Only update progress every 100ms to avoid spam
            if current_time - last_progress_update >= 0.1:
                show_progress(completed, len(platforms), "Generating URL files", force=True)
                last_progress_update = current_time

        async def progress_callback(task):
            """Update progress when a platform completes"""
            nonlocal completed
            completed += 1
            await update_progress()

        # Create HTTP session for connection pooling
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={'User-Agent': 'Mozilla/5.0 (compatible; MyrientDL/1.0)'}
        ) as session:

            # Create tasks for all platforms
            tasks = []
            for platform_name in platforms:
                task = asyncio.create_task(process_single_platform(platform_name, session))
                task.add_done_callback(lambda t: asyncio.create_task(progress_callback(t)))
                tasks.append(task)

            # Wait for all tasks to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Task failed with exception: {result}")
                    continue

                platform_name, success, error = result
                if success:
                    success_count += 1
                else:
                    logger.error(f"✗ Error processing {platform_name}: {error}")

        clear_progress()
        return success_count

    finally:
        enable_console_logging()


async def generate_platform_urls(collection_path: str, platform_name: str, cache_manager=None, session=None) -> bool:
    """
    Generate URL file for a single platform from collection.toml
    """
    logger = get_logger()

    try:
        filter_obj = CollectionFilter(collection_path)
        platform_config = filter_obj.get_platform_config(platform_name)

        if not platform_config:
            logger.error(f"Platform {platform_name} not found in collection")
            return False

        url = platform_config.get('url')
        if not url:
            logger.error(f"No URL specified for platform {platform_name}")
            return False

        directory = platform_config.get('directory')
        if not directory:
            logger.error(f"No directory specified for platform {platform_name}")
            return False

        logger.info(f"[{platform_name}] Processing platform...")

        # Scrape the URL (with caching)
        logger.info(f"[{platform_name}] Scraping: {url}")
        html = await scrape_platform_html(url, cache_manager, session)

        # Extract files
        files = scrape_zip_filenames(html)
        if not files:
            logger.error(f"[{platform_name}] No .zip files found on page")
            return False

        logger.info(f"[{platform_name}] Found {len(files)} files")

        # Apply filtering
        filtered_files = filter_obj.filter_files(platform_name, files)

        # Count included files
        included_files = [f for f in filtered_files if not f.startswith('#')]
        excluded_files = [f for f in filtered_files if f.startswith('#')]
        logger.info(f"[{platform_name}] Filter results: {len(included_files)} included, {len(excluded_files)} excluded")

        # Generate full URLs
        urls = generate_urls_from_files(filtered_files, url)

        # Write URL file
        url_file = get_url_file_path(collection_path, platform_name)
        write_url_file(urls, url_file)

        logger.info(f"[{platform_name}] Generated {url_file} with {len(urls)} URLs")
        return True

    except Exception as e:
        logger.error(f"Failed to generate URLs for {platform_name}: {e}")
        return False


async def generate_collection_urls_async(collection_path: str, cache_manager=None, dry_run: bool = False) -> bool:
    """
    Generate URL files for all platforms in collection.toml
    """
    logger = get_logger()

    try:
        # Discover and organize platforms
        filter_platforms, nofilter_platforms = discover_and_organize_platforms(collection_path)

        total_platforms = len(filter_platforms) + len(nofilter_platforms)

        if dry_run:
            logger.info(f"DRY RUN: Would generate URLs for {total_platforms} platforms from collection")
            return True

        logger.info(f"Generating URLs for {total_platforms} platforms from collection...")

        # Handle nofilter platforms
        for platform_name in nofilter_platforms:
            url_file = get_url_file_path(collection_path, platform_name)
            if url_file.exists():
                logger.info(f"✓ Using existing URL file for {platform_name}")
            else:
                logger.warning(f"✗ No existing URL file found for {platform_name}")

        # Process filter platforms with async concurrency
        if filter_platforms:
            success_count = await process_platforms_async(collection_path, filter_platforms, cache_manager)
            total_processed = success_count
            fail_count = len(filter_platforms) - success_count
        else:
            total_processed = 0
            fail_count = 0

        successful_platforms = total_processed
        for platform_name in nofilter_platforms:
            url_file = get_url_file_path(collection_path, platform_name)
            if url_file.exists():
                successful_platforms += 1

        logger.info(f"URL generation completed: {successful_platforms}/{total_platforms} successful")
        return fail_count == 0

    except Exception as e:
        logger.error(f"Failed to generate collection URLs: {e}")
        return False
