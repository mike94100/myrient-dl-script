#!/usr/bin/env python3
"""
Myrient Content Generator
Generate URL files and README documentation from collection TOML configurations

Supports concurrent generation for improved performance when both are needed.
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import List, Any

# Import utilities
from utils import wget_install
from utils.log_utils import init_logger, get_logger, disable_console_logging, enable_console_logging
from utils.wget_utils import wget_check
from utils.progress_utils import show_progress, clear_progress
from utils.cache_utils import setup_cache_from_config
from filters.filter_collection import CollectionFilter, get_all_platforms

# Import the generation utilities
from utils.url_generator import generate_collection_urls_async
from utils.readme_generator import generate_readme


async def generate_urls_async(collection_path: str, cache_manager=None, dry_run: bool = False) -> bool:
    """Wrapper to call the URL generation module"""
    return await generate_collection_urls_async(collection_path, cache_manager, dry_run)


def generate_readme_sync(collection_path: str, dry_run: bool = False) -> bool:
    """Wrapper to call the README generation module"""
    return generate_readme(collection_path) if not dry_run else True


async def generate_both_async(collection_path: str, cache_manager=None, dry_run: bool = False) -> tuple[bool, bool]:
    """Generate both URLs and README concurrently for maximum speed"""
    logger = get_logger()
    logger.info("Generating URLs and README concurrently...")

    if dry_run:
        logger.info("DRY RUN: Would generate both URLs and README")
        return True, True

    # Run URL generation and README generation concurrently
    url_task = generate_urls_async(collection_path, cache_manager, dry_run)
    readme_task = asyncio.to_thread(generate_readme_sync, collection_path, dry_run)

    # Wait for both to complete
    url_success, readme_success = await asyncio.gather(url_task, readme_task, return_exceptions=True)

    # Handle exceptions
    if isinstance(url_success, Exception):
        logger.error(f"URL generation failed with exception: {url_success}")
        url_success = False

    if isinstance(readme_success, Exception):
        logger.error(f"README generation failed with exception: {readme_success}")
        readme_success = False

    return url_success, readme_success


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Myrient Content Generator - Generate URL files and README documentation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate only URL files
  python myrient_generator.py --gen-url collections/sample/sample.toml

  # Generate only README
  python myrient_generator.py --gen-readme collections/sample/sample.toml

  # Generate both concurrently
  python myrient_generator.py --gen-url --gen-readme collections/sample/sample.toml

  # Dry run to see what would be done
  python myrient_generator.py --gen-url --gen-readme --dry-run collections/sample/sample.toml
        """
    )

    # Generation options
    parser.add_argument(
        '--gen-url', '--gen-urls', action='store_true',
        help='Generate URL files by scraping Myrient pages'
    )
    parser.add_argument(
        '--gen-readme', action='store_true',
        help='Generate README documentation'
    )

    # Global options
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Show what would be done without actually generating files'
    )
    parser.add_argument(
        '--verbose', '-v', action='store_true',
        help='Enable verbose output'
    )
    parser.add_argument(
        '--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='INFO',
        help='Set logging level (default: INFO)'
    )

    # Input files
    parser.add_argument(
        'collection_files', nargs='+',
        help='Path to collection TOML file(s)'
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.gen_url and not args.gen_readme:
        parser.error("Must specify at least one of --gen-url or --gen-readme")

    # Setup logging
    log_dir = Path.cwd() / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "gen_content.log"
    logger = init_logger(log_file=str(log_file), verbose=args.verbose, level=getattr(logging, args.log_level.upper(), logging.INFO))

    # Setup cache for URL generation
    cache_manager = None
    if args.gen_url:
        cache_manager = setup_cache_from_config()

        # Ensure wget is available for scraping
        if not wget_check():
            logger.info("Installing wget...")
            if not wget_install():
                logger.error("Failed to install wget")
                sys.exit(1)

    # Validate input files
    toml_files = []
    for path_str in args.collection_files:
        path = Path(path_str)
        if not path.exists():
            logger.error(f"Collection file not found: {path}")
            sys.exit(1)
        if not path.name.endswith('.toml'):
            logger.error(f"File must be a TOML file: {path}")
            sys.exit(1)
        toml_files.append(path)

    # Remove duplicates while preserving order
    seen = set()
    toml_files = [f for f in toml_files if str(f) not in seen and not seen.add(str(f))]

    logger.info(f"Processing {len(toml_files)} collection file(s)")

    # Process each collection file
    async def process_collections():
        total_success = True

        for i, toml_file in enumerate(toml_files, 1):
            logger.info(f"Processing collection {i}/{len(toml_files)}: {toml_file}")

            try:
                if args.gen_url and args.gen_readme:
                    # Generate both concurrently
                    url_success, readme_success = await generate_both_async(str(toml_file), cache_manager, args.dry_run)
                    success = url_success and readme_success
                elif args.gen_url:
                    # Generate only URLs
                    success = await generate_urls_async(str(toml_file), cache_manager, args.dry_run)
                elif args.gen_readme:
                    # Generate only README
                    success = generate_readme_sync(str(toml_file), args.dry_run)
                else:
                    success = False

                if not success:
                    total_success = False
                    logger.error(f"Failed to process {toml_file}")

            except Exception as e:
                logger.error(f"Error processing {toml_file}: {e}")
                total_success = False

        return total_success

    # Run async processing
    import asyncio
    success = asyncio.run(process_collections())

    if success:
        logger.info("Content generation completed successfully!")
    else:
        logger.error("Content generation failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
