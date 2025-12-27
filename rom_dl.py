#!/usr/bin/env python3
"""
ROM Downloader - Cross-platform downloader using wget
Downloads files, commonly from Myrient, from URLs listed in text files or TOML configurations
"""

import argparse
import sys
import zipfile
import tempfile
import os
from pathlib import Path
from typing import Optional

# Import utilities
from utils import wget_install
from utils.log_utils import init_logger, get_logger
from utils.toml_utils import parse_toml_file, filter_valid_files, parse_platforms_from_file
from utils.url_utils import construct_url
from utils.wget_utils import wget_download


def process_url_file(url_file_path: Path, output_dir: Path, dry_run: bool = False) -> bool:
    """
    Process a URL file (simple text file with one URL per line)

    Args:
        url_file_path: Path to URL file
        output_dir: Output directory for downloads
        dry_run: If True, only show what would be done

    Returns:
        True if successful
    """
    logger = get_logger()

    try:
        # Read URLs from file
        with open(url_file_path, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]

        if not urls:
            logger.error(f"No URLs found in {url_file_path}")
            return False

        if dry_run:
            logger.info(f"DRY RUN: Would process URL file: {url_file_path}")
            logger.info(f"DRY RUN: Would create directory: {output_dir}")
            logger.info(f"DRY RUN: Total URLs that would be downloaded: {len(urls)}")
            return True

        logger.info(f"Processing URL file: {url_file_path.name}")
        logger.info(f"Found {len(urls)} URLs to download")

        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created directory: {output_dir}")

        # Download files
        return wget_download(urls, output_dir)

    except Exception as e:
        logger.error(f"Failed to process URL file {url_file_path}: {e}")
        return False


def process_url_directory(url_dir_path: Path, output_dir: Path, dry_run: bool = False, platforms: list[str] = None) -> bool:
    """
    Process a directory containing multiple URL files

    Args:
        url_dir_path: Path to directory containing URL files
        output_dir: Base output directory for downloads
        dry_run: If True, only show what would be done

    Returns:
        True if successful
    """
    logger = get_logger()

    try:
        if not url_dir_path.exists() or not url_dir_path.is_dir():
            logger.error(f"URL directory not found: {url_dir_path}")
            return False

        # Find all .txt files in the directory
        all_url_files = list(url_dir_path.glob("*.txt"))
        if not all_url_files:
            logger.error(f"No URL files found in {url_dir_path}")
            return False

        # Filter to only requested platforms if specified
        if platforms:
            platforms_set = set(p.lower() for p in platforms)
            url_files = [f for f in all_url_files if f.stem.lower() in platforms_set]
            if not url_files:
                logger.error(f"None of the requested platforms {platforms} found in {url_dir_path}")
                logger.info(f"Available platforms: {[f.stem for f in all_url_files]}")
                return False
            logger.info(f"Filtering to platforms: {platforms}")
        else:
            url_files = all_url_files

        if dry_run:
            logger.info(f"DRY RUN: Would process URL directory: {url_dir_path}")
            total_urls = 0
            for url_file in url_files:
                try:
                    with open(url_file, 'r', encoding='utf-8') as f:
                        urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                        total_urls += len(urls)
                        logger.info(f"DRY RUN: {url_file.name} - {len(urls)} URLs")
                except Exception:
                    logger.warning(f"DRY RUN: Could not read {url_file.name}")
            logger.info(f"DRY RUN: Total URLs that would be downloaded: {total_urls}")
            return True

        logger.info(f"Processing URL directory: {url_dir_path}")
        logger.info(f"Found {len(url_files)} URL files to process")

        # Process each URL file
        total_success = True
        processed_files = 0
        total_urls = 0

        for url_file in url_files:
            platform_name = url_file.stem  # Remove .txt extension
            platform_output_dir = output_dir / platform_name

            logger.info(f"Processing platform: {platform_name}")

            if process_url_file(url_file, platform_output_dir, dry_run=False):
                processed_files += 1

                # Count URLs in this file
                try:
                    with open(url_file, 'r', encoding='utf-8') as f:
                        urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                        total_urls += len(urls)
                except Exception:
                    pass

                logger.info(f"Successfully processed {platform_name} ({len(urls)} files)")
            else:
                total_success = False
                logger.error(f"Failed to process {platform_name}")

        # Report results
        if total_success:
            logger.info(f"Successfully processed {processed_files}/{len(url_files)} URL files")
            logger.info(f"Total ROMs downloaded: {total_urls}")
        else:
            logger.error(f"Completed with errors: {processed_files}/{len(url_files)} URL files processed successfully")

        return total_success

    except Exception as e:
        logger.error(f"Failed to process URL directory {url_dir_path}: {e}")
        return False


def process_platform_toml(toml_path: Path, output_dir: Path, dry_run: bool = False) -> bool:
    """
    Process a platform TOML file

    Args:
        toml_path: Path to TOML file
        output_dir: Output directory for downloads
        dry_run: If True, only show what would be done

    Returns:
        True if successful
    """
    logger = get_logger()

    try:
        # Parse TOML
        config = parse_toml_file(str(toml_path))

        # Extract configuration
        site = config.get('site', 'https://myrient.erista.me')
        path_directory = config['path_directory']
        directory = config.get('directory', toml_path.stem)
        files = config.get('files', [])

        if not files:
            logger.error(f"No files found in {toml_path}")
            return False

        # Count valid files
        valid_files = filter_valid_files(files)
        total_files = len(valid_files)

        if dry_run:
            logger.info(f"DRY RUN: Would process platform TOML: {toml_path}")
            logger.info(f"DRY RUN: Would create directory: {output_dir / directory}")
            logger.info(f"DRY RUN: Total files that would be downloaded: {total_files}")
            return True

        logger.info(f"Processing {toml_path.name}")

        # Create output directory
        full_dir = output_dir / directory
        full_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created directory: {full_dir}")

        # Build download URLs
        download_urls = []
        for filename in valid_files:
            url = construct_url(site, path_directory, filename)
            download_urls.append(url)

        if not download_urls:
            logger.warning(f"No valid files to download from {toml_path}")
            return True

        # Download files
        return wget_download(download_urls, full_dir)

    except Exception as e:
        logger.error(f"Failed to process {toml_path}: {e}")
        return False


def is_meta_toml(toml_path: Path) -> bool:
    """Check if TOML is a meta config (contains platform_tomls array)"""
    try:
        config = parse_toml_file(str(toml_path))
        return 'platform_tomls' in config
    except:
        return False


def is_bios_toml(toml_path: Path) -> bool:
    """Check if TOML is a BIOS config (contains bios_platforms table)"""
    try:
        config = parse_toml_file(str(toml_path))
        return 'bios_platforms' in config
    except:
        return False


def is_url_file(file_path: Path) -> bool:
    """Check if file is a URL file (simple .txt file with URLs)"""
    if not file_path.name.endswith('.txt'):
        return False
    # Check if it's actually a TOML file (has key=value format)
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
            # If first line looks like TOML (has = and no http), it's a TOML file
            return not ('=' in first_line and not first_line.startswith('http'))
    except:
        return False


def is_collection_toml(file_path: Path) -> bool:
    """Check if TOML is a collection config (contains roms or bios sections)"""
    try:
        config = parse_toml_file(str(file_path))
        return 'roms' in config or 'bios' in config
    except:
        return False





def get_platform_url_file(toml_path: Path, platform_config: dict) -> Path:
    """Get the URL file path for a platform"""
    if 'urllist' not in platform_config:
        logger = get_logger()
        logger.error(f"Platform {platform_config.get('name', 'unknown')} is missing required 'urllist' field")
        sys.exit(1)
    return Path(platform_config['urllist'])


def process_collection_platforms(toml_path: Path, platforms_config: dict, output_dir: Path, dry_run: bool = False) -> bool:
    """Process platforms from new collection TOML format"""
    logger = get_logger()

    if dry_run:
        logger.info(f"DRY RUN: Would process {len(platforms_config)} platforms from collection")
        total_urls = 0
        for platform_name, platform_config in platforms_config.items():
            url_file = get_platform_url_file(toml_path, platform_config)
            if url_file.exists():
                try:
                    with open(url_file, 'r', encoding='utf-8') as f:
                        urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                        total_urls += len(urls)
                        logger.info(f"DRY RUN: {platform_name} - {len(urls)} URLs")
                except Exception:
                    logger.warning(f"DRY RUN: Could not read URL file for {platform_name}")
            else:
                logger.warning(f"DRY RUN: URL file not found for {platform_name}: {url_file}")
        logger.info(f"DRY RUN: Total URLs that would be downloaded: {total_urls}")
        return True

    logger.info(f"Processing {len(platforms_config)} platforms from collection")

    total_success = True
    processed_platforms = 0
    total_urls = 0

    for platform_name, platform_config in platforms_config.items():
        logger.info(f"Processing platform: {platform_name}")

        url_file = get_platform_url_file(toml_path, platform_config)
        if not url_file.exists():
            logger.error(f"URL file not found for {platform_name}: {url_file}")
            total_success = False
            continue

        # Determine output directory for this platform
        platform_dir = platform_config.get('directory', f"{platform_config['type']}/{platform_name}")
        full_output_dir = output_dir / platform_dir

        # Process the URL file
        if process_url_file(url_file, full_output_dir, dry_run=False):
            processed_platforms += 1

            # Count URLs processed
            try:
                with open(url_file, 'r', encoding='utf-8') as f:
                    urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                    total_urls += len(urls)
            except Exception:
                pass

            logger.info(f"Successfully processed {platform_name} ({len(urls)} files)")

            # Handle extraction if specified
            if platform_config.get('extract', False):
                logger.info(f"Extracting files for {platform_name}...")
                extract_platform_files(full_output_dir, platform_name)
        else:
            total_success = False
            logger.error(f"Failed to process {platform_name}")

    # Report results
    if total_success:
        logger.info(f"Successfully processed {processed_platforms}/{len(platforms_config)} platforms")
        logger.info(f"Total ROMs/BIOS downloaded: {total_urls}")
    else:
        logger.error(f"Completed with errors: {processed_platforms}/{len(platforms_config)} platforms processed successfully")

    return total_success


def extract_platform_files(platform_dir: Path, platform_name: str) -> None:
    """Extract zip files in a platform directory if extract=true"""
    logger = get_logger()

    try:
        zip_files = list(platform_dir.glob("*.zip"))
        if not zip_files:
            logger.info(f"No zip files found to extract for {platform_name}")
            return

        for zip_file in zip_files:
            logger.info(f"Extracting {zip_file.name}...")
            try:
                with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                    zip_ref.extractall(platform_dir)
                    logger.info(f"Extracted {len(zip_ref.namelist())} files from {zip_file.name}")

                # Remove the zip file after successful extraction
                zip_file.unlink()
                logger.info(f"Removed {zip_file.name} after extraction")

            except zipfile.BadZipFile as e:
                logger.error(f"Failed to extract {zip_file.name}: {e}")
            except Exception as e:
                logger.error(f"Error processing {zip_file.name}: {e}")

    except Exception as e:
        logger.error(f"Failed to extract files for {platform_name}: {e}")


def process_meta_toml(meta_path: Path, output_dir: Path, dry_run: bool = False) -> bool:
    """Process a meta TOML that lists other TOMLs"""
    logger = get_logger()

    try:
        config = parse_toml_file(str(meta_path))
        platform_tomls = config.get('platform_tomls', [])

        if not dry_run:
            logger.info(f"Processing meta TOML: {meta_path.name}")

        # Process each platform TOML individually for batch downloading per platform
        processed_tomls = []
        total_files = 0

        for toml_ref in platform_tomls:
            # Resolve path relative to meta TOML
            if toml_ref.startswith('/'):
                # Absolute path
                toml_path = Path(toml_ref)
            else:
                # Relative path
                toml_path = meta_path.parent / toml_ref

            if not toml_path.exists():
                logger.error(f"Referenced TOML not found: {toml_path}")
                return False

            processed_tomls.append(toml_path)

            # Count files for dry run (parse TOML to get file count)
            platform_config = parse_toml_file(str(toml_path))
            files = platform_config.get('files', [])
            valid_files = filter_valid_files(files)
            total_files += len(valid_files)

        if dry_run:
            logger.info(f"DRY RUN: Would process meta TOML: {meta_path}")
            logger.info(f"DRY RUN: Would process {len(processed_tomls)} platform TOML(s):")
            for toml_path in processed_tomls:
                logger.info(f"  - {toml_path}")
            logger.info(f"DRY RUN: Total files that would be downloaded: {total_files}")
            return True

        # Process each platform TOML individually (downloads files per platform in batches)
        total_success = True
        failed_platforms = []

        for toml_path in processed_tomls:
            platform_name = toml_path.parent.name
            logger.info(f"Processing platform: {platform_name}")

            if not process_platform_toml(toml_path, output_dir, dry_run=False):
                total_success = False
                failed_platforms.append(platform_name)
                logger.error(f"Failed to download platform: {platform_name}")
            else:
                logger.info(f"Successfully downloaded platform: {platform_name}")

        # Report overall results
        if failed_platforms:
            logger.error(f"Download completed with failures: {len(failed_platforms)}/{len(processed_tomls)} platforms failed")
            for failed_platform in failed_platforms:
                logger.error(f"  - {failed_platform}")
        else:
            logger.info(f"All {len(processed_tomls)} platforms downloaded successfully")

        return total_success

    except Exception as e:
        logger.error(f"Failed to process meta TOML {meta_path}: {e}")
        return False


def process_bios_toml(bios_path: Path, output_dir: Path, dry_run: bool = False) -> bool:
    """
    Process a BIOS TOML file that defines BIOS files for multiple platforms

    BIOS TOML format:
    site = "https://myrient.erista.me"

    [bios_platforms.PLATFORM]
    path = "URL/DIRECTORY/TO/FILES"
    directory = "bios/PLATFORM"
    files = [
        - "file1.zip",
        - "file2.zip"
    ]

    Args:
        bios_path: Path to BIOS TOML file
        output_dir: Output directory for downloads
        dry_run: If True, only show what would be done

    Returns:
        True if successful
    """
    logger = get_logger()

    try:
        # Parse TOML
        config = parse_toml_file(str(bios_path))
        site = config.get('site', 'https://myrient.erista.me')
        bios_platforms = config.get('bios_platforms', {})

        if not bios_platforms:
            logger.error(f"No BIOS platforms found in {bios_path}")
            return False

        if dry_run:
            logger.info(f"DRY RUN: Would process BIOS TOML: {bios_path}")
            total_files = 0
            for platform_name, platform_config in bios_platforms.items():
                files = platform_config.get('files', [])
                valid_files = filter_valid_files(files)
                total_files += len(valid_files)
                logger.info(f"DRY RUN: Platform {platform_name} - {len(valid_files)} files")
            logger.info(f"DRY RUN: Total BIOS files that would be downloaded: {total_files}")
            return True

        logger.info(f"Processing BIOS TOML: {bios_path.name}")

        # Process each platform
        total_success = True
        failed_platforms = []

        for platform_name, platform_config in bios_platforms.items():
            logger.info(f"Processing BIOS platform: {platform_name}")

            try:
                # Require explicit path and directory specification
                if 'path' not in platform_config:
                    logger.error(f"Platform '{platform_name}' missing required 'path' field")
                    total_success = False
                    failed_platforms.append(platform_name)
                    continue

                if 'directory' not in platform_config:
                    logger.error(f"Platform '{platform_name}' missing required 'directory' field")
                    total_success = False
                    failed_platforms.append(platform_name)
                    continue

                platform_path = platform_config['path']
                platform_dir_name = platform_config['directory']
                files = platform_config.get('files', [])

                if not files:
                    logger.warning(f"No files specified for platform {platform_name}")
                    continue

                valid_files = filter_valid_files(files)

                # Create platform subdirectory (from TOML configuration)
                platform_dir = output_dir / platform_dir_name
                platform_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created BIOS directory: {platform_dir}")

                # Download and process each file
                for filename in valid_files:
                    try:
                        # Download file
                        url = construct_url(site, platform_path, filename)
                        logger.info(f"Downloading BIOS file: {filename}")

                        # Use wget_download for single file (modify to handle single file)
                        download_urls = [url]
                        with tempfile.TemporaryDirectory() as temp_dir:
                            temp_path = Path(temp_dir)

                            # Download to temp directory first
                            if not wget_download(download_urls, temp_path):
                                logger.error(f"Failed to download {filename}")
                                continue

                            downloaded_file = temp_path / filename

                            if not downloaded_file.exists():
                                logger.error(f"Downloaded file not found: {downloaded_file}")
                                continue

                            # Check if it's a zip file and extract
                            if filename.lower().endswith('.zip'):
                                logger.info(f"Extracting BIOS files from {filename}")
                                try:
                                    with zipfile.ZipFile(downloaded_file, 'r') as zip_ref:
                                        # Extract all files to platform directory
                                        zip_ref.extractall(platform_dir)
                                        logger.info(f"Extracted {len(zip_ref.namelist())} files from {filename}")
                                except zipfile.BadZipFile as e:
                                    logger.error(f"Failed to extract {filename}: {e}")
                                    total_success = False
                            else:
                                # Copy non-zip files directly
                                import shutil
                                final_path = platform_dir / filename
                                shutil.copy2(downloaded_file, final_path)
                                logger.info(f"Copied BIOS file: {filename}")

                    except Exception as e:
                        logger.error(f"Failed to process BIOS file {filename}: {e}")
                        total_success = False

            except Exception as e:
                logger.error(f"Failed to process BIOS platform {platform_name}: {e}")
                failed_platforms.append(platform_name)
                total_success = False

        # Report results
        if failed_platforms:
            logger.error(f"BIOS download completed with failures: {len(failed_platforms)}/{len(bios_platforms)} platforms failed")
            for failed_platform in failed_platforms:
                logger.error(f"  - {failed_platform}")
        else:
            logger.info(f"All {len(bios_platforms)} BIOS platforms processed successfully")

        return total_success

    except Exception as e:
        logger.error(f"Failed to process BIOS TOML {bios_path}: {e}")
        return False


def main():
    """Main entry point"""
    # Ensure wget is available
    wget_install()

    # Setup logging with file in logs directory
    log_dir = Path.cwd() / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "rom_dl.log"
    logger = init_logger(log_file=str(log_file), verbose=True)

    # Parse arguments
    parser = argparse.ArgumentParser(
        description="ROM/file downloader using wget and URL lists",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download from collection TOML (recommended - auto-finds URL files)
  python rom_dl.py collections/sample/sample.toml -o ~/roms

  # Download only specific platforms from collection
  python rom_dl.py collections/sample/sample.toml --platforms gb gba -o ~/roms

  # Download from individual URL file
  python rom_dl.py urls.txt -o ~/roms

  # Download from platform TOML
  python rom_dl.py gb.toml -o ~/roms/gb

  # Download from meta TOML (multiple platforms)
  python rom_dl.py meta.toml -o ~/roms

  # Dry run to see what would be downloaded
  python rom_dl.py collections/sample/sample.toml --dry-run
        """
    )

    parser.add_argument(
        'input', nargs='?',
        help='Input file (TOML config, or urls.txt file)'
    )

    parser.add_argument(
        '-o', '--output',
        help='Output directory for downloads (default: ./roms/)'
    )
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Show what would be done without downloading'
    )
    parser.add_argument(
        '--platforms', nargs='*',
        help='Download only specified platforms from collection (e.g., gb gba nes)'
    )

    args = parser.parse_args()

    # Validate input - input file is required
    if not args.input:
        parser.print_help()
        return

    # Determine output directory
    if args.output:
        output_dir = Path(args.output)
    else:
        output_dir = Path('./roms/')

    # Process input file
    input_path = Path(args.input)
    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        sys.exit(1)

    if is_collection_toml(input_path):
        # Process collection TOML - parse config and process platforms
        platforms_config = parse_platforms_from_file(input_path)
        logger.info(f"Detected collection TOML with {len(platforms_config)} platforms")

        # Filter platforms if specified
        if args.platforms:
            platforms_set = set(p.lower() for p in args.platforms)
            filtered_config = {name: config for name, config in platforms_config.items()
                             if name.lower() in platforms_set}
            if not filtered_config:
                logger.error(f"None of the requested platforms {args.platforms} found in collection")
                logger.info(f"Available platforms: {list(platforms_config.keys())}")
                sys.exit(1)
            platforms_config = filtered_config
            logger.info(f"Filtering to platforms: {list(platforms_config.keys())}")

        success = process_collection_platforms(input_path, platforms_config, output_dir, args.dry_run)
    elif is_url_file(input_path):
        success = process_url_file(input_path, output_dir, args.dry_run)
    elif is_bios_toml(input_path):
        success = process_bios_toml(input_path, output_dir, args.dry_run)
    elif is_meta_toml(input_path):
        success = process_meta_toml(input_path, output_dir, args.dry_run)
    else:
        success = process_platform_toml(input_path, output_dir, args.dry_run)

    if success:
        logger.info("Download completed successfully!")
    else:
        logger.error("Download failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
