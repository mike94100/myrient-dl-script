#!/usr/bin/env bash
set -uo pipefail

# Source utility functions
. ./scripts/url-utils.sh
. ./scripts/toml-utils.sh
. ./scripts/progress.sh
. ./scripts/log.sh

# Validate filter file
validate_filter_file() {
    local file="$1"
    if [[ ! -f "$file" ]]; then
        log "ERROR: Filter file not found: $file"
        exit 1
    fi
    # Basic validation - ensure file contains sed-like commands
    if ! grep -q 's/.*//' "$file" 2>/dev/null; then
        log "WARNING: Filter file may not contain valid sed commands"
    fi
}

show_help() {
    cat << EOF
NAME
    gen-platform-toml.sh - Generate platform TOML files by scraping Myrient pages

SYNOPSIS
    gen-platform-toml.sh [OPTIONS] <path_directory> <output_file>
    gen-platform-toml.sh [OPTIONS] <site> <path_directory> <output_file>

DESCRIPTION
    This script generates TOML configuration files for the myrient-dl.sh ROM downloader
    by scraping Myrient download pages. It automatically discovers all available .zip
    files on a given platform page and creates a properly formatted TOML file.

ARGUMENTS
    site (optional)
        The site for Myrient. Defaults to "https://myrient.erista.me".
        Only specify this if you need to use a different Myrient instance.

    path_directory
        The specific directory path under the site. This should include the files,
        collection, and platform directories (e.g., "/files/No-Intro/Nintendo - Game Boy/")

    output_file
        The path of the TOML file to generate (e.g., gb.toml or n64/n64.toml).
        Any directories in the path will be created automatically.

OPTIONS
    -f, --filter-file FILE
        Load filter commands from a sed script file containing sed commands.
        Example: -f "filters/1g1r.sed"

    -g, --gen-readme
        Automatically generate a README.md file for the created TOML configuration.

    -s, --slim-output
        Skip printing commented out files in the generated TOML. Only files that
        pass all filters will be included in the files array.

    -h, --help
        Display this help message and exit.

EXAMPLES
    Generate a Game Boy TOML file (using default base URL):
        gen-platform-toml.sh "/files/No-Intro/Nintendo - Game Boy/" "gb.toml"

    Generate a filtered TOML file using a sed filter:
        gen-platform-toml.sh -f "filters/1g1r.sed" "/files/No-Intro/Nintendo - Game Boy Advance/" "gba.toml"

    Generate TOML file in subdirectory (creates directory automatically):
        gen-platform-toml.sh "/files/No-Intro/Nintendo - Nintendo 64 (BigEndian)/" "1g1r/n64/n64.toml"

OUTPUT FORMAT
    The generated TOML file contains the following fields:

    site
        The site hosting files

    path_directory
        The path to the platform directory containing files

    directory
        Where files will be saved, derived from output_file name.

    files
        An array of human-readable .zip filenames found on the page, sorted alphabetically

BEHAVIOR
    - Files are scraped from the constructed URL: site + path_directory
    - Filter and pass game files to files array
    - Generated TOML files are compatible with myrient-dl.sh
EOF
}

# Parse options using getopt
TEMP=$(getopt -o 'hf:gs' --long 'help,filter-file:,gen-readme,slim-output' -n 'gen-platform-toml' -- "$@")
if [[ $? -ne 0 ]]; then
    log "Use -h or --help for usage"
    exit 1
fi

eval set -- "$TEMP"

FILTER_FILE=""
GEN_README=false
SLIM_OUTPUT=false

while true; do
    case "$1" in
        -h|--help)
            show_help
            exit 0
            ;;

        -f|--filter-file)
            FILTER_FILE="$2"
            shift 2
            ;;
        -g|--gen-readme)
            GEN_README=true
            shift
            ;;
        -s|--slim-output)
            SLIM_OUTPUT=true
            shift
            ;;
        --)
            shift
            break
            ;;
        *)
            # Non-option argument, stop parsing options
            break
            ;;
    esac
done

# Validate filter file if specified
if [[ -n "$FILTER_FILE" ]]; then
    if [[ ! -f "$FILTER_FILE" ]]; then
        log "ERROR: Filter file not found: $FILTER_FILE"
        exit 1
    fi
    log "Using filter file: $FILTER_FILE"
fi

# Check remaining arguments - support both 2 and 3 argument formats
if [[ $# -eq 2 ]]; then
    # 2 args: path_directory output_file (Use default site)
    CONFIG_JSON=$(parse_toml "./config.toml")
    SITE=$(printf "%s" "$CONFIG_JSON" | jq -r '.site')
    PATH_DIRECTORY_DEC=$(url_decode "$1")
    PATH_DIRECTORY_ENC=$(url_encode "$1")
    OUTPUT_FILE="$2"
elif [[ $# -eq 3 ]]; then
    # 3 args: site path_directory output_file
    SITE=$1
    PATH_DIRECTORY_DEC=$(url_decode "$2")
    PATH_DIRECTORY_ENC=$(url_encode "$2")
    OUTPUT_FILE="$3"
else
    log "Usage: gen-platform-toml.sh [OPTIONS] <path_directory> <output_file>"
    log "   or: gen-platform-toml.sh [OPTIONS] <site> <path_directory> <output_file>"
    log "Use -h or --help for detailed help"
    exit 1
fi

if ! validate_directory_path "$PATH_DIRECTORY_DEC"; then
    exit 1
fi

# Parse output file path - extract directory and filename
OUTPUT_DIR=$(dirname "$OUTPUT_FILE")
OUTPUT_FILENAME=$(basename "$OUTPUT_FILE")
BASENAME="${OUTPUT_FILENAME%.toml}"

# If no directory was specified, create one with the same name as the file
if [[ "$OUTPUT_DIR" == "." ]]; then
    OUTPUT_DIR="$BASENAME"
fi

# Construct full output path
OUTPUT_PATH="${OUTPUT_DIR}/${OUTPUT_FILENAME}"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Directory for downloads
DIRECTORY="${BASENAME}/"

# Construct URL for the directory
SOURCE_URL_ENC="${SITE}${PATH_DIRECTORY_ENC}"
SOURCE_URL_DEC="${SITE}${PATH_DIRECTORY_DEC}"

# Scrape the page
log "Scraping: $SOURCE_URL_DEC"
HTML=$(curl -s "$SOURCE_URL_ENC")

# Extract file links - capture link text only
FILES=$(echo "$HTML" | grep -o '<a href="[^"]*\.zip"[^>]*>[^<]*</a>' | sed 's|<a href="[^"]*"[^>]*>\([^<]*\)</a>|\1|g' | sort)

if [[ -z "$FILES" ]]; then
    log "ERROR: No .zip files found on the page"
    exit 1
fi

# Apply sed filtering if filter file was provided
if [[ -n "$FILTER_FILE" ]]; then
    total_files=$(echo "$FILES" | wc -l)

    log "Filtering $total_files files"
    FILES=$(echo "$FILES" | sed -E -f "$FILTER_FILE" 2>/dev/null || echo "$FILES")

    filtered_count=$(echo "$FILES" | grep -c '^[^#]')  # Count uncommented lines
    excluded_count=$((total_files - filtered_count))
    
    if [[ $excluded_count -gt 0 ]]; then
        log "Files Included | Files Excluded - $filtered_count | $excluded_count"
    fi
fi

# Write TOML
{
    echo "# Site that is hosting these files"
    echo "site = \"$SITE\""
    echo ""

    echo "# The path to the directory these files are located in"
    echo "path_directory = \"$PATH_DIRECTORY_DEC\""
    echo ""

    echo "# Directory where files will be downloaded:"
    echo "directory = \"$DIRECTORY\""
    echo ""

    echo "# List of files to download:"
    echo "files = ["
    echo "$FILES" | while IFS= read -r file; do
        if [[ -n "$file" && "$file" != \#* ]]; then
            echo "  \"$file\","
        elif [[ -n "$file" && "$SLIM_OUTPUT" == false ]]; then
            echo "  # \"${file#"#"}\","
        fi
    done
    echo "]"
} > "$OUTPUT_PATH"

log "Generated $OUTPUT_PATH"

# Generate README if requested
if [[ "$GEN_README" == true ]]; then
    ./gen-readme.sh "$OUTPUT_PATH"
fi
