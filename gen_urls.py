#!/usr/bin/env python3
"""
Myrient URL Generator
Generate URL files from collection.toml configuration by scraping Myrient pages
"""

import argparse
import logging
import re
import sys
from pathlib import Path
from typing import List, Any
from urllib.parse import quote

# Import utilities
from utils import wget_install
from utils.log_utils import init_logger, get_logger, disable_console_logging, enable_console_logging
from utils.wget_utils import wget_scrape, wget_check
from utils.progress_utils import show_progress, clear_progress
from utils.cache_utils import setup_cache_from_config
from filters.filter_collection import CollectionFilter, get_all_platforms


def discover_and_organize_platforms(collection_path: str) -> tuple[List[str], List[str]]:
    """Discover platforms and separate filter from nofilter platforms"""
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

def get_url_file_path(collection_path: str, platform_name: str) -> Path:
    """Get the URL file path for a platform from its urllist configuration"""
    filter_obj = CollectionFilter(collection_path)
    platform_config = filter_obj.get_platform_config(platform_name)
    if not platform_config or 'urllist' not in platform_config:
        logger = get_logger()
        logger.error(f"Platform {platform_name} is missing required 'urllist' field")
        sys.exit(1)
    return Path(platform_config['urllist'])

def setup_application_environment(args) -> tuple[Any, Any]:
    """Setup logging, cache, and validate environment"""
    # Setup logging
    log_dir = Path.cwd() / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "gen_urls.log"
    logger = init_logger(log_file=str(log_file), verbose=args.verbose,
                        level=getattr(logging, args.log_level.upper(), logging.INFO))

    # Setup cache
    cache_manager = setup_cache_from_config()

    # Ensure wget is available for scraping
    if not wget_check():
        logger.info("Installing wget...")
        if not wget_install():
            logger.error("Failed to install wget")
            sys.exit(1)

    return logger, cache_manager


def create_platform_worker(collection_path: str, cache_manager=None):
    """Create a worker function for processing platforms in parallel"""
    async def process_platform(platform_name: str) -> tuple[str, bool, str]:
        """Process a single platform and return results"""
        try:
            success = await generate_platform_urls(collection_path, platform_name, cache_manager)
            return platform_name, success, ""
        except Exception as e:
            return platform_name, False, str(e)

    return process_platform


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


async def generate_collection_urls_async(collection_path: str, cache_manager=None) -> bool:
    """
    Generate URL files for all platforms in collection.toml

    Args:
        collection_path: Path to collection.toml file

    Returns:
        True if successful
    """
    logger = get_logger()

    try:
        # Discover and organize platforms
        filter_platforms, nofilter_platforms = discover_and_organize_platforms(collection_path)

        total_platforms = len(filter_platforms) + len(nofilter_platforms)
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

        logger.info(f"Collection URL generation completed: {successful_platforms}/{total_platforms} successful")
        return fail_count == 0

    except Exception as e:
        logger.error(f"Failed to generate collection URLs: {e}")
        return False


async def process_platforms_async(collection_path: str, platforms: List[str], cache_manager=None) -> int:
    """
    Process multiple platforms asynchronously with true concurrency

    Args:
        collection_path: Path to collection.toml
        platforms: List of platform names to process
        cache_manager: Cache manager for HTTP responses

    Returns:
        Number of successfully processed platforms
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
    from utils.log_utils import disable_console_logging, enable_console_logging
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
            # Calculate total files processed so far (rough estimate)
            # This is an approximation since we don't have exact file counts per platform
            # In a full implementation, we'd track this more accurately
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

    Args:
        collection_path: Path to collection.toml
        platform_name: Name of the platform

    Returns:
        True if successful
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


async def async_main():
    """Async main entry point with subcommands"""
    parser = argparse.ArgumentParser(
        description="Myrient URL Generator - Generate URL files from collection.toml",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate URL files for all platforms
  python gen_urls.py scrape collections/sample/sample.toml

  # Validate collection file
  python gen_urls.py validate collections/sample/sample.toml

  # Show collection information
  python gen_urls.py info collections/sample/sample.toml

  # Generate shell completion
  python gen_urls.py completion bash >> ~/.bashrc
        """
    )

    # Global options
    parser.add_argument(
        '--verbose', '-v', action='store_true',
        help='Enable verbose output'
    )
    parser.add_argument(
        '--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='INFO',
        help='Set logging level (default: INFO)'
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available commands', required=True)

    # Scrape command
    scrape_parser = subparsers.add_parser(
        'scrape',
        help='Generate URL files by scraping Myrient pages',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python gen_urls.py scrape collections/sample/sample.toml
  python gen_urls.py scrape collections/sample/sample.toml --dry-run
        """
    )
    scrape_parser.add_argument(
        'collection_file',
        help='Path to collection.toml file'
    )
    scrape_parser.add_argument(
        '--dry-run', action='store_true',
        help='Show what would be done without actually generating files'
    )
    scrape_parser.add_argument(
        '--force', '-f', action='store_true',
        help='Force regeneration even if cache exists'
    )
    scrape_parser.add_argument(
        '--readme', action='store_true',
        help='Generate README automatically after URL generation'
    )

    # Validate command
    validate_parser = subparsers.add_parser(
        'validate',
        help='Validate collection file syntax and structure',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python gen_urls.py validate collections/sample/sample.toml
        """
    )
    validate_parser.add_argument(
        'collection_file',
        help='Path to collection.toml file to validate'
    )

    # Info command
    info_parser = subparsers.add_parser(
        'info',
        help='Show information about a collection',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python gen_urls.py info collections/sample/sample.toml
        """
    )
    info_parser.add_argument(
        'collection_file',
        help='Path to collection.toml file'
    )

    # Completion command
    completion_parser = subparsers.add_parser(
        'completion',
        help='Generate shell completion script',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Bash completion
  python gen_urls.py completion bash >> ~/.bashrc

  # Zsh completion
  python gen_urls.py completion zsh >> ~/.zshrc
        """
    )
    completion_parser.add_argument(
        'shell', choices=['bash', 'zsh'],
        help='Shell type for completion script'
    )

    args = parser.parse_args()

    # Setup application environment
    logger, cache_manager = setup_application_environment(args)

    # Handle subcommands
    if args.command == 'scrape':
        await handle_scrape_command(args, logger, cache_manager)
    elif args.command == 'validate':
        handle_validate_command(args, logger)
    elif args.command == 'info':
        handle_info_command(args, logger)
    elif args.command == 'completion':
        handle_completion_command(args)


async def handle_scrape_command(args, logger, cache_manager):
    """Handle the scrape subcommand"""
    if args.dry_run:
        print("DRY RUN: Would generate URL files from collection")
        print(f"  Collection: {args.collection_file}")
        return

    if not Path(args.collection_file).exists():
        logger.error(f"Collection file not found: {args.collection_file}")
        sys.exit(1)

    logger.info(f"Generating URL files from {args.collection_file}")
    success = await generate_collection_urls_async(args.collection_file, cache_manager)

    if success:
        logger.info("URL generation completed successfully!")

        # Generate README if requested
        if args.readme:
            logger.info("Generating README...")
            try:
                # Import README generation function
                from gen_readme import generate_readme
                readme_result = generate_readme(args.collection_file)
                if readme_result:
                    logger.info("README generation completed successfully!")
                else:
                    logger.warning("README generation failed")
            except Exception as e:
                logger.warning(f"README generation failed: {e}")
    else:
        logger.error("URL generation failed")
        sys.exit(1)


def handle_validate_command(args, logger):
    """Handle the validate subcommand"""
    if not Path(args.collection_file).exists():
        logger.error(f"Collection file not found: {args.collection_file}")
        sys.exit(1)

    try:
        # Try to parse the collection
        filter_platforms, nofilter_platforms = discover_and_organize_platforms(args.collection_file)

        print("✅ Collection file is valid")
        print(f"   Filter platforms: {len(filter_platforms)}")
        print(f"   Nofilter platforms: {len(nofilter_platforms)}")

        if filter_platforms:
            print(f"   Platforms: {', '.join(filter_platforms[:5])}{'...' if len(filter_platforms) > 5 else ''}")
        if nofilter_platforms:
            print(f"   Nofilter platforms: {', '.join(nofilter_platforms[:5])}{'...' if len(nofilter_platforms) > 5 else ''}")

    except Exception as e:
        logger.error(f"❌ Collection file validation failed: {e}")
        sys.exit(1)


def handle_info_command(args, logger):
    """Handle the info subcommand"""
    if not Path(args.collection_file).exists():
        logger.error(f"Collection file not found: {args.collection_file}")
        sys.exit(1)

    try:
        filter_platforms, nofilter_platforms = discover_and_organize_platforms(args.collection_file)

        print(f"Collection: {args.collection_file}")
        print()

        print("Platforms:")
        for platform in sorted(filter_platforms):
            url_file = get_url_file_path(args.collection_file, platform)
            status = "✅ Generated" if url_file.exists() else "❌ Missing"
            print(f"  {platform}: {status}")

        if nofilter_platforms:
            print()
            print("Nofilter platforms:")
            for platform in sorted(nofilter_platforms):
                url_file = get_url_file_path(args.collection_file, platform)
                status = "✅ Has file" if url_file.exists() else "❌ No file"
                print(f"  {platform}: {status}")

        # Collect all URL files
        all_platforms = filter_platforms + nofilter_platforms
        url_files = []
        for platform in all_platforms:
            url_file = get_url_file_path(args.collection_file, platform)
            if url_file.exists():
                url_files.append(url_file)

        total_urls = 0
        if url_files:
            print()
            print("File statistics:")
            for url_file in sorted(url_files):
                try:
                    with open(url_file, 'r') as f:
                        urls = [line.strip() for line in f if line.strip()]
                        included = sum(1 for url in urls if not url.startswith('#'))
                        excluded = sum(1 for url in urls if url.startswith('#'))
                        total_urls += len(urls)
                        print(f"  {url_file.name}: {included} included, {excluded} excluded")
                except Exception:
                    print(f"  {url_file.name}: Error reading file")

            print()
            print(f"Summary: {len(url_files)} URL files, {total_urls} total URLs")

    except Exception as e:
        logger.error(f"Failed to get collection info: {e}")
        sys.exit(1)


def handle_completion_command(args):
    """Handle the completion subcommand"""
    if args.shell == 'bash':
        completion_script = generate_bash_completion()
    elif args.shell == 'zsh':
        completion_script = generate_zsh_completion()
    else:
        print(f"Unsupported shell: {args.shell}")
        return

    print(completion_script)


def generate_bash_completion():
    """Generate bash completion script"""
    return '''
# Bash completion for gen_urls.py
_gen_urls_completions() {
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    opts="scrape validate info completion --help --verbose --log-level"

    case "${prev}" in
        scrape|validate|info)
            # Complete TOML files
            COMPREPLY=( $(compgen -f -X "!*.toml" -- "${cur}") )
            return 0
            ;;
        completion)
            COMPREPLY=( $(compgen -W "bash zsh" -- "${cur}") )
            return 0
            ;;
        --log-level)
            COMPREPLY=( $(compgen -W "DEBUG INFO WARNING ERROR" -- "${cur}") )
            return 0
            ;;
    esac

    COMPREPLY=( $(compgen -W "${opts}" -- "${cur}") )
    return 0
}

complete -F _gen_urls_completions gen_urls.py
'''


def generate_zsh_completion():
    """Generate zsh completion script"""
    return '''
# Zsh completion for gen_urls.py
#compdef gen_urls.py

_gen_urls() {
    local -a commands
    commands=(
        'scrape:Generate URL files by scraping Myrient pages'
        'validate:Validate collection file syntax and structure'
        'info:Show information about a collection'
        'completion:Generate shell completion script'
    )

    _arguments \\
        '(-v --verbose)'{-v,--verbose}'[Enable verbose output]' \\
        '--log-level[Set logging level]:(level):(DEBUG INFO WARNING ERROR)' \\
        ':command:->command' \\
        '*::options:->options'

    case $state in
        command)
            _describe -t commands 'command' commands
            ;;
        options)
            case $words[1] in
                scrape)
                    _arguments \\
                        '*:collection file:_files -g "*.toml"' \\
                        '--dry-run[Show what would be done]' \\
                        '(-f --force)'{-f,--force}'[Force regeneration]'
                    ;;
                validate|info)
                    _arguments \\
                        '*:collection file:_files -g "*.toml"'
                    ;;
                completion)
                    _arguments \\
                        ':shell:(bash zsh)'
                    ;;
            esac
            ;;
    esac
}

_gen_urls "$@"
'''


def main():
    """Main entry point - runs async main"""
    import asyncio
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
