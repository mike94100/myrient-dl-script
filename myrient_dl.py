#!/usr/bin/env python3
"""
Myrient ROM Downloader - Python version
Cross-platform ROM downloader using wget
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
from utils.toml_utils import parse_toml_file, filter_valid_files
from utils.url_utils import construct_url
from utils.wget_utils import wget_download


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
    log_file = log_dir / "myrient_dl.log"
    logger = init_logger(log_file=str(log_file), verbose=True)

    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Download ROMs from Myrient based on TOML configuration files"
    )
    parser.add_argument(
        'input', nargs='?',
        help='Input TOML file (platform, meta, or BIOS config)'
    )
    parser.add_argument(
        '-o', '--output',
        help='Output directory for downloads (default: ./roms/)'
    )
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Show what would be done without downloading'
    )

    args = parser.parse_args()

    # Validate input
    if not args.input:
        parser.print_help()
        return

    input_path = Path(args.input)
    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        sys.exit(1)

    # Determine output directory
    if args.output:
        output_dir = Path(args.output)
    else:
        output_dir = Path('./roms/')

    # Process the input file
    if is_bios_toml(input_path):
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
