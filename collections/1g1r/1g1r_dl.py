#!/usr/bin/env python3
"""
Generated ROM/BIOS download script
This script downloads files using wget for parallel downloads
"""

import os
import sys
import tempfile
import zipfile
import subprocess
import urllib.request
import urllib.error
from pathlib import Path

# Platform configuration lists
PLATFORM_NAMES = [
    "roms.nes",
    "roms.snes",
    "roms.n64",
    "roms.gc",
    "roms.wii",
    "roms.gb",
    "roms.gbc",
    "roms.gba",
    "roms.nds",
    "roms.3ds",
    "roms.genesis",
    "roms.dreamcast",
    "roms.psx",
    "roms.ps2",
    "roms.psp",
    "roms.atari2600",
    "roms.atari5200",
    "roms.atari7800",
    "roms.c64",
    "roms.colecovision",
    "roms.intellivision",
]

PLATFORM_DIRS = [
    "roms/nes",
    "roms/snes",
    "roms/n64",
    "roms/gc",
    "roms/wii",
    "roms/gb",
    "roms/gbc",
    "roms/gba",
    "roms/nds",
    "roms/3ds",
    "roms/genesis",
    "roms/dreamcast",
    "roms/psx",
    "roms/ps2",
    "roms/psp",
    "roms/atari2600",
    "roms/atari5200",
    "roms/atari7800",
    "roms/c64",
    "roms/colecovision",
    "roms/intellivision",
]

PLATFORM_URLS = [
    "https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/collections/1g1r/urls/nes.txt",
    "https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/collections/1g1r/urls/snes.txt",
    "https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/collections/1g1r/urls/n64.txt",
    "https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/collections/1g1r/urls/gc.txt",
    "https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/collections/1g1r/urls/wii.txt",
    "https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/collections/1g1r/urls/gb.txt",
    "https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/collections/1g1r/urls/gbc.txt",
    "https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/collections/1g1r/urls/gba.txt",
    "https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/collections/1g1r/urls/nds.txt",
    "https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/collections/1g1r/urls/3ds.txt",
    "https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/collections/1g1r/urls/genesis.txt",
    "https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/collections/1g1r/urls/dreamcast.txt",
    "https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/collections/1g1r/urls/psx.txt",
    "https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/collections/1g1r/urls/ps2.txt",
    "https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/collections/1g1r/urls/psp.txt",
    "https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/collections/1g1r/urls/atari2600.txt",
    "https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/collections/1g1r/urls/atari5200.txt",
    "https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/collections/1g1r/urls/atari7800.txt",
    "https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/collections/1g1r/urls/c64.txt",
    "https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/collections/1g1r/urls/colecovision.txt",
    "https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/collections/1g1r/urls/intellivision.txt",
]

PLATFORM_EXTRACTS = [
    false,
    false,
    false,
    false,
    false,
    false,
    false,
    false,
    false,
    false,
    false,
    false,
    false,
    false,
    false,
    false,
    false,
    false,
    false,
    false,
    false,
]

# Initialize variables
SELECTED_PLATFORMS = PLATFORM_NAMES.copy()
OUTPUT_DIR = str(Path.home() / "Downloads")

def show_menu():
    print("=== ROM/BIOS Download Script ===")
    print("")
    print("Current settings:")
    print(f"  Platforms: {', '.join(SELECTED_PLATFORMS) if SELECTED_PLATFORMS else 'None selected'}")
    print(f"  Output directory: {OUTPUT_DIR}")
    print("")
    print("Available platforms:")
    for i, platform in enumerate(PLATFORM_NAMES):
        selected = "✓" if platform in SELECTED_PLATFORMS else " "
        print(f"  [{selected}] {i+1}) {platform}")
    print("")
    print("Options:")
    print("  1) Select platforms")
    print("  2) Set output directory")
    print("  3) Continue with download")
    print("  4) Cancel")
    print("")
    try:
        choice = input("Choose option (1-4): ").strip()
    except KeyboardInterrupt:
        print("\nDownload cancelled.")
        sys.exit(0)

    if choice == "1":
        select_platforms()
    elif choice == "2":
        set_output_dir()
    elif choice == "3":
        if not SELECTED_PLATFORMS or not OUTPUT_DIR:
            print("Error: Please select platforms and set output directory first.")
            print("")
            show_menu()
            return
        confirm_download()
        return
    elif choice == "4":
        print("Download cancelled.")
        sys.exit(0)
    else:
        print("Invalid option. Please try again.")
        print("")
        show_menu()

def select_platforms():
    print("")
    print("Enter platform numbers to toggle (space-separated) or 'all'/'none':")
    try:
        input_str = input().strip()
    except KeyboardInterrupt:
        print("\nDownload cancelled.")
        sys.exit(0)

    if input_str.lower() == "all":
        SELECTED_PLATFORMS[:] = PLATFORM_NAMES
    elif input_str.lower() == "none":
        SELECTED_PLATFORMS.clear()
    else:
        for num_str in input_str.split():
            try:
                num = int(num_str)
                if 1 <= num <= len(PLATFORM_NAMES):
                    platform = PLATFORM_NAMES[num-1]
                    if platform in SELECTED_PLATFORMS:
                        SELECTED_PLATFORMS.remove(platform)
                    else:
                        SELECTED_PLATFORMS.append(platform)
            except ValueError:
                pass
    show_menu()

def set_output_dir():
    print("")
    print(f"Current output directory: {OUTPUT_DIR}")
    print("Enter new output directory (press Enter for ~/Downloads):")
    try:
        new_dir = input().strip()
    except KeyboardInterrupt:
        print("\nDownload cancelled.")
        sys.exit(0)

    if new_dir:
        OUTPUT_DIR = new_dir
    elif not OUTPUT_DIR:
        OUTPUT_DIR = str(Path.home() / "Downloads")
    show_menu()

def confirm_download():
    print("")
    print("Ready to download:")
    print(f"  Platforms: {', '.join(SELECTED_PLATFORMS)}")
    print(f"  Output directory: {OUTPUT_DIR}")
    print("")
    try:
        confirm = input("Start download? (y/N): ").strip().lower()
    except KeyboardInterrupt:
        print("\nDownload cancelled.")
        return

    if confirm == "y" or confirm == "yes":
        return
    else:
        print("Download cancelled.")
        show_menu()

# Show initial menu
show_menu()

# Colors for output (using ANSI escape codes)
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
NC = '\033[0m'  # No Color

def log_info(msg):
    print(f"{GREEN}[{os.popen('date +%H:%M:%S').read().strip()}] INFO: {msg}{NC}")

def log_warn(msg):
    print(f"{YELLOW}[{os.popen('date +%H:%M:%S').read().strip()}] WARN: {msg}{NC}")

def log_error(msg):
    print(f"{RED}[{os.popen('date +%H:%M:%S').read().strip()}] ERROR: {msg}{NC}")
    sys.exit(1)

log_info(f"Starting 1g1r download to {OUTPUT_DIR}")

# Create output directory if it doesn't exist
output_path = Path(OUTPUT_DIR)
output_path.mkdir(parents=True, exist_ok=True)
os.chdir(output_path)

def process_platform(index):
    platform_name = PLATFORM_NAMES[index]
    platform_dir = PLATFORM_DIRS[index]
    platform_url = PLATFORM_URLS[index]
    should_extract = PLATFORM_EXTRACTS[index]

    # Create platform directory
    platform_path = Path(platform_dir)
    platform_path.mkdir(parents=True, exist_ok=True)

    # Download URL list
    try:
        with urllib.request.urlopen(platform_url) as response:
            url_list_content = response.read().decode('utf-8')
    except urllib.error.URLError as e:
        log_error(f"Failed to download URL list for {platform_name}: {e}")
        return

    # Filter comments and empty lines
    urls = [line.strip() for line in url_list_content.split('\n') if line.strip() and not line.startswith('#')]

    if not urls:
        log_warn(f"No URLs found for {platform_name}")
        return

    # Create temporary URL list file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as url_file:
        for url in urls:
            url_file.write(f"{url}\n")
        url_list_file = url_file.name

    try:
        # Download all files using wget in parallel
        log_info(f"Downloading files for {platform_name}")
        result = subprocess.run([
            'wget', '-np', '-c', '--progress=bar', '-i', url_list_file, '-P', platform_dir
        ], capture_output=True, text=True)

        if result.returncode != 0:
            log_error(f"wget failed for {platform_name}: {result.stderr}")
            return

    finally:
        # Clean up URL list file
        os.unlink(url_list_file)

    # Extract if needed
    if should_extract:
        log_info(f"Extracting files for {platform_name}")
        for zip_file in platform_path.glob("*.zip"):
            try:
                with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                    zip_ref.extractall(platform_path)
                zip_file.unlink()  # Remove zip file after extraction
            except zipfile.BadZipFile:
                log_error(f"Failed to extract {zip_file}")

# Process selected platforms
for i, platform_name in enumerate(PLATFORM_NAMES):
    if platform_name in SELECTED_PLATFORMS:
        process_platform(i)

log_info("Download completed successfully")
