#!/usr/bin/env python3
"""
Myrient Link Scraper
Crawls Myrient directory listings and caches download links
"""

import requests
from bs4 import BeautifulSoup
import json
import argparse
from pathlib import Path
from urllib.parse import urljoin, urlparse
import time
import re

def parse_size(size_str):
    """Convert IEC size string like '1.2 MiB', '500 KiB', '2.5 GiB' to bytes"""
    if not size_str or size_str == 'Unknown':
        return 0

    # Extract number and unit (B, KiB, MiB, GiB, etc.)
    match = re.match(r'(\d+(?:\.\d+)?)\s*(B|KiB|MiB|GiB|TiB)', size_str.strip())
    if not match:
        return 0

    number = float(match.group(1))
    unit = match.group(2)

    # Convert to bytes
    multipliers = {
        'B': 1,           # bytes
        'KiB': 1024,      # 2^10
        'MiB': 1024**2,   # 2^20
        'GiB': 1024**3,   # 2^30
        'TiB': 1024**4    # 2^40
    }

    return int(number * multipliers.get(unit, 1))

class MyrientScraper:
    def __init__(self, base_url="https://myrient.erista.me/files/", delay=1):
        self.base_url = base_url
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; ROM Cache Scraper)'
        })

    def get_page_files(self, url):
        """Extract all .zip files with sizes from a directory listing page"""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            files = []

            table = soup.find('table')
            if table:
                rows = table.find_all('tr')
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 3:  # filename, size, date columns
                        link = cols[0].find('a')
                        if link and link.get('href', '').endswith('.zip'):
                            filename = link.text.strip()
                            size_text = cols[1].text.strip() if len(cols) > 1 else 'Unknown'

                            full_url = urljoin(url, link['href'])
                            size_bytes = parse_size(size_text)
                            files.append({
                                'url': full_url,
                                'size': size_bytes
                            })

            time.sleep(self.delay)  # Be respectful
            return files
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return []

    def scrape_directory(self, url):
        """Scrape all .zip files with metadata from a directory"""
        print(f"Scraping: {url}")
        files = self.get_page_files(url)
        return files

    def categorize_urls(self, urls, config):
        """Categorize URLs by platform based on config patterns"""
        categorized = {}

        for platform, patterns in config.items():
            categorized[platform] = []
            for url in urls:
                path_parts = urlparse(url).path.split('/')
                filename = path_parts[-1] if path_parts else ''

                # Check if any pattern matches the path or filename
                matches = False
                for pattern in patterns:
                    if re.search(pattern, url, re.IGNORECASE):
                        matches = True
                        break

                if matches:
                    categorized[platform].append(url)

        return categorized

def load_platform_config():
    """Load platform configurations from metadata.json"""
    try:
        with open('metadata.json', 'r', encoding='utf-8') as f:
            metadata = json.load(f)

        platforms = []
        for platform_key, platform_data in metadata['platforms'].items():
            if 'url' in platform_data:
                platforms.append((platform_key, platform_data['url']))

        return platforms
    except Exception as e:
        print(f"Error loading metadata.json: {e}")
        return []

def main():
    parser = argparse.ArgumentParser(description="Scrape Myrient and generate data files")
    parser.add_argument('-o', '--output-dir', default='data', help='Output directory for JSON files')
    parser.add_argument('-d', '--delay', type=float, default=1, help='Delay between requests (seconds)')
    args = parser.parse_args()

    scraper = MyrientScraper(delay=args.delay)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)

    # Load platform configurations from metadata.json
    platforms = load_platform_config()
    if not platforms:
        print("Failed to load platform configurations from metadata.json")
        return

    scraper = MyrientScraper(delay=args.delay)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)

    total_files = 0
    for platform, url in platforms:
        files = scraper.scrape_directory(url)

        if files:
            output_file = output_dir / f'{platform}.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(files, f, indent=2)
            print(f"Generated {output_file} with {len(files)} files")
            total_files += len(files)
        else:
            print(f"No files found for {platform}")

    print(f"Processed {total_files} files total across {len(platforms)} directories")

if __name__ == "__main__":
    main()
