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


def get_current_timestamp() -> str:
    """Get current timestamp in consistent format for READMEs"""
    return datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')


def write_readme_file(toml_file: Path, readme_content: str) -> None:
    """Write README content to file with consistent encoding and logging"""
    readme_file = toml_file.parent / "README.md"
    readme_file.write_text(readme_content, encoding='utf-8')
    logger = get_logger()
    logger.info(f"Generated {readme_file}")




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

                # Check if this is a meta TOML
                if 'platform_tomls' in config:
                    return generate_meta_readme(toml_file, config)

                # Generate platform README
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


def generate_platform_readme(toml_file: Path, config: Dict[str, Any]) -> bool:
    """Generate README for a platform TOML"""
    logger = get_logger()

    # Extract configuration
    site = config.get('site', '')
    path_directory = config.get('path_directory', '')
    directory = config.get('directory', '')
    files = config.get('files', [])

    if not all([site, path_directory, directory]):
        logger.error("Missing required fields in TOML")
        return False

    # Generate platform name
    platform_name = Path(directory).name.upper() or "UNKNOWN"

    # Construct source URL
    source_url_encoded = construct_url(site, path_directory)
    source_url_decoded = unquote(source_url_encoded)  # Decoded for display

    # Scrape file sizes
    logger.info(f"Scraping file sizes from: {source_url_encoded}")
    html = wget_scrape(source_url_encoded)
    file_sizes = {}
    total_bytes = 0

    if html:
        file_sizes = extract_file_sizes(html, files)
        total_bytes = calculate_total_size(file_sizes)

    # Format total size in both IEC (binary) and SI (decimal) formats
    total_size_formatted = format_file_size_dual(total_bytes)

    # Generate file table
    file_table = "| GAME | TAGS | SIZE |\n| --- | --- | --- |\n"
    for file in files:
        if file.startswith('#'):
            continue  # Skip commented files

        game_name, tags = parse_game_info(file)
        size = file_sizes.get(file, '-')
        file_table += f"| {game_name} | {tags} | {size} |\n"

    # Generate README content
    repo_root = Path.cwd()
    toml_relative_path = toml_file.relative_to(repo_root)
    toml_url = f"{REPO_BASE_URL}/{toml_relative_path}"

    bootstrap_sh_url = f"{REPO_BASE_URL}/download_roms.sh"
    bootstrap_bat_url = f"{REPO_BASE_URL}/download_roms.bat"

    readme_content = f"""# {platform_name} ROM Collection

This collection contains ROMs for the {platform_name}.

## Metadata

- **Generated**: {get_current_timestamp()}
- **Source URL**: [{source_url_decoded}]({source_url_encoded})
- **Total Files**: {len(filter_valid_files(files))}
- **Total Size**: {total_size_formatted}
- **Platform Directory**: {directory}

## ROM Files
<details>
<summary>The following ROM files are included in this collection:</summary>

{file_table}
</details>

## Download

### Local Execution
To download all ROMs in this collection locally:

```bash
python myrient_dl.py "{toml_file.name}"
```

Or download to a custom directory:

```bash
python myrient_dl.py -o /path/to/directory "{toml_file.name}"
```

### Remote Execution (One-Command)
Download directly without installing anything:

**Linux/Mac:**
```bash
wget -q -O - {bootstrap_sh_url} | bash -s -- --toml "{toml_url}"
```

**Windows:**
```batch
powershell -c "& {{ $s=iwr '{bootstrap_bat_url}'; $t=New-TemporaryFile; $t=$t.FullName+'.bat'; [IO.File]::WriteAllText($t,$s); & $t --toml '{toml_url}'; del $t }}"
```
"""

    # Write README
    write_readme_file(toml_file, readme_content)

    return True


def generate_meta_readme(toml_file: Path, config: Dict[str, Any]) -> bool:
    """Generate README for a meta TOML"""
    logger = get_logger()

    platform_tomls = config.get('platform_tomls', [])
    if not platform_tomls:
        logger.error("No platform_tomls found in meta TOML")
        return False

    # Collect platform TOML files that need READMEs generated
    toml_files_to_generate = []

    # Generate READMEs for individual platforms first
    total_files = 0
    total_collection_bytes = 0
    platform_summaries = []

    for platform_ref in platform_tomls:
        # Resolve platform TOML path
        if platform_ref.startswith('/'):
            platform_path = Path(platform_ref)
        else:
            platform_path = toml_file.parent / platform_ref

        if not platform_path.exists():
            continue

        # Always regenerate platform READMEs when updating meta TOML
        toml_files_to_generate.append(platform_path)

        # Parse platform TOML for summary
        try:
            platform_config = parse_toml_file(str(platform_path))
            platform_name = platform_path.stem.upper()
            directory = platform_config.get('directory', '')
            files = platform_config.get('files', [])

            file_count = len(filter_valid_files(files))
            total_files += file_count

            # Size info will be populated after README generation
            size_info = "Unknown"
            platform_bytes = 0

            platform_summaries.append({
                'name': platform_name,
                'files': file_count,
                'size': size_info,
                'directory': directory,
                'readme_path': platform_path.parent / "README.md",
                'bytes': platform_bytes
            })

        except Exception as e:
            logger.warning(f"Failed to process platform {platform_ref}: {e}")

    # Generate READMEs for all platforms
    if toml_files_to_generate:
        logger.info(f"Generating READMEs for {len(toml_files_to_generate)} platforms...")
        generate_readme(toml_files_to_generate)

    # Now collect size information from the newly generated READMEs
    total_collection_bytes = 0
    for summary in platform_summaries:
        readme_path = summary['readme_path']
        if readme_path.exists():
            try:
                readme_content = readme_path.read_text(encoding='utf-8')
                size_match = re.search(r'\*\*Total Size\*\*: ([^\n]+)', readme_content)
                if size_match:
                    size_info = size_match.group(1).strip()
                    summary['size'] = size_info

                    # Extract byte count for summingfrom IEC format
                    bytes_match = re.search(r'(\d+(?:\.\d+)?)\s*(B|KiB|MiB|GiB|TiB)', size_info)
                    if bytes_match:
                        iec_part = f"{bytes_match.group(1)} {bytes_match.group(2)}"
                        try:
                            platform_bytes = parse_file_size(iec_part)
                            summary['bytes'] = platform_bytes
                            total_collection_bytes += platform_bytes
                        except ValueError:
                            pass  # Keep platform_bytes as 0
            except Exception as e:
                logger.warning(f"Could not read size from {readme_path}: {e}")

    # Generate summary table
    table = "| PLATFORM | FILES | SIZE | DIRECTORY |\n| --- | --- | --- | --- |\n"
    for summary in platform_summaries:
        readme_rel_path = summary['readme_path'].relative_to(toml_file.parent)
        table += f"| [{summary['name']}]({readme_rel_path}) | {summary['files']} Files | {summary['size']} | {summary['directory']} |\n"

    # Format total collection size
    total_size_formatted = format_file_size_dual(total_collection_bytes)

    # Generate meta README
    repo_root = Path.cwd()
    toml_relative_path = toml_file.relative_to(repo_root)
    toml_url = f"{REPO_BASE_URL}/{toml_relative_path}"
    bootstrap_sh_url = f"{REPO_BASE_URL}/download_roms.sh"
    bootstrap_bat_url = f"{REPO_BASE_URL}/download_roms.bat"

    readme_content = f"""# Multi-Platform ROM Collection

This collection contains ROMs for multiple gaming platforms.

## Metadata

- **Generated**: {get_current_timestamp()}
- **Total Platforms**: {len(platform_summaries)}
- **Total Files**: {total_files}
- **Total Size**: {total_size_formatted}

## Included Platforms

{table}

## Download

### Local Execution
To download all platforms in this collection locally:

```bash
python myrient_dl.py "{toml_file.name}"
```

Or download to a custom directory:

```bash
python myrient_dl.py -o /path/to/directory "{toml_file.name}"
```

### Remote Execution (One-Command)
Download directly without installing anything:

**Linux/Mac:**
```bash
wget -q -O - {bootstrap_sh_url} | bash -s -- --toml "{toml_url}"
```

**Windows:**
```batch
powershell -c "& {{ $s=iwr '{bootstrap_bat_url}'; $t=New-TemporaryFile; $t=$t.FullName+'.bat'; [IO.File]::WriteAllText($t,$s); & $t --toml '{toml_url}'; del $t }}"
```
"""

    # Write README
    write_readme_file(toml_file, readme_content)

    return True


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
