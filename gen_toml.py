#!/usr/bin/env python3
"""
Myrient TOML Generator
Generate TOML configuration files and README documentation by scraping Myrient pages
"""

import argparse
import logging
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any
from urllib.parse import unquote

# Import utilities
from utils import wget_install
from utils.log_utils import init_logger, get_logger
from utils.url_utils import construct_url, validate_directory_path
from utils.wget_utils import wget_scrape, wget_check
from utils.toml_utils import write_toml_file, parse_toml_file
from utils.file_size_utils import format_file_size_dual
from utils.cache_utils import setup_cache_from_config, get_config_value, load_config
from utils.progress_utils import show_progress, clear_progress
from filters.filter_1g1r import filter_apply_1g1r
from gen_readme import generate_readme, generate_meta_readme


def determine_filter_settings(args) -> tuple[str, bool]:
    """Determine filter type and whether to apply filtering based on args"""
    filter_type = args.filter or 'none'
    apply_filter = filter_type != 'none'
    return filter_type, apply_filter


def get_platform_mappings(config: dict) -> dict:
    """Get platform mappings from config with validation"""
    platform_mappings = config.get('platforms', {})
    if not platform_mappings:
        logger = get_logger()
        logger.error("No platforms defined in config [platforms] section")
        logger.info("Add platform mappings to config.toml or config.toml.template")
    return platform_mappings


def update_meta_all_toml(output_base: Path, generated_platforms: list, config: dict) -> bool:
    """Update the meta all.toml file and generate READMEs for all successfully generated platforms"""
    logger = get_logger()

    try:
        # Path to the meta all.toml file
        all_toml_path = output_base / "all.toml"

        # Get all platform names that were attempted (from config)
        all_config_platforms = set(get_platform_mappings(config).keys())

        # Generate the list of platform TOML references
        # Only include platforms that exist in the output directory
        platform_tomls = []

        for platform_name in sorted(all_config_platforms):
            platform_dir = output_base / platform_name
            platform_toml = platform_dir / f"{platform_name}.toml"

            # Only include platforms that were successfully generated
            if platform_toml.exists():
                # Use relative path from the all.toml directory
                relative_path = f"{platform_name}/{platform_name}.toml"
                platform_tomls.append(relative_path)

        # Prepare the TOML data
        all_toml_data = {
            "site": get_config_value('general', 'site', default='https://myrient.erista.me'),
            "platform_tomls": platform_tomls
        }

        # Write the updated all.toml file
        write_toml_file(str(all_toml_path), all_toml_data)

        # Generate README using the centralized function from gen_readme.py
        # This will regenerate all platform READMEs and create the meta README
        generate_meta_readme(all_toml_path, all_toml_data)

        logger.info(f"Updated {all_toml_path} and generated READMEs for {len(platform_tomls)} platforms")
        return True

    except Exception as e:
        logger.error(f"Failed to update meta all.toml and README: {e}")
        return False


def ensure_output_directory(output_dir: Path) -> None:
    """Create output directory if it doesn't exist"""
    output_dir.mkdir(parents=True, exist_ok=True)


def generate_platform_with_readme(platform_name: str, platform_path: str, output_dir: Path,
                                 apply_filter: bool, config: dict) -> bool:
    """Generate TOML and README for a single platform, return success"""
    logger = get_logger()

    # Ensure output directory exists
    ensure_output_directory(output_dir)

    # Generate the TOML
    success = generate_platform_toml(
        site=get_config_value('general', 'site', default='https://myrient.erista.me'),
        path_directory=platform_path,
        output_dir=output_dir,
        apply_filter=apply_filter,
        slim_output=get_config_value('generation', 'slim_output', default=False)
    )

    if success:
        # Generate README from the newly created TOML
        toml_file = output_dir / f"{platform_name}.toml"
        if generate_readme(toml_file):
            logger.info(f"✓ Completed {platform_name}")
            return True
        else:
            logger.error(f"✗ Failed to generate README for {platform_name}")
            return False
    else:
        logger.error(f"✗ Failed to generate TOML for {platform_name}")
        return False


def extract_zip_files(html: str) -> list:
    """Extract .zip filenames from Myrient HTML"""
    # Pattern matches: href="filename.zip">filename.zip</a>
    pattern = r'href="([^"]*\.zip)"[^>]*>([^<]*)</a>'
    matches = re.findall(pattern, html)

    # Return unique filenames
    seen = set()
    files = []
    for href, text in matches:
        filename = text.strip()
        if filename and filename not in seen:
            files.append(filename)
            seen.add(filename)

    return sorted(files)

def generate_platform_toml(site: str, path_directory: str, output_dir: Path,
                          apply_filter: bool = True, slim_output: bool = False) -> bool:
    """
    Generate TOML file for a platform

    Args:
        site: Myrient site URL
        path_directory: Platform directory path
        output_dir: Output directory for TOML file
        apply_filter: Whether to apply 1G1R filtering
        slim_output: Whether to exclude commented files from output

    Returns:
        True if successful
    """
    logger = get_logger()

    try:
        # Validate path
        validate_directory_path(path_directory)

        # Construct directory URL
        dir_url = construct_url(site, path_directory)
        logger.info(f"Scraping: {dir_url}")

        # Download HTML
        html = wget_scrape(dir_url)
        if not html:
            logger.error("Failed to download directory listing")
            return False

        # Extract files
        files = extract_zip_files(html)
        if not files:
            logger.error("No .zip files found on page")
            return False

        logger.info(f"Found {len(files)} files")

        # Apply filtering
        if apply_filter:
            logger.info("Applying 1G1R filter...")
            filtered_files = filter_apply_1g1r(files)
            included = sum(1 for f in filtered_files if not f.startswith('#'))
            excluded = len(filtered_files) - included
            logger.info(f"Filter results: {included} included, {excluded} excluded")
        else:
            filtered_files = files

        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        # Use the output directory name as filename
        output_file = output_dir / f"{output_dir.name}.toml"

        # Prepare TOML data
        toml_data = {
            "site": site,
            "path_directory": path_directory,
            "directory": output_dir.name,
            "files": filtered_files if not slim_output else
                    [f for f in filtered_files if not f.startswith('#')]
        }

        # Write TOML file
        write_toml_file(str(output_file), toml_data)
        logger.info(f"Generated {output_file}")

        return True

    except Exception as e:
        logger.error(f"Failed to generate TOML: {e}")
        return False


def main():
    """Main entry point"""
    # Parse arguments first to see if we need wget
    parser = argparse.ArgumentParser(
        description="Generate platform TOML files and READMEs by scraping Myrient pages",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate ALL platforms from config (default: no filter)
  python gen_platform_toml.py --all --output output/dir

  # Generate ALL platforms with 1G1R filter
  python gen_platform_toml.py --all --filter 1g1r --output output/dir

  # Generate single platform TOML with default settings
  python gen_platform_toml.py toml "/files/No-Intro/Nintendo - Game Boy/" output/dir

  # Generate with custom config
  python gen_platform_toml.py toml "/files/No-Intro/Nintendo - Game Boy/" output/dir --no-filter --slim

  # Generate README for specific TOML
  python gen_platform_toml.py --readme gb.toml

  # Generate READMEs for all TOMLs in current directory
  python gen_platform_toml.py --readme

  # Generate TOML+README from config mapping
  python gen_platform_toml.py --readme output/dir

  # Dry run to see what would be generated
  python gen_platform_toml.py toml "/files/No-Intro/Nintendo - Game Boy/" output/dir --dry-run
        """
    )

    # Global arguments
    parser.add_argument(
        '--readme', nargs='*', metavar=('OUTPUT_DIR', 'SOURCE_URL'),
        help='Generate README.md from TOML file, or generate TOML+README from output dir and source URL'
    )
    parser.add_argument(
        '--all', action='store_true',
        help='Generate TOML+README for all platforms defined in config [platforms] section'
    )
    parser.add_argument(
        '--filter', metavar='FILTER',
        help='Filter to apply: "none" (default, no filtering), "1g1r" (1G1R filter), or custom filter name'
    )
    parser.add_argument(
        '--output', '-o', metavar='DIR',
        help='Output directory for generated files'
    )
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Show what would be done without actually generating files'
    )
    parser.add_argument(
        '--verbose', '-v', action='store_true',
        help='Enable verbose output'
    )
    parser.add_argument(
        '--parallel', type=int, metavar='N',
        help='Generate READMEs in parallel with N workers (default: sequential)'
    )

    # Subparsers for different commands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # TOML generation command
    toml_parser = subparsers.add_parser('toml', help='Generate TOML file')
    toml_parser.add_argument(
        'path_directory',
        help='Platform directory path (e.g., "/files/No-Intro/Nintendo - Game Boy/")'
    )
    toml_parser.add_argument(
        'output_directory',
        help='Output directory for TOML file'
    )
    toml_parser.add_argument(
        'site', nargs='?',
        help='Myrient site URL (default: from config or https://myrient.erista.me)'
    )
    toml_parser.add_argument(
        '--no-filter', action='store_true',
        help='Skip 1G1R filtering'
    )
    toml_parser.add_argument(
        '--slim', action='store_true',
        help='Exclude commented files from TOML output'
    )
    toml_parser.add_argument(
        '--dry-run', action='store_true',
        help='Show what would be done without actually generating files'
    )

    # Legacy positional arguments support
    parser.add_argument(
        'legacy_path', nargs='?',
        help=argparse.SUPPRESS
    )
    parser.add_argument(
        'legacy_output', nargs='?',
        help=argparse.SUPPRESS
    )
    parser.add_argument(
        'legacy_site', nargs='?',
        help=argparse.SUPPRESS
    )

    args = parser.parse_args()

    # Load configuration
    config = load_config()

    # Setup logging with config
    verbose = args.verbose or get_config_value('logging', 'verbose', default=True)
    log_level = get_config_value('logging', 'level', default='INFO')
    # Use a log file in logs directory so logging messages don't interfere with progress bars
    log_dir = Path.cwd() / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "gen_platform_toml.log"
    logger = init_logger(log_file=str(log_file), verbose=verbose, level=getattr(logging, log_level.upper(), logging.INFO))

    # Setup cache
    cache_manager = setup_cache_from_config()

    # Handle --all flag (generate all platforms from config)
    if args.all:
        if args.dry_run:
            print("DRY RUN: Would generate TOML+README for all platforms in config")
            return

        # Get platform mappings from config
        platform_mappings = get_platform_mappings(config)

        if not platform_mappings:
            sys.exit(1)

        # Determine filter settings
        filter_type, apply_filter = determine_filter_settings(args)

        # Get output directory
        output_base = Path(getattr(args, 'output', None) or 'dl/')

        logger.info(f"Generating TOML+README for {len(platform_mappings)} platforms with {filter_type} filter...")
        logger.info(f"Output directory: {output_base}")

        # First, generate all TOMLs with progress bar (parallelized)
        toml_files_to_generate_readmes = []
        success_count = 0
        fail_count = 0

        logger.info(f"Generating TOMLs for {len(platform_mappings)} platforms...")

        # Get rate limiting settings
        request_delay = get_config_value('scraping', 'request_delay', default=1.0)
        max_workers = get_config_value('generation', 'max_parallel_workers', default=min(4, len(platform_mappings)))

        # Disable console logging during TOML generation to show progress cleanly
        from utils.log_utils import disable_console_logging, enable_console_logging
        from concurrent.futures import ThreadPoolExecutor, as_completed
        disable_console_logging()

        try:
            # Use parallel processing for TOML generation with rate limiting
            completed = 0
            total = len(platform_mappings)
            last_request_time = 0

            def generate_toml_with_rate_limit(platform_name: str, platform_url: str):
                """Generate TOML for a single platform with rate limiting and error handling"""
                nonlocal last_request_time

                # Enforce minimum delay between requests
                current_time = time.time()
                time_since_last = current_time - last_request_time
                if time_since_last < request_delay:
                    sleep_time = request_delay - time_since_last
                    time.sleep(sleep_time)

                try:
                    # Create platform directory
                    output_dir = output_base / platform_name
                    output_dir.mkdir(parents=True, exist_ok=True)

                    # Generate TOML
                    success = generate_platform_toml(
                        site=get_config_value('general', 'site', default='https://myrient.erista.me'),
                        path_directory=platform_url,
                        output_dir=output_dir,
                        apply_filter=apply_filter,
                        slim_output=get_config_value('generation', 'slim_output', default=False)
                    )

                    last_request_time = time.time()

                    if success:
                        toml_file = output_dir / f"{platform_name}.toml"
                        return platform_name, toml_file, True, None
                    else:
                        return platform_name, None, False, "TOML generation failed"

                except Exception as e:
                    return platform_name, None, False, str(e)

            def toml_progress_callback(future):
                """Update progress when a TOML generation completes"""
                nonlocal completed
                completed += 1
                show_progress(completed, total, "Generating TOMLs", force=True)

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all TOML generation tasks
                futures = {}
                for platform_name, platform_url in platform_mappings.items():
                    future = executor.submit(generate_toml_with_rate_limit, platform_name, platform_url)
                    futures[future] = platform_name

                # Add progress callback to each future
                for future in futures:
                    future.add_done_callback(toml_progress_callback)

                # Collect results as they complete
                for future in as_completed(futures):
                    platform_name = futures[future]
                    try:
                        name, toml_file, success, error = future.result(timeout=300)  # 5 minute timeout per TOML
                        if success:
                            toml_files_to_generate_readmes.append(toml_file)
                            success_count += 1
                        else:
                            logger.error(f"✗ Error processing {name}: {error}")
                            fail_count += 1
                    except Exception as e:
                        logger.error(f"✗ Error processing {platform_name}: {e}")
                        fail_count += 1

            clear_progress()
        finally:
            enable_console_logging()

        # Update the meta all.toml file with all generated platforms
        if success_count > 0:
            logger.info("Updating meta all.toml file...")
            update_meta_all_toml(output_base, platform_mappings.keys(), config)

        # Then generate all READMEs with parallel processing
        if toml_files_to_generate_readmes:
            logger.info(f"Generating READMEs for {len(toml_files_to_generate_readmes)} platforms...")

            # Use parallel processing for README generation
            readme_max_workers = get_config_value('generation', 'max_parallel_workers', default=min(4, len(toml_files_to_generate_readmes)))
            generate_readme(toml_files_to_generate_readmes, max_workers=readme_max_workers, request_delay=request_delay)

        logger.info(f"Batch generation completed: {success_count} successful, {fail_count} failed")
        if fail_count > 0:
            sys.exit(1)
        return

    # Handle README generation
    if args.readme:
        if args.dry_run:
            print("DRY RUN: Would generate README files")
            return

        if args.readme == '.':
            # Generate READMEs for all TOML files in current directory
            current_dir = Path.cwd()
            toml_files = list(current_dir.glob("*.toml"))
            if not toml_files:
                logger.error("No TOML files found in current directory")
                logger.info("Try running: python gen_platform_toml.py toml <path> <output> --filter")
                sys.exit(1)

            # Get rate limiting settings from config
            request_delay = get_config_value('scraping', 'request_delay', default=1.0)

            # Use parallel processing if requested
            if getattr(args, 'parallel', None) and args.parallel > 1:
                logger.info(f"Generating READMEs for {len(toml_files)} TOML files using {args.parallel} workers...")
                results = generate_readme(toml_files, args.parallel, request_delay)
                success = all(results)
            else:
                logger.info(f"Generating READMEs for {len(toml_files)} TOML files...")
                results = generate_readme(toml_files, 1, request_delay)  # Sequential
                success = all(results)

            if success:
                logger.info("README generation completed successfully!")
            else:
                failed_count = sum(1 for r in results if not r)
                logger.error(f" {failed_count} README generation(s) failed")
                sys.exit(1)
        else:
            # Parse README arguments
            readme_args = args.readme

            if len(readme_args) == 1:
                target_path = Path(readme_args[0])
                if target_path.is_dir():
                    # Single directory argument - try to generate TOML using config mappings
                    platform_name = target_path.name

                    # Get platform mappings from config
                    platform_mappings = get_platform_mappings(config)

                    if platform_name in platform_mappings:
                        platform_path = platform_mappings[platform_name]
                        logger.info(f"Generating TOML+README for {platform_name} from {platform_path}")

                        # Determine filter settings
                        _, apply_filter = determine_filter_settings(args)

                        # Generate TOML and README using helper function
                        if not generate_platform_with_readme(platform_name, platform_path, target_path, apply_filter, config):
                            sys.exit(1)
                    else:
                        logger.error(f"No mapping found for platform: {platform_name}")
                        logger.info("Add it to the [platforms] section in config.toml")
                        logger.info("Or use: python gen_platform_toml.py --readme <output_dir> <source_url>")
                        sys.exit(1)
                else:
                    # Single TOML file argument
                    toml_file = target_path
                    if not toml_file.exists():
                        logger.error(f"TOML file not found: {toml_file}")
                        sys.exit(1)

                    if generate_readme(toml_file):
                        logger.info(" README generation completed successfully!")
                    else:
                        logger.error(" README generation failed")
                        sys.exit(1)

            elif len(readme_args) == 2:
                # Two arguments - output directory and source URL
                output_dir = Path(readme_args[0])
                source_url = readme_args[1]

                logger.info(f"Generating TOML+README for {output_dir} from {source_url}")

                # Determine filter settings
                _, apply_filter = determine_filter_settings(args)

                # For two-argument case, platform name is derived from output directory
                platform_name = output_dir.name

                # Generate TOML and README using helper function
                if not generate_platform_with_readme(platform_name, source_url, output_dir, apply_filter, config):
                    sys.exit(1)

            else:
                logger.error("Invalid number of arguments for --readme")
                logger.info("Usage:")
                logger.info("  python gen_platform_toml.py --readme <toml_file>")
                logger.info("  python gen_platform_toml.py --readme <output_dir> <source_url>")
                sys.exit(1)
        return

    # Handle legacy arguments (backward compatibility)
    if hasattr(args, 'legacy_path') and args.legacy_path and not args.command:
        args.command = 'toml'
        args.path_directory = args.legacy_path
        args.output_directory = args.legacy_output
        args.site = args.legacy_site

    # Ensure wget is available for TOML generation
    if args.command == 'toml':
        if not wget_check():
            logger.info("Installing wget...")
            if not wget_install():
                logger.error(" Failed to install wget")
                sys.exit(1)

    # Handle TOML generation
    if args.command == 'toml':
        # Get config values
        default_site = get_config_value('general', 'site', default='https://myrient.erista.me')
        default_output = 'dl/'
        apply_filter_default = get_config_value('generation', 'apply_filter', default=True)
        slim_default = get_config_value('generation', 'slim_output', default=False)

        # Determine parameters
        site = getattr(args, 'site', None) or default_site
        output_dir = Path(args.output_directory or default_output)
        apply_filter = not getattr(args, 'no_filter', False) and apply_filter_default
        slim_output = getattr(args, 'slim', False) or slim_default

        if args.dry_run:
            print("DRY RUN: Would generate TOML file")
            print(f"  Platform: {args.path_directory}")
            print(f"  Site: {site}")
            print(f"  Output: {output_dir}")
            print(f"  Filter: {'enabled' if apply_filter else 'disabled'}")
            print(f"  Slim: {'enabled' if slim_output else 'disabled'}")
            return

        # Generate TOML
        logger.info(" Starting TOML generation...")
        success = generate_platform_toml(
            site=site,
            path_directory=args.path_directory,
            output_dir=output_dir,
            apply_filter=apply_filter,
            slim_output=slim_output
        )

        if success:
            logger.info(" TOML generation completed successfully!")
            toml_file = output_dir / f"{Path(args.path_directory).name}.toml"
            logger.info(f" Generated: {toml_file}")
        else:
            logger.error(" TOML generation failed")
            logger.info(" Check your internet connection and try again")
            sys.exit(1)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
