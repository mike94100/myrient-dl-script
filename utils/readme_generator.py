#!/usr/bin/env python3
"""
Generate README - Generate README documentation from TOML configuration files
"""

import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any
from urllib.parse import unquote

# Import utilities
from utils.log_utils import get_logger
from utils.wget_utils import wget_scrape
from utils.toml_utils import parse_toml_file
from utils.file_size_utils import format_file_size, calculate_total_size, format_file_size_dual
from utils.file_parsing_utils import parse_url_file_content, parse_game_info, write_readme_file, organize_files_by_game, build_platform_data_structure
import threading

# Load config
config = parse_toml_file('config.toml')
REPO_BASE_URL = config.get('general', {}).get('repo_base_url', 'https://raw.githubusercontent.com/mike94100/myrient-dl-script/main')


def get_current_timestamp() -> str:
    """Get current timestamp in consistent format for READMEs"""
    return datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')



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


def generate_readme(toml_files):
    """Generate READMEs for collection TOML files"""
    # Handle single file vs list
    if isinstance(toml_files, (str, Path)):
        toml_files = [Path(toml_files)]
        return_single = True
    else:
        toml_files = list(toml_files)
        return_single = False

    logger = get_logger()

    results = []
    total_files = len(toml_files)
    is_single_file = total_files == 1

    stop_event = threading.Event()

    for i, toml_file in enumerate(toml_files, 1):
        if is_single_file:
            # Show spinner for single file
            spinner_thread = threading.Thread(target=show_spinner, args=(f"Generating README for {toml_file.name}", stop_event), daemon=True)
            spinner_thread.start()
        else:
            # Show progress bar for multiple files
            show_progress(i, total_files, f"Generating READMEs ({i}/{total_files})", force=True, show_spinner=True)

        try:
            # Parse TOML
            config = parse_toml_file(str(toml_file))

            # Only process collection TOMLs
            if 'roms' in config or 'bios' in config:
                result = generate_collection_readme(toml_file, config)
            else:
                logger.error(f"TOML file {toml_file} is not a valid collection (missing 'roms' or 'bios' sections)")
                result = False

        except Exception as e:
            logger.error(f"Failed to generate README for {toml_file}: {e}")
            result = False

        results.append(result)

        # Stop the spinner for single file processing
        if is_single_file:
            stop_event.set()
            if 'spinner_thread' in locals():
                spinner_thread.join(timeout=0.1)

    clear_progress()
    return results[0] if return_single else results


def generate_collection_readme(collection_path: Path, config: Dict[str, Any]) -> bool:
    """Generate comprehensive README for a collection TOML with all platform details"""
    logger = get_logger()

    # Collect platforms from roms and bios sections
    platforms = {}
    if 'roms' in config:
        platforms.update(config['roms'])
    if 'bios' in config:
        platforms.update(config['bios'])

    if not platforms:
        logger.error(f"No platforms found in collection {collection_path}")
        return False

    collection_name = collection_path.name
    logger.info(f"Generating comprehensive README for collection '{collection_name}' with {len(platforms)} platforms")

    # Separate ROM and BIOS platforms
    rom_platforms = {}
    bios_platforms = {}

    if 'roms' in config:
        rom_platforms.update(config['roms'])
    if 'bios' in config:
        bios_platforms.update(config['bios'])

    # Process all platforms and collect their data
    rom_data = {}
    bios_data = {}
    total_rom_files = 0
    total_bios_files = 0
    total_rom_bytes = 0
    total_bios_bytes = 0

    for platform_name, platform_config in rom_platforms.items():
        rom_data[platform_name] = process_platform_for_readme(collection_path, platform_name, platform_config)
        if rom_data[platform_name]:
            total_rom_files += rom_data[platform_name]['total_files']
            total_rom_bytes += rom_data[platform_name]['total_bytes']

    for platform_name, platform_config in bios_platforms.items():
        bios_data[platform_name] = process_platform_for_readme(collection_path, platform_name, platform_config)
        if bios_data[platform_name]:
            total_bios_files += bios_data[platform_name]['total_files']
            total_bios_bytes += bios_data[platform_name]['total_bytes']

    # Generate hierarchical directory structure
    folder_structure = "```\n"

    # Build directory tree from actual directory specifications
    all_dirs = {}

    # Collect all directories from ROM platforms
    for platform_name, platform_config in rom_platforms.items():
        directory = platform_config.get('directory', platform_name)
        if directory not in all_dirs:
            all_dirs[directory] = {'type': 'rom', 'platform': platform_name}
        elif platform_name in rom_data and rom_data[platform_name]:
            all_dirs[directory] = {'type': 'rom', 'platform': platform_name}

    # Collect all directories from BIOS platforms
    for platform_name, platform_config in bios_platforms.items():
        directory = platform_config.get('directory', platform_name)
        if directory not in all_dirs:
            all_dirs[directory] = {'type': 'bios', 'platform': platform_name}
        elif platform_name in bios_data and bios_data[platform_name]:
            all_dirs[directory] = {'type': 'bios', 'platform': platform_name}

    # Generate directory tree
    if all_dirs:
        # Sort directories to create a hierarchical structure
        sorted_dirs = sorted(all_dirs.keys())

        # Create a tree structure
        tree = {}
        for directory in sorted_dirs:
            parts = directory.split('/')
            current = tree
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            leaf = parts[-1]
            current[leaf] = all_dirs[directory]

        def render_tree(node, prefix="", is_last=True):
            lines = []
            if isinstance(node, dict):
                items = list(node.items())
                for i, (name, subtree) in enumerate(items):
                    is_last_item = (i == len(items) - 1)
                    if isinstance(subtree, dict) and ('type' in subtree or 'platform' in subtree):
                        # This is a leaf with platform info
                        platform_info = subtree
                        platform_name = platform_info['platform']
                        platform_type = platform_info['type']

                        if platform_type == 'rom' and platform_name in rom_data and rom_data[platform_name]:
                            data = rom_data[platform_name]
                        elif platform_type == 'bios' and platform_name in bios_data and bios_data[platform_name]:
                            data = bios_data[platform_name]
                        else:
                            data = None

                        if data:
                            file_count = data['total_files']
                            size_formatted = format_file_size(data['total_bytes']) if data['total_bytes'] > 0 else "Unknown"
                            lines.append(f"{prefix}{'└──' if is_last_item else '├──'} {name}/ ({file_count} files, {size_formatted})")
                        else:
                            lines.append(f"{prefix}{'└──' if is_last_item else '├──'} {name}/")
                    else:
                        # This is a directory
                        lines.append(f"{prefix}{'└──' if is_last_item else '├──'} {name}/")
                        new_prefix = prefix + ("    " if is_last_item else "│   ")
                        lines.extend(render_tree(subtree, new_prefix, is_last_item))

            return lines

        folder_structure += '\n'.join(render_tree(tree))
        folder_structure += '\n'

    folder_structure += "```\n"

    # Generate collapsible files sections
    rom_files_section = ""
    bios_files_section = ""

    # ROM files section
    if rom_platforms:
        rom_files_section += "## ROM Files\n\n"
        for platform_name in sorted(rom_platforms.keys()):
            if platform_name not in rom_data or not rom_data[platform_name]:
                continue

            platform_info = rom_data[platform_name]
            platform_config = rom_platforms[platform_name]
            directory = platform_config.get('directory', f'roms/{platform_name}')

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

    # BIOS files section
    if bios_platforms:
        bios_files_section += "## BIOS Files\n\n"
        for platform_name in sorted(bios_platforms.keys()):
            if platform_name not in bios_data or not bios_data[platform_name]:
                continue

            platform_info = bios_data[platform_name]
            platform_config = bios_platforms[platform_name]
            directory = platform_config.get('directory', f'bios/{platform_name}')

            file_count = platform_info['total_files']
            size_formatted = format_file_size(platform_info['total_bytes']) if platform_info['total_bytes'] > 0 else "Unknown"

            # Start collapsible section for this platform (show only platform name)
            platform_part = directory.split('/')[-1] if '/' in directory else directory
            bios_files_section += f"""<details>
<summary>{platform_part}</summary>

"""

            # List all files for this platform
            for game_name in sorted(platform_info['game_groups'].keys()):
                files = platform_info['game_groups'][game_name]

                for file_info in files:
                    # Use decoded filename for display
                    filename_decoded = file_info['decoded_filename']
                    size_display = file_info['size']
                    bios_files_section += f"  - {filename_decoded} ({size_display})\n"

            bios_files_section += "</details>\n\n"

    # Combine ROM and BIOS sections
    files_section = rom_files_section + bios_files_section

    # Format total collection size
    total_files_all = total_rom_files + total_bios_files
    total_bytes_all = total_rom_bytes + total_bios_bytes
    total_size_formatted = format_file_size_dual(total_bytes_all)

    # Generate script paths for remote execution
    script_base = str(collection_path).replace('.toml', '').replace('\\', '/')
    sh_script_url = f"{REPO_BASE_URL}/{script_base}_dl.sh"
    ps1_script_url = f"{REPO_BASE_URL}/{script_base}_dl.ps1"

    # Combine everything into compact comprehensive README
    readme_content = f"""# {collection_path.name.upper().replace('.TOML', '')} ROM Collection

This collection contains ROMs for multiple gaming platforms.

## Metadata

- **Generated**: {get_current_timestamp()}
- **ROM Platforms**: {len(rom_platforms)}{f"\n- **BIOS Platforms**: {len(bios_platforms)}" if bios_platforms else ""}
- **Total Files**: {total_files_all}
- **Total Size**: {total_size_formatted}

## Directory Structure

{folder_structure}

{files_section}

## Download

Download and run the interactive script directly from GitHub:

**Linux/Mac:**
```bash
bash <(curl -s {sh_script_url})
```

**Windows:**
```powershell
powershell -Command "& {{ Invoke-WebRequest -Uri '{ps1_script_url}' -OutFile 'temp_dl.ps1'; & .\\temp_dl.ps1; Remove-Item 'temp_dl.ps1' }}"
```
"""

    # Write comprehensive README
    readme_file = collection_path.parent / "README.md"
    readme_file.write_text(readme_content, encoding='utf-8')

    logger.info(f"Generated compact comprehensive collection README: {readme_file}")
    return True


def process_platform_for_readme(collection_path: Path, platform_name: str, platform_config: Dict[str, Any]) -> Dict[str, Any]:
    """Process a single platform and return data needed for README generation"""
    # Get URL file path using urllist field
    url_file = collection_path.parent / platform_config['urllist']

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


# Import missing functions that were in the original gen_readme.py
def show_spinner(message, stop_event=None, interval=0.1):
    """Show a simple spinner for single file processing"""
    import time
    import itertools

    spinner = itertools.cycle(['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'])

    print(f"{message} ", end='', flush=True)

    while not stop_event.is_set():
        print(f"\r{message} {next(spinner)}", end='', flush=True)
        time.sleep(interval)

    print(f"\r{message} ✓")


def show_progress(current, total, message="", force=False, show_spinner=False):
    """Show progress bar for multiple file processing"""
    import sys
    if show_spinner and not force:
        return  # Don't show progress bar for spinner mode

    percent = int(100 * current / total)
    bar = '█' * (percent // 2) + '░' * (50 - percent // 2)
    sys.stdout.write(f"\r{message} [{bar}] {current}/{total} ({percent}%)")
    sys.stdout.flush()


def clear_progress():
    """Clear the progress bar line"""
    import sys
    sys.stdout.write('\r' + ' ' * 80 + '\r')
    sys.stdout.flush()
