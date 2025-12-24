#!/usr/bin/env python3
"""
Generate README - Generate README documentation from TOML configuration files
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
from utils.log_utils import init_logger, get_logger
from utils.url_utils import construct_url
from utils.wget_utils import wget_scrape
from utils.toml_utils import parse_toml_file, filter_valid_files
from utils.file_size_utils import format_file_size, calculate_total_size, parse_file_size, format_file_size_dual
from utils.progress_utils import show_progress, clear_progress

# Load config
config = parse_toml_file('config.toml')
REPO_BASE_URL = config.get('general', {}).get('repo_base_url', 'https://raw.githubusercontent.com/mike94100/myrient-dl-script/main')


def get_current_timestamp() -> str:
    """Get current timestamp in consistent format for READMEs"""
    return datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')


def write_readme_file(toml_file: Path, readme_content: str) -> None:
    """Write README content to file with consistent encoding and logging"""
    readme_file = toml_file.parent / "README.md"
    readme_file.write_text(readme_content, encoding='utf-8')
    logger = get_logger()
    logger.info(f"Generated {readme_file}")





def generate_collection_download_section(collection_path: Path, platform_name: str = None) -> str:
    """Generate download section for collection-based workflow"""
    collection_name = collection_path.name
    collection_url = f"{REPO_BASE_URL}/collections/{collection_name}/collection.toml"

    if platform_name:
        # Platform-specific download section
        return f"""## Download

### Generate URLs and Download
First generate the URL file for this platform:

```bash
python gen_urls.py scrape collections/{collection_name}/collection.toml
```

Then download the ROMs:

```bash
python myrient_dl.py --urls collections/{collection_name}/urls/{platform_name}.txt
```

Or download to a custom directory:

```bash
python myrient_dl.py --urls collections/{collection_name}/urls/{platform_name}.txt --output ~/my-roms
```

### Remote Execution (One-Command)
Download directly without installing anything:

**Linux/Mac:**
```bash
# Generate URLs and download to default location
python gen_urls.py scrape collections/{collection_name}/collection.toml && \\
python myrient_dl.py --urls collections/{collection_name}/urls/{platform_name}.txt

# Download to custom directory
python gen_urls.py scrape collections/{collection_name}/collection.toml && \\
python myrient_dl.py --urls collections/{collection_name}/urls/{platform_name}.txt --output ~/custom/path
```"""
    else:
        # Collection-level download section
        return f"""## Download

### Generate URLs and Download All Platforms
First generate URL files for all platforms in this collection:

```bash
python gen_urls.py scrape collections/{collection_name}/collection.toml
```

Then download all ROMs:

```bash
python myrient_dl.py --urls collections/{collection_name}/urls/
```

Or download to a custom directory:

```bash
python myrient_dl.py --urls collections/{collection_name}/urls/ --output ~/my-roms
```

### Remote Execution (One-Command)
Download directly without installing anything:

**Linux/Mac:**
```bash
# Generate URLs and download all platforms to default location
python gen_urls.py scrape collections/{collection_name}/collection.toml && \\
python myrient_dl.py --urls collections/{collection_name}/urls/

# Download to custom directory
python gen_urls.py scrape collections/{collection_name}/collection.toml && \\
python myrient_dl.py --urls collections/{collection_name}/urls/ --output ~/custom/path
```"""


def extract_file_sizes(html: str, files: List[str]) -> Dict[str, str]:
    """Extract file sizes from Myrient HTML"""
    sizes = {}

    for file in files:
        # Look for file in HTML table structure
        # Pattern: <tr><td class="link"><a href="...">filename</a></td><td class="size">SIZE</td>
        pattern = rf'<a[^>]*>{re.escape(file)}</a></td><td[^>]*class="size"[^>]*>([^<]+)</td>'
        match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
        if match:
            size = match.group(1).strip()
            if size and size != '-':
                sizes[file] = size

    return sizes


def parse_game_info(filename: str) -> tuple:
    """Parse game name and tags from filename"""
    # Remove extension
    name = re.sub(r'\.[^.]+$', '', filename)

    # Extract game name (everything before first parenthesis)
    game_name = name
    paren_match = re.search(r'\s*\(', name)
    if paren_match:
        game_name = name[:paren_match.start()].strip()

    # Extract tags (everything in parentheses) - preserve individual groups
    tags_match = re.findall(r'\([^)]+\)', name)
    tags = ' '.join(tags_match)

    return game_name, tags


def parse_url_file_content(url_file: Path) -> tuple[List[str], List[str]]:
    """Parse URL file and return (included_files, excluded_files)"""
    included_files = []
    excluded_files = []

    try:
        with open(url_file, 'r', encoding='utf-8') as f:
            url_lines = [line.strip() for line in f if line.strip()]
    except Exception as e:
        logger = get_logger()
        logger.error(f"Failed to read URL file {url_file}: {e}")
        return [], []

    for url_line in url_lines:
        if url_line.startswith('#'):
            # Excluded file - extract filename from commented URL
            if url_line.startswith('#http'):
                url_part = url_line[1:]  # Remove # prefix
                filename = url_part.split('/')[-1]
                if filename:
                    excluded_files.append(filename)
        else:
            # Included file - extract filename from URL
            if url_line.startswith('http'):
                filename = url_line.split('/')[-1]
                if filename:
                    included_files.append(filename)

    return included_files, excluded_files


def create_file_size_mapping(included_files: List[str], source_url: str) -> tuple[Dict[str, str], int]:
    """Scrape file sizes and return (file_sizes, total_bytes)"""
    file_sizes = {}
    total_bytes = 0

    if included_files and source_url:
        logger = get_logger()
        logger.info(f"Scraping file sizes from: {source_url}")
        html = wget_scrape(source_url)
        if html:
            # URL-decode filenames before searching in HTML
            decoded_files = [unquote(f) for f in included_files]
            file_sizes = extract_file_sizes(html, decoded_files)
            total_bytes = calculate_total_size(file_sizes)

    return file_sizes, total_bytes


def organize_files_by_game(decoded_files: List[str], file_sizes: Dict[str, str]) -> Dict[str, List[Dict]]:
    """Group files by game name and return structured data"""
    # Create a mapping from decoded filenames back to original encoded filenames
    decoded_to_encoded = {unquote(f): f for f in decoded_files}

    # Group files by game name for better organization
    game_groups = {}
    for decoded_filename in decoded_files:
        encoded_filename = decoded_to_encoded.get(decoded_filename, decoded_filename)
        game_name, tags = parse_game_info(decoded_filename)
        size_bytes = 0
        size_str = file_sizes.get(decoded_filename, 'Unknown')

        # Try to parse size for sorting/grouping
        try:
            if size_str != 'Unknown' and size_str != '-':
                size_bytes = parse_file_size(size_str)
        except:
            pass

        if game_name not in game_groups:
            game_groups[game_name] = []
        game_groups[game_name].append({
            'filename': encoded_filename,  # Use encoded for display
            'decoded_filename': decoded_filename,  # Use decoded for lookup
            'tags': tags,
            'size': size_str,
            'size_bytes': size_bytes
        })

    return game_groups


def build_platform_data_structure(platform_name: str, included_files: List[str],
                                excluded_files: List[str], game_groups: Dict[str, List[Dict]],
                                total_bytes: int, source_url: str) -> Dict[str, Any]:
    """Assemble final platform data structure"""
    return {
        'platform_name': platform_name,
        'included_files': included_files,
        'excluded_files': excluded_files,
        'game_groups': game_groups,
        'total_files': len(included_files),
        'total_bytes': total_bytes,
        'source_url': source_url
    }


def extract_base_directory(platform_configs: Dict[str, Any]) -> str:
    """Extract base directory from platform configurations"""
    for platform_config in platform_configs.values():
        directory = platform_config.get('directory', '')
        if directory and '/' in directory:
            return directory.split('/')[0]
    return "roms"


def generate_readme(toml_files, max_workers: int = 1, request_delay: float = 1.0):
    """Generate READMEs (single file or list) with optional parallel processing"""
    from typing import Union
    from utils.log_utils import disable_console_logging, enable_console_logging

    # Handle single file vs list
    if isinstance(toml_files, (str, Path)):
        toml_files = [Path(toml_files)]
        return_single = True
    else:
        toml_files = list(toml_files)
        return_single = False

    logger = get_logger()

    # Disable console logging during batch README generation to keep progress bar clean
    if len(toml_files) > 1:
        disable_console_logging()

    try:
        def generate_single_readme(toml_file: Path) -> bool:
            """Generate README for a single TOML file"""
            try:
                # Parse TOML
                config = parse_toml_file(str(toml_file))

                # Check if this is a collection TOML (has platforms section)
                if 'platforms' in config:
                    return generate_collection_readme(toml_file, config)

                # Check if this is a meta TOML
                if 'platform_tomls' in config:
                    return generate_meta_readme(toml_file, config)

                # Generate platform README (legacy support)
                return generate_platform_readme(toml_file, config)

            except Exception as e:
                logger.error(f"Failed to generate README for {toml_file}: {e}")
                return False

        if max_workers <= 1 or len(toml_files) == 1:
            # Sequential processing
            results = []
            for i, toml_file in enumerate(toml_files, 1):
                show_progress(i, len(toml_files), "Generating READMEs", force=True)
                result = generate_single_readme(toml_file)
                results.append(result)
            clear_progress()

            return results[0] if return_single else results

        # Parallel processing
        results = []
        completed = 0
        total = len(toml_files)
        last_request_time = 0

        def generate_with_rate_limit(toml_file: Path) -> bool:
            """Generate README with rate limiting"""
            nonlocal last_request_time

            # Enforce minimum delay between requests
            current_time = time.time()
            time_since_last = current_time - last_request_time
            if time_since_last < request_delay:
                sleep_time = request_delay - time_since_last
                time.sleep(sleep_time)

            try:
                result = generate_single_readme(toml_file)
                last_request_time = time.time()
                return result
            except Exception as e:
                logger.error(f"Failed to generate README for {toml_file}: {e}")
                return False

        def progress_callback(future):
            """Update progress when a task completes"""
            nonlocal completed
            completed += 1
            show_progress(completed, total, "Generating READMEs", force=True)

        logger.info(f"Generating READMEs using {max_workers} parallel workers")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            futures = [executor.submit(generate_with_rate_limit, tf) for tf in toml_files]

            # Add progress callback to each future
            for future in futures:
                future.add_done_callback(progress_callback)

            # Collect results as they complete
            for future in as_completed(futures):
                try:
                    result = future.result(timeout=300)  # 5 minute timeout per README
                    results.append(result)
                except Exception as e:
                    logger.error(f"README generation failed: {e}")
                    results.append(False)

        clear_progress()
        return results[0] if return_single else results
    finally:
        # Re-enable console logging after batch processing
        if len(toml_files) > 1:
            enable_console_logging()


def generate_collection_readme(collection_path: Path, config: Dict[str, Any]) -> bool:
    """Generate comprehensive README for a collection TOML with all platform details"""
    logger = get_logger()

    platforms = config.get('platforms', {})
    if not platforms:
        logger.error(f"No platforms found in collection {collection_path}")
        return False

    collection_name = collection_path.name
    logger.info(f"Generating comprehensive README for collection '{collection_name}' with {len(platforms)} platforms")

    # Generate comprehensive collection README with all platform details
    return generate_comprehensive_collection_readme(collection_path, platforms)


def generate_comprehensive_collection_readme(collection_path: Path, platforms: Dict[str, Any]) -> bool:
    """Generate a README with platform details and folder structure"""
    logger = get_logger()

    collection_name = collection_path.name

    # Process all platforms and collect their data
    platform_data = {}
    total_files_all = 0
    total_bytes_all = 0

    for platform_name, platform_config in platforms.items():
        platform_data[platform_name] = process_platform_for_readme(collection_path, platform_name, platform_config)

        if platform_data[platform_name]:
            total_files_all += platform_data[platform_name]['total_files']
            total_bytes_all += platform_data[platform_name]['total_bytes']

    # Generate hierarchical directory structure
    folder_structure = "```\nroms/\n"

    for i, platform_name in enumerate(sorted(platforms.keys())):
        if platform_name not in platform_data or not platform_data[platform_name]:
            continue

        platform_info = platform_data[platform_name]
        platform_config = platforms[platform_name]
        directory = platform_config.get('directory', f'{platform_name}')

        # Extract just the platform part (after the base directory)
        platform_part = directory.split('/')[-1] if '/' in directory else directory

        file_count = platform_info['total_files']
        size_formatted = format_file_size(platform_info['total_bytes']) if platform_info['total_bytes'] > 0 else "Unknown"

        # Use tree symbols: ├── for middle items, └── for last item
        prefix = "├──" if i < len(platforms) - 1 else "└──"
        folder_structure += f"{prefix} {platform_part}/ ({file_count} files, {size_formatted})\n"

    folder_structure += "```\n"

    # Generate collapsible ROM files sections
    rom_files_section = ""

    for platform_name in sorted(platforms.keys()):
        if platform_name not in platform_data or not platform_data[platform_name]:
            continue

        platform_info = platform_data[platform_name]
        platform_config = platforms[platform_name]
        directory = platform_config.get('directory', f'{platform_name}')

        file_count = platform_info['total_files']
        size_formatted = format_file_size(platform_info['total_bytes']) if platform_info['total_bytes'] > 0 else "Unknown"

        # Start collapsible section for this platform (show only platform name)
        platform_part = directory.split('/')[-1] if '/' in directory else directory
        rom_files_section += f"""<details>
<summary>{platform_part}</summary>

"""

        # List all files for this platform
        for game_name in sorted(platform_info['game_groups'].keys()):
            files = platform_info['game_groups'][game_name]

            for file_info in files:
                # Use decoded filename for display
                filename_decoded = file_info['decoded_filename']
                size_display = file_info['size']
                rom_files_section += f"  - {filename_decoded} ({size_display})\n"

        rom_files_section += "</details>\n\n"

    # Format total collection size
    total_size_formatted = format_file_size_dual(total_bytes_all)

    # Generate download section
    download_section = generate_collection_download_section(collection_path)

    # Combine everything into compact comprehensive README
    readme_content = f"""# {collection_name.upper()} ROM Collection

This collection contains ROMs for multiple gaming platforms with intelligent filtering.

## Metadata

- **Generated**: {get_current_timestamp()}
- **Total Platforms**: {len(platforms)}
- **Total Files**: {total_files_all}
- **Total Size**: {total_size_formatted}

## Directory Structure

{folder_structure}

## ROM Files

{rom_files_section}

## Download

### Generate URLs and Download All Platforms
```bash
# Generate URL files for all platforms
python gen_urls.py scrape collections/{collection_name}/collection.toml

# Download all ROMs to default directory
python myrient_dl.py --urls collections/{collection_name}/urls/
```

### Individual Platform Download
```bash
# Generate and download specific platform
python gen_urls.py scrape collections/{collection_name}/collection.toml
python myrient_dl.py --urls collections/{collection_name}/urls/gb.txt --output ~/roms/gb
```

### Remote One-Command Download
**Linux/Mac:**
```bash
# Download all platforms to ~/Downloads/roms
python gen_urls.py scrape collections/{collection_name}/collection.toml && \\
python myrient_dl.py --urls collections/{collection_name}/urls/ --output ~/Downloads/roms
```
"""

    # Write comprehensive README
    readme_file = collection_path.parent / "README.md"
    readme_file.write_text(readme_content, encoding='utf-8')

    logger.info(f"Generated compact comprehensive collection README: {readme_file}")
    return True


def process_platform_for_readme(collection_path: Path, platform_name: str, platform_config: Dict[str, Any]) -> Dict[str, Any]:
    """Process a single platform and return data needed for README generation"""
    # Get URL file path
    urls_dir = collection_path.parent / "urls"
    url_file = urls_dir / f"{platform_name}.txt"

    if not url_file.exists():
        logger = get_logger()
        logger.warning(f"URL file not found: {url_file}")
        return None

    # Parse URL file content
    included_files, excluded_files = parse_url_file_content(url_file)

    # Create file size mapping
    source_url = platform_config.get('url', '')
    file_sizes, total_bytes = create_file_size_mapping(included_files, source_url)

    # Organize files by game
    decoded_files = [unquote(f) for f in included_files]
    game_groups = organize_files_by_game(decoded_files, file_sizes)

    # Build final platform data structure
    return build_platform_data_structure(
        platform_name, included_files, excluded_files,
        game_groups, total_bytes, source_url
    )





def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Generate README.md files from TOML configuration files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate README for a single TOML file
  python generate_readme.py gb.toml

  # Generate READMEs for all TOML files in current directory
  python generate_readme.py .

  # Generate READMEs with parallel processing
  python generate_readme.py . --parallel 4

  # Generate READMEs with custom request delay
  python generate_readme.py . --delay 2.0
        """
    )

    parser.add_argument(
        'toml_files', nargs='+',
        help='TOML file(s) or directory containing TOML files to generate READMEs for'
    )
    parser.add_argument(
        '--parallel', '-p', type=int, default=1, metavar='N',
        help='Generate READMEs in parallel with N workers (default: 1)'
    )
    parser.add_argument(
        '--delay', '-d', type=float, default=1.0, metavar='SECONDS',
        help='Delay between requests in seconds (default: 1.0)'
    )
    parser.add_argument(
        '--verbose', '-v', action='store_true',
        help='Enable verbose output'
    )
    parser.add_argument(
        '--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='INFO',
        help='Set logging level (default: INFO)'
    )

    args = parser.parse_args()

    # Setup logging
    log_dir = Path.cwd() / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "generate_readme.log"
    logger = init_logger(log_file=str(log_file), verbose=args.verbose, level=getattr(logging, args.log_level.upper(), logging.INFO))

    # Collect TOML files
    toml_files = []
    for path_str in args.toml_files:
        path = Path(path_str)
        if path.is_dir():
            # Find all .toml files in directory
            toml_files.extend(path.glob("*.toml"))
        elif path.is_file() and path.suffix == '.toml':
            toml_files.append(path)
        else:
            logger.error(f"Invalid path: {path} (must be .toml file or directory containing .toml files)")
            sys.exit(1)

    if not toml_files:
        logger.error("No TOML files found")
        sys.exit(1)

    # Remove duplicates while preserving order
    seen = set()
    toml_files = [f for f in toml_files if str(f) not in seen and not seen.add(str(f))]

    logger.info(f"Generating READMEs for {len(toml_files)} TOML file(s)")

    # Generate READMEs
    results = generate_readme(toml_files, max_workers=args.parallel, request_delay=args.delay)

    # Report results
    success_count = sum(results)
    fail_count = len(results) - success_count

    if success_count > 0:
        logger.info(f"README generation completed: {success_count} successful")
    if fail_count > 0:
        logger.error(f"README generation failed: {fail_count} failed")
        sys.exit(1)

    logger.info("All READMEs generated successfully!")


if __name__ == "__main__":
    main()
