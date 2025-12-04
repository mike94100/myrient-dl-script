#!/usr/bin/env bash
set -euo pipefail

# Generate platform TOML by scraping Myrient page
# Usage: gen-platform-toml.sh <base_url> <subdomain_path> <output_file>

log() {
    echo "$*" >&2
}

show_help() {
    cat << EOF
NAME
    gen-platform-toml.sh - Generate platform TOML files by scraping Myrient pages

SYNOPSIS
    gen-platform-toml.sh [OPTIONS] <base_url> <subdomain_path> <output_file>

DESCRIPTION
    This script generates TOML configuration files for the myrient-dl.sh ROM downloader
    by scraping Myrient download pages. It automatically discovers all available .zip
    files on a given platform page and creates a properly formatted TOML file.

ARGUMENTS
    base_url
        The base URL for Myrient (e.g., 'https://myrient.erista.me/files/')

    subdomain_path
        The platform-specific path under the base URL. This should include the
        collection and platform directories (e.g., 'No-Intro/Nintendo%20-%20Game%20Boy/')

    output_file
        The name of the TOML file to generate (e.g., gb.toml). The directory name
        will be automatically derived from this filename.

OPTIONS
    -h, --help
        Display this help message and exit.

EXAMPLES
    Generate a Game Boy TOML file:
        gen-platform-toml.sh 'https://myrient.erista.me/files/' \\
            'No-Intro/Nintendo%20-%20Game%20Boy/' gb.toml

    Generate a GBA TOML file:
        gen-platform-toml.sh 'https://myrient.erista.me/files/' \\
            'No-Intro/Nintendo%20-%20Game%20Boy%20Advance/' gba.toml

OUTPUT FORMAT
    The generated TOML file contains three fields:

    subdomain
        The provided subdomain_path (used to construct download URLs)

    directory
        Automatically derived from output_file (e.g., gb.toml → "gb/")

    files
        An array of URL-encoded .zip filenames found on the page, sorted alphabetically

BEHAVIOR
    - Files are scraped from the constructed URL: base_url + subdomain_path
    - Only .zip files are included in the files array
    - Files are listed in alphabetical order
    - The script requires internet access to scrape Myrient pages
    - Generated TOML files are compatible with myrient-dl.sh

ERRORS
    The script will exit with an error if:
    - Required arguments are missing
    - The target URL cannot be accessed
    - No .zip files are found on the page

SEE ALSO
    myrient-dl.sh - Download ROMs using generated TOML files
    gen-readme.sh - Generate README files from TOML configurations

EOF
}

# Parse options
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -*)
            log "Unknown option: $1"
            log "Use -h or --help for usage"
            exit 1
            ;;
        *)
            break
            ;;
    esac
done

# Check arguments
if [[ $# -ne 3 ]]; then
    log "Usage: $0 [OPTIONS] <base_url> <subdomain_path> <output_file>"
    log "Use -h or --help for detailed help"
    exit 1
fi

BASE_URL="$1"
SUBDOMAIN_PATH="$2"
OUTPUT_FILE="$3"

# Construct full URL
FULL_URL="${BASE_URL%/}/${SUBDOMAIN_PATH#/}"

# Extract directory from output filename (remove .toml extension)
BASENAME="${OUTPUT_FILE%.toml}"
DIRECTORY="${BASENAME}/"

log "Scraping: $FULL_URL"
log "Subdomain: $SUBDOMAIN_PATH"
log "Directory: $DIRECTORY"
log "Output: $OUTPUT_FILE"

# Scrape the page
HTML=$(curl -s "$FULL_URL")

# Extract file links - look for href="..." that end with .zip
# Myrient pages have links like: <a href="filename.zip">filename</a>
FILES=$(echo "$HTML" | grep -o '<a href="[^"]*\.zip">' | sed 's/<a href="//;s/">$//' | sort)

if [[ -z "$FILES" ]]; then
    log "ERROR: No .zip files found on the page"
    exit 1
fi

log "Found $(echo "$FILES" | wc -l) files"

# Write TOML
{
    echo "subdomain = \"$SUBDOMAIN_PATH\""
    echo "directory = \"$DIRECTORY\""
    echo ""
    echo "files = ["
    echo "$FILES" | sed 's/.*/  "&",/'
    echo "]"
} > "$OUTPUT_FILE"

log "Generated $OUTPUT_FILE"
