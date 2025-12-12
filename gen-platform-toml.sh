#!/usr/bin/env bash
set -uo pipefail

# Source utility functions
. ./scripts/url-utils.sh
. ./scripts/toml-utils.sh
. ./scripts/progress.sh
. ./scripts/log.sh

show_help() {
    cat << EOF
NAME
    gen-platform-toml.sh - Generate platform TOML files by scraping Myrient pages

SYNOPSIS
    gen-platform-toml.sh [OPTIONS] <path_directory> <output_directory>
    gen-platform-toml.sh [OPTIONS] <site> <path_directory> <output_directory>

DESCRIPTION
    This script generates TOML configuration files for the myrient-dl.sh ROM downloader
    by scraping Myrient download pages. It automatically discovers all available .zip
    files on a given platform page and creates a properly formatted TOML file.

ARGUMENTS
    site (optional)
        The site for Myrient. Defaults to site in config or "https://myrient.erista.me".
        Only specify this if you need to use a different Myrient instance.

    path_directory
        The specific directory path under the site. This should include the files,
        collection, and platform directories (e.g., "/files/No-Intro/Nintendo - Game Boy/")

    output_directory
        The directory where the TOML configuration file will be created.
        The filename will be derived from the directory name.
        Any missing directories in the path will be created automatically.
        Example: "gb/" creates "gb/gb.toml"

OPTIONS
    -f, --filter-file FILE
        Load filter commands from a sed or awk script file.
        Supports .sed files (sed commands) or .awk files (awk commands).
        Examples: -f "filter.sed" or -f "filter.awk"

    -g, --gen-readme
        Automatically generate a README.md file for the created TOML configuration.

    -s, --slim-output
        Skip printing commented out files in the generated TOML. Only files that
        pass all filters will be included in the files array.

    -h, --help
        Display this help message and exit.

EXAMPLES
    Generate a Game Boy TOML file:
        gen-platform-toml.sh "/files/No-Intro/Nintendo - Game Boy/" "gb/"
        # Creates: gb/gb.toml

    Generate a filtered TOML file using a filter:
        gen-platform-toml.sh -f "filter.awk" "/files/No-Intro/Nintendo - Game Boy Advance/" "gb/"
        # Creates: gb/gb.toml

    Generate a Game Boy TOML file and README:
        gen-platform-toml.sh -g "/files/No-Intro/Nintendo - Game Boy/" "gb/"
        # Creates: gb/gb.toml & gb/README.md

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
    info "Use -h or --help for usage"; exit 1
fi

eval set -- "$TEMP"

FILTER_FILE=""; GEN_README=false; SLIM_OUTPUT=false

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

# Check arguments - support both 2 and 3 argument formats
if [[ $# -eq 3 ]]; then
    SITE="$1"; shift
elif [[ $# -eq 2 ]]; then
    CONFIG_JSON=$(parse_toml "./config.toml")
    SITE=$(printf "%s" "$CONFIG_JSON" | jq -r '.site // "https://myrient.erista.me"')
else
    info "Usage: gen-platform-toml.sh [OPTIONS] <path_directory> <output_directory>"
    info "   or: gen-platform-toml.sh [OPTIONS] <site> <path_directory> <output_directory>"
    info "Use -h or --help for detailed help"
    exit 1
fi

# Parse remaining arguments
PATH_DIRECTORY_DEC=$(url_decode "$1")
PATH_DIRECTORY_ENC=$(url_encode "$1")
OUTPUT_DIR="$2"

if ! validate_directory_path "$PATH_DIRECTORY_DEC"; then
    exit 1
fi

# Validate and normalize output directory path
OUTPUT_DIR=$(echo "$OUTPUT_DIR" | sed '/\/$/!s|$|/|')
if [[ ! "$OUTPUT_DIR" =~ ^[a-zA-Z0-9/_-]+$ ]]; then
    error "Invalid output directory path: $OUTPUT_DIR"; exit 1
fi

# Create output directory
if ! mkdir -p "$OUTPUT_DIR"; then
    error "Failed to create directory: $OUTPUT_DIR"; exit 1
fi

# Directory for downloads
DIRECTORY="$(basename "${OUTPUT_DIR}")/"

# Output TOML file path
OUTPUT_PATH="${OUTPUT_DIR}${DIRECTORY%/}.toml"

# Construct URL for the directory
SOURCE_URL_ENC="${SITE}${PATH_DIRECTORY_ENC}"
SOURCE_URL_DEC="${SITE}${PATH_DIRECTORY_DEC}"

# Scrape the page
HTML=$(curl -s "$SOURCE_URL_ENC"); info "Scraping: $SOURCE_URL_DEC"

# Extract file links
FILES=$(echo "$HTML" | grep -o '<a href="[^"]*\.zip"[^>]*>[^<]*</a>' | sed 's|<a href="[^"]*"[^>]*>\([^<]*\)</a>|\1|g' | sort)

if [[ -z "$FILES" ]]; then
    error "No .zip files found on the page"; exit 1
fi

# Apply filtering
if [[ -n "$FILTER_FILE" ]]; then
    # Determine filter command and validate
    if [[ -z "$FILTER_FILE" ]]; then
        error "Filter File not found"; exit 1
    elif [[ "$FILTER_FILE" == *.sed ]]; then
        filter_cmd="sed -E -f"
    elif [[ "$FILTER_FILE" == *.awk ]]; then
        filter_cmd="awk -f"
    else
        error "Filter file must be .sed or .awk: $FILTER_FILE"; exit 1
    fi

    # Count total files
    total_files=$(echo "$FILES" | wc -l); info "Filter file: $FILTER_FILE - Files: $total_files"

    # Apply filter
    FILES=$(echo "$FILES" | $filter_cmd "$FILTER_FILE" 2>/dev/null || echo "$FILES")

    # Count results
    filtered_count=$(echo "$FILES" | grep -c '^[^#]')
    excluded_count=$((total_files - filtered_count))
    info "Files Included | Excluded - $filtered_count | $excluded_count"
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
        if [[ -n "$file" && "$file" != \#* ]]; then echo "  \"$file\","
        elif [[ -n "$file" && "$SLIM_OUTPUT" == false ]]; then echo "  # \"${file#"#"}\","; fi
    done
    echo "]"
} > "$OUTPUT_PATH"; info "Generated $OUTPUT_PATH"

# Generate README if requested
if [[ "$GEN_README" == true ]]; then ./gen-readme.sh "$OUTPUT_PATH"; fi
