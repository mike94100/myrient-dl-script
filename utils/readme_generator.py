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
from utils.progress_utils import show_progress, clear_progress
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


def create_file_size_mapping(included_files: List[str], source_url: str, progress_callback=None) -> tuple[Dict[str, str], int]:
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

            # Process files with progress tracking
            for i, file in enumerate(decoded_files):
                if progress_callback:
                    progress_callback(i + 1, len(decoded_files))

                # Look for file in HTML table structure
                pattern = rf'<a[^>]*>{re.escape(file)}</a></td><td[^>]*class="size"[^>]*>([^<]+)</td>'
                match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
                if match:
                    size = match.group(1).strip()
                    if size and size != '-':
                        file_sizes[file] = size

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
        if not is_single_file:
            # Show progress bar for multiple files
            show_progress(i, total_files, f"Generating READMEs ({i}/{total_files})", force=True, show_spinner=True)

        try:
            # Parse TOML
            config = parse_toml_file(str(toml_file))

            # Only process collection TOMLs
            if 'roms' in config or 'bios' in config:
                result = generate_collection_readme(toml_file, config, is_single_file)
            else:
                logger.error(f"TOML file {toml_file} is not a valid collection (missing 'roms' or 'bios' sections)")
                result = False

        except Exception as e:
            logger.error(f"Failed to generate README for {toml_file}: {e}")
            result = False

        results.append(result)

    clear_progress()
    return results[0] if return_single else results


def generate_collection_readme(collection_path: Path, config: Dict[str, Any], is_single_file=False) -> bool:
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

    # First pass: count total files across all platforms for progress tracking
    total_files_all = 0

    def count_files_in_platform(platform_name: str, platform_config: Dict[str, Any]) -> int:
        """Count files in a platform without processing"""
        nonlocal total_files_all
        try:
            from utils.toml_utils import get_url_file_path
            url_file = get_url_file_path(str(collection_path), platform_name)
            if url_file.exists():
                included_files, _ = parse_url_file_content(url_file)
                return len(included_files)
        except:
            pass
        return 0

    print("Counting total files across all platforms...")
    for platform_name, platform_config in rom_platforms.items():
        total_files_all += count_files_in_platform(platform_name, platform_config)
    for platform_name, platform_config in bios_platforms.items():
        total_files_all += count_files_in_platform(platform_name, platform_config)

    print(f"Found {total_files_all} total files to process. Starting README generation...")

    # Second pass: process platforms with progress tracking
    rom_data = {}
    bios_data = {}
    total_rom_files = 0
    total_bios_files = 0
    total_rom_bytes = 0
    total_bios_bytes = 0
    processed_files = 0

    def file_progress_callback(files_processed, total_in_platform):
        """Update progress bar as files are processed"""
        nonlocal processed_files
        processed_files += 1
        show_progress(processed_files, total_files_all, f"Processing files", force=True, unit="files", show_speed=False)

    for platform_name, platform_config in rom_platforms.items():
        rom_data[platform_name] = process_platform_for_readme(collection_path, platform_name, platform_config, file_progress_callback)
        if rom_data[platform_name]:
            total_rom_files += rom_data[platform_name]['total_files']
            total_rom_bytes += rom_data[platform_name]['total_bytes']

    for platform_name, platform_config in bios_platforms.items():
        bios_data[platform_name] = process_platform_for_readme(collection_path, platform_name, platform_config, file_progress_callback)
        if bios_data[platform_name]:
            total_bios_files += bios_data[platform_name]['total_files']
            total_bios_bytes += bios_data[platform_name]['total_bytes']

    clear_progress()
    print("README generation complete.")

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

    # Generate URLs for scripts and collection TOML
    toml_url = f"{REPO_BASE_URL}/{collection_path}".replace('\\', '/')
    sh_script_url = f"{REPO_BASE_URL}/myrient_dl.sh"
    py_script_url = f"{REPO_BASE_URL}/myrient_dl.py"
    ps1_script_url = f"{REPO_BASE_URL}/myrient_dl.ps1"

    # Local collection path (relative)
    local_toml_path = str(collection_path).replace('\\', '/')

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

### Local Usage

If you have the myrient-dl-script repository cloned locally:

**Linux/macOS:**
```bash
./myrient_dl.sh {local_toml_path}
```

**Windows:**
```powershell
.\\myrient_dl.ps1 {local_toml_path}
```

**Python (Cross-platform):**
```bash
python myrient_dl.py {local_toml_path}
```

### Remote Usage

Run the scripts directly from the repository without downloading them first. The scripts will fetch and parse the collection TOML from the URL and allow interactive platform selection.

**Linux/macOS:**
```bash
bash <(curl -s {sh_script_url}) {toml_url}
```

**Python (Cross-platform):**
```bash
python3 <(curl -s {py_script_url}) {toml_url}
```

**Windows PowerShell:**
```powershell
powershell -Command "& {{ $script = Invoke-WebRequest -Uri '{ps1_script_url}' -UseBasicParsing; $sb = [scriptblock]::Create($script.Content); & $sb -CollectionUrl '{toml_url}' }}"
```
"""

    # Write comprehensive README
    readme_file = collection_path.parent / "README.md"
    readme_file.write_text(readme_content, encoding='utf-8')

    logger.info(f"Generated compact comprehensive collection README: {readme_file}")
    return True


def process_platform_for_readme(collection_path: Path, platform_name: str, platform_config: Dict[str, Any], progress_callback=None) -> Dict[str, Any]:
    """Process a single platform and return data needed for README generation"""
    # Get URL file path using urllist field - resolve relative to repo root
    from utils.toml_utils import get_url_file_path
    url_file = get_url_file_path(str(collection_path), platform_name)

    if not url_file.exists():
        logger = get_logger()
        logger.warning(f"URL file not found: {url_file} (resolved from {platform_config['urllist']})")
        return None

    # Parse URL file content
    included_files, excluded_files = parse_url_file_content(url_file)

    # Create file size mapping with progress callback
    source_url = platform_config.get('url', '')
    file_sizes, total_bytes = create_file_size_mapping(included_files, source_url, progress_callback)

    # Organize files by game
    decoded_files = [unquote(f) for f in included_files]
    game_groups = organize_files_by_game(decoded_files, file_sizes)

    # Build final platform data structure
    return build_platform_data_structure(
        platform_name, included_files, excluded_files,
        game_groups, total_bytes, source_url
    )
