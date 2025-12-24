#!/usr/bin/env python3
"""
wget utility functions for myrient-dl
Handles wget dependency checking and user-guided installation
"""

import platform
import shutil
import subprocess
import sys
from pathlib import Path


def run_command(cmd, shell=False, check=True):
    """Run a command and return True if successful"""
    try:
        subprocess.run(cmd if shell else cmd.split(),
                      shell=shell, check=check,
                      capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError:
        return False
    except FileNotFoundError:
        return False


def wget_check():
    """Check if wget is available"""
    return shutil.which("wget") is not None


def wget_install_options():
    """Get platform-specific wget installation options"""
    system = platform.system().lower()

    if system == "windows":
        return {
            "1": ("Chocolatey", "choco install wget"),
            "2": ("Winget", "winget install wget"),
            "3": ("Git for Windows", "echo 'wget included with Git for Windows'"),
            "4": ("Manual download", "echo 'Download from: https://gnuwin32.sourceforge.net/packages/wget.htm'")
        }
    elif system == "darwin":  # macOS
        return {
            "1": ("Homebrew", "brew install wget"),
            "2": ("MacPorts", "sudo port install wget"),
            "3": ("Manual download", "echo 'Download from: https://ftp.gnu.org/gnu/wget/'")
        }
    else:  # Linux/Unix
        return {
            "1": ("apt (Ubuntu/Debian)", "sudo apt update && sudo apt install wget"),
            "2": ("yum (RHEL/CentOS)", "sudo yum install wget"),
            "3": ("dnf (Fedora)", "sudo dnf install wget"),
            "4": ("pacman (Arch)", "sudo pacman -S wget"),
            "5": ("zypper (openSUSE)", "sudo zypper install wget"),
            "6": ("Manual download", "echo 'Download from: https://ftp.gnu.org/gnu/wget/'")
        }


def wget_install():
    """Ensure wget is available, prompt for installation if missing"""
    if wget_check():
        return True

    print("\n" + "="*60)
    print("Myrient ROM downloader requires 'wget' for downloading files.")
    print()
    print("Why wget?")
    print("- Myrient officially recommends wget for their site")
    print("- Handles large downloads reliably with resume support")
    print("- Respects robots.txt and has built-in rate limiting")
    print("- Cross-platform and widely available")
    print("="*60)

    while True:
        response = input("\nInstall wget now? (y/N): ").strip().lower()
        if response in ('n', 'no', ''):
            print("\nPlease install wget manually and run the script again.")
            print("Installation commands for your platform:")
            options = wget_install_options()
            for key, (name, cmd) in options.items():
                print(f"  {key}. {name}: {cmd}")
            return False
        elif response in ('y', 'yes'):
            break
        else:
            print("Please enter 'y' or 'n'")

    # Show installation options
    options = wget_install_options()
    print("\nChoose installation method:")
    for key, (name, cmd) in options.items():
        print(f"  {key}. {name}")

    while True:
        choice = input(f"\nEnter choice (1-{len(options)}): ").strip()
        if choice in options:
            name, cmd = options[choice]
            print(f"\nInstalling wget using {name}...")
            print(f"Command: {cmd}")

            # Run installation command
            success = run_command(cmd, shell=True, check=False)
            if success:
                print("Installation completed successfully!")
                # Verify installation
                if wget_check():
                    print("wget is now available.")
                    return True
                else:
                    print("Installation may have succeeded but wget is not found in PATH.")
                    print("You may need to restart your terminal or add wget to PATH.")
                    return False
            else:
                print(f"Installation failed. Please try manually: {cmd}")
                return False
        else:
            print(f"Invalid choice. Enter 1-{len(options)}")


def wget_download(urls, output_dir, progress=True):
    """Download files using wget with progress bars and detailed error reporting"""
    import tempfile
    import os
    from utils.log_utils import get_logger

    logger = get_logger()

    # Create temporary file with URLs
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        for url in urls:
            f.write(f"{url}\n")
        url_file = f.name

    try:
        # Build wget command
        cmd = [
            "wget",
            "--progress=bar" if progress else "--quiet",
            "-i", url_file,
            "-P", str(output_dir),
            "-np",  # Don't ascend to parent directories
            "-c",   # Continue partial downloads
            "-e", "robots=off",  # Ignore robots.txt
            "-R", "index.html*"  # Reject index files
        ]

        # Run wget
        result = subprocess.run(cmd)

        # Check for failures
        if result.returncode != 0:
            logger.error(f"wget batch download failed (exit code: {result.returncode})")
            return False

        return True

    finally:
        # Clean up temp file
        try:
            os.unlink(url_file)
        except:
            pass


# Global session for connection pooling
_http_session = None

def get_http_session():
    """Get or create a global HTTP session for connection pooling"""
    global _http_session
    if _http_session is None:
        try:
            import requests
            _http_session = requests.Session()
            # Set a reasonable timeout
            _http_session.timeout = 30
            # Set user agent
            _http_session.headers.update({
                'User-Agent': 'Mozilla/5.0 (compatible; MyrientDL/1.0)'
            })
        except ImportError:
            # Fallback if requests not available
            _http_session = None
    return _http_session


def wget_scrape(url, cache_manager=None, request_delay=1.0, use_session=True):
    """Download HTML content using requests.Session() for connection pooling, fallback to wget"""
    import time

    # Check cache first
    if cache_manager:
        cached_content = cache_manager.get(url)
        if cached_content:
            return cached_content

    # Add delay
    if request_delay > 0:
        time.sleep(request_delay)

    # Try requests.Session() first for connection pooling
    if use_session:
        session = get_http_session()
        if session:
            try:
                response = session.get(url, timeout=30)
                response.raise_for_status()
                content = response.text

                # Cache the result
                if cache_manager and content:
                    cache_manager.put(url, content)

                return content
            except Exception as e:
                # Fall back to wget if session fails
                pass

    # Fallback to wget
    import tempfile
    import os

    with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as f:
        temp_file = f.name

    try:
        cmd = [
            "wget",
            "-q",  # Quiet mode
            "-O", temp_file,  # Output file
            "--timeout", "30",  # 30 second timeout
            "--tries", "3",     # Retry up to 3 times
            "--user-agent", "Mozilla/5.0 (compatible; MyrientDL/1.0)",
            url
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return None

        # Read the downloaded HTML
        with open(temp_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Cache the result
        if cache_manager and content:
            cache_manager.put(url, content)

        return content

    finally:
        try:
            os.unlink(temp_file)
        except:
            pass
