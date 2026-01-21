#!/usr/bin/env python3
"""
Auto-generated download script for {TITLE}
Generated on {DATE}
"""

import os
import urllib.request
{E_ZIPFILE}
from pathlib import Path

def main():
    platform_dir = "{DIRECTORY}"
    os.makedirs(platform_dir, exist_ok=True)
    os.chdir(platform_dir)

    urls = [
{URL_LIST}
    ]

    print(f"Downloading {len(urls)} files to {platform_dir}")

    for i, url in enumerate(urls, 1):
        filename = url.split('/')[-1]
        print(f"Downloading {i}/{len(urls)}: {filename}")
        try:
            urllib.request.urlretrieve(url, filename)
        except Exception as e:
            print(f"Failed to download {filename}: {e}")

    {E_EXTRACTION}

    print("Download complete!")
    print(f"Files saved to: {platform_dir}")

if __name__ == "__main__":
    main()
