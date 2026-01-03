#!/usr/bin/env python3
"""
Myrient Download Script
Downloads files from any TOML collection configuration
"""

import os
import sys
import tempfile
import zipfile
import subprocess
import urllib.request
import urllib.error
import argparse
import tomllib
from pathlib import Path
from typing import Dict, Any

def fetch_toml(url: str) -> Dict[str, Any]:
    """Fetch and parse TOML from URL or local file"""
    try:
        if url.startswith(('http://', 'https://')):
            # Remote URL
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=30) as response:
                toml_content = response.read()
                return tomllib.loads(toml_content.decode('utf-8'))
        else:
            # Local file
            with open(url, 'rb') as f:
                return tomllib.load(f)
    except Exception as e:
        print(f"Error fetching/parsing TOML from {url}: {e}", file=sys.stderr)
        sys.exit(1)

def resolve_relative_url(toml_url: str, relative_path: str) -> str:
    """Resolve relative path against TOML URL or local path"""
    if toml_url.startswith(('http://', 'https://')):
        # Remote URL
        if toml_url.startswith('https://raw.githubusercontent.com/'):
            # GitHub raw URL: https://raw.githubusercontent.com/user/repo/branch/...
            # Extract repo root: https://raw.githubusercontent.com/user/repo/branch/
            parts = toml_url.split('/')
            if len(parts) >= 6:
                repo_root = '/'.join(parts[:6])  # https://raw.githubusercontent.com/user/repo/branch
                resolved = f"{repo_root}/{relative_path}"
                return resolved
        # Generic remote URL: remove filename from TOML URL
        base_url = toml_url.rsplit('/', 1)[0]
        resolved = f"{base_url}/{relative_path}"
        return resolved
    else:
        # Local file: resolve relative to script directory (repo root)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        resolved = os.path.join(script_dir, relative_path)
        return resolved

def parse_platforms_from_config(config: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Extract platforms from TOML config"""
    platforms = {}

    # Handle the current TOML structure with [roms] and [bios] sections
    for section_name, section_data in config.items():
        if isinstance(section_data, dict):
            for platform_key, platform_data in section_data.items():
                if isinstance(platform_data, dict):
                    platforms[platform_key] = platform_data

    return platforms

def get_platforms_by_type_and_status(platforms: Dict[str, Dict[str, Any]], config: Dict[str, Any],
                                   selected_platforms: list, platform_type: str, selected: bool) -> str:
    """Get platforms filtered by type and selection status as comma-separated string"""
    result = []
    for platform_name in platforms.keys():
        is_selected = platform_name in selected_platforms

        # Determine platform type
        if 'roms' in config and platform_name in config['roms']:
            current_type = 'roms'
        elif 'bios' in config and platform_name in config['bios']:
            current_type = 'bios'
        else:
            current_type = 'unknown'

        if current_type == platform_type and is_selected == selected:
            result.append(platform_name)
    return ', '.join(result) if result else 'None'

def show_menu(platforms: Dict[str, Dict[str, Any]], toml_url: str, config: Dict[str, Any]):
    """Interactive menu for platform selection"""
    selected_platforms = list(platforms.keys())  # Start with all selected
    output_dir = str(Path.home() / "Downloads")

    while True:
        print("=== Myrient Download Script ===")
        print(f"Collection: {toml_url}")
        print(f"Output directory: {output_dir}")

        # Display platforms by type and status
        print(f"Selected ROM platforms: {get_platforms_by_type_and_status(platforms, config, selected_platforms, 'roms', True)}")
        print(f"Selected BIOS platforms: {get_platforms_by_type_and_status(platforms, config, selected_platforms, 'bios', True)}")
        print(f"Unselected ROM platforms: {get_platforms_by_type_and_status(platforms, config, selected_platforms, 'roms', False)}")
        print(f"Unselected BIOS platforms: {get_platforms_by_type_and_status(platforms, config, selected_platforms, 'bios', False)}")
        print("")

        print("Options:")
        print("  1) Toggle platform selection")
        print("  2) Set output directory")
        print("  3) Dry run (preview download)")
        print("  4) Start download")
        print("  5) Cancel")
        print("")

        try:
            choice = input("Choose option (1-5): ").strip()
        except KeyboardInterrupt:
            print("\nDownload cancelled.")
            sys.exit(0)

        if choice == "1":
            print("")
            print("Available platforms:")
            platform_list = list(platforms.keys())
            for i in range(0, len(platform_list), 3):
                row_platforms = platform_list[i:i+3]
                row_lines = []
                for j, platform_name in enumerate(row_platforms):
                    marker = "✓" if platform_name in selected_platforms else " "
                    line = f"  [{marker}] {i+j+1:2d}) {platform_name}"
                    row_lines.append(line)
                print("    ".join(row_lines))
            print("")

            print("Enter platform numbers to toggle (space-separated) or 'all'/'none':")
            try:
                input_str = input().strip()
            except KeyboardInterrupt:
                continue

            if input_str.lower() == "all":
                selected_platforms = list(platforms.keys())
            elif input_str.lower() == "none":
                selected_platforms.clear()
            else:
                for num_str in input_str.split():
                    try:
                        num = int(num_str)
                        if 1 <= num <= len(platforms):
                            platform_name = list(platforms.keys())[num-1]
                            if platform_name in selected_platforms:
                                selected_platforms.remove(platform_name)
                            else:
                                selected_platforms.append(platform_name)
                    except ValueError:
                        pass

        elif choice == "2":
            print(f"Current output directory: {output_dir}")
            print("Enter new output directory (press Enter for ~/Downloads):")
            try:
                new_dir = input().strip()
                if new_dir:
                    output_dir = new_dir
                elif not output_dir:
                    output_dir = str(Path.home() / "Downloads")
            except KeyboardInterrupt:
                continue

        elif choice == "3":
            if not selected_platforms:
                print("Error: Please select at least one platform first.")
                input("Press Enter to continue...")
                continue
            dry_run(platforms, selected_platforms, toml_url, output_dir, config)

        elif choice == "4":
            if not selected_platforms:
                print("Error: Please select at least one platform first.")
                input("Press Enter to continue...")
                continue
            # Start download
            break

        elif choice == "5":
            print("Download cancelled.")
            sys.exit(0)

        else:
            print("Invalid option. Please try again.")
            input("Press Enter to continue...")

    return selected_platforms, output_dir

def dry_run(platforms: Dict[str, Dict[str, Any]], selected_platforms: list, toml_url: str, output_dir: str, config: Dict[str, Any]):
    """Show preview of what will be downloaded"""
    print("\n=== DRY RUN - Preview Download ===")
    print(f"Output directory: {output_dir}")
    print(f"Selected ROM platforms: {get_platforms_by_type_and_status(platforms, config, selected_platforms, 'roms', True)}")
    print(f"Selected BIOS platforms: {get_platforms_by_type_and_status(platforms, config, selected_platforms, 'bios', True)}")
    print("")

    print("Directories that will be created:")

    for platform_name in selected_platforms:
        platform_data = platforms[platform_name]
        platform_dir = platform_data['directory']
        full_platform_dir = os.path.join(output_dir, platform_dir)

        # Try to fetch URL list to show count
        try:
            urllist_path = platform_data['urllist']
            urllist_url = resolve_relative_url(toml_url, urllist_path)
            if urllist_url.startswith(('http://', 'https://')):
                req = urllib.request.Request(urllist_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=30) as response:
                    url_content = response.read().decode('utf-8')
            else:
                with open(urllist_url, 'r', encoding='utf-8') as f:
                    url_content = f.read()
            urls = [line.strip() for line in url_content.split('\n') if line.strip() and not line.startswith('#')]
            print(f"  {full_platform_dir} ({len(urls)} files)")
        except Exception as e:
            print(f"  {full_platform_dir} (Could not fetch URL list)")

    print("")
    input("Press Enter to return to menu...")

def download_platform(platform_name: str, platform_data: Dict[str, Any], output_dir: str):
    """Download files for a single platform"""
    platform_dir = platform_data['directory']
    should_extract = platform_data.get('extract', False)
    urllist_url = platform_data['resolved_urllist']

    # Create platform directory
    full_platform_dir = Path(output_dir) / platform_dir
    full_platform_dir.mkdir(parents=True, exist_ok=True)

    # Fetch URL list
    try:
        if urllist_url.startswith(('http://', 'https://')):
            # Remote URL
            req = urllib.request.Request(urllist_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=30) as response:
                url_content = response.read().decode('utf-8')
        else:
            # Local file
            with open(urllist_url, 'r', encoding='utf-8') as f:
                url_content = f.read()
    except Exception as e:
        log_error(f"Failed to fetch URL list for {platform_name}: {e}")
        return

    # Filter comments and empty lines
    urls = [line.strip() for line in url_content.split('\n') if line.strip() and not line.startswith('#')]

    if not urls:
        log_warn(f"No URLs found for {platform_name}")
        return

    # Create temporary URL list file for wget
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as url_file:
        for url in urls:
            url_file.write(f"{url}\n")
        url_list_file = url_file.name

    try:
        log_info(f"Downloading files for {platform_name}")
        result = subprocess.run([
            'wget', '-q', '-np', '-c', '-i', url_list_file, '-P', str(full_platform_dir)
        ])

        if result.returncode != 0:
            log_error(f"wget failed for {platform_name}")
            return

    finally:
        # Clean up URL list file
        os.unlink(url_list_file)

    # Extract if needed
    if should_extract:
        log_info(f"Extracting files for {platform_name}")
        for zip_file in full_platform_dir.glob("*.zip"):
            try:
                with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                    zip_ref.extractall(full_platform_dir)
                zip_file.unlink()  # Remove zip file after extraction
            except zipfile.BadZipFile:
                log_error(f"Failed to extract {zip_file}")

def main():
    parser = argparse.ArgumentParser(description="Universal ROM/BIOS downloader")
    parser.add_argument('collection_url', help='URL to TOML collection configuration')
    parser.add_argument('-o', '--output', help='Output directory (default: ~/Downloads)')
    parser.add_argument('--non-interactive', action='store_true', help='Skip interactive menu, download all platforms')

    args = parser.parse_args()

    # Fetch and parse TOML
    config = fetch_toml(args.collection_url)
    platforms = parse_platforms_from_config(config)

    if not platforms:
        print("Error: No platforms found in collection", file=sys.stderr)
        sys.exit(1)

    # Determine output directory
    output_dir = args.output or str(Path.home() / "Downloads")

    if args.non_interactive:
        selected_platforms = list(platforms.keys())
    else:
        selected_platforms, output_dir = show_menu(platforms, args.collection_url, config)

    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    os.chdir(output_dir)

    # Download selected platforms
    log_info(f"Starting download to {output_dir}")

    for platform_name in selected_platforms:
        if platform_name in platforms:
            # Resolve URL list path before changing directory
            platform_data = platforms[platform_name].copy()
            urllist_path = platform_data['urllist']
            resolved_urllist = resolve_relative_url(args.collection_url, urllist_path)
            platform_data['resolved_urllist'] = resolved_urllist
            download_platform(platform_name, platform_data, output_dir)

    log_info("Download completed successfully")

# Colors for output
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
NC = '\033[0m'

def log_info(msg):
    print(f"{GREEN}[{os.popen('date +%H:%M:%S').read().strip()}] INFO: {msg}{NC}")

def log_warn(msg):
    print(f"{YELLOW}[{os.popen('date +%H:%M:%S').read().strip()}] WARN: {msg}{NC}")

def log_error(msg):
    print(f"{RED}[{os.popen('date +%H:%M:%S').read().strip()}] ERROR: {msg}{NC}")
    sys.exit(1)

if __name__ == "__main__":
    main()
