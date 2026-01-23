#!/bin/bash
# ROM Collection Downloader
# Downloads ROM files based on JSON configuration

set -e

# Default values
JSON_FILE=""
OUTPUT_DIR=""
DRY_RUN=false
QUIET=false
MAX_CONCURRENT=4

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_error() {
    echo -e "${RED}ERROR:${NC} $1" >&2
}

log_warn() {
    echo -e "${YELLOW}WARNING:${NC} $1" >&2
}

log_info() {
    if [ "$QUIET" = false ]; then
        echo -e "${BLUE}INFO:${NC} $1"
    fi
}

log_success() {
    if [ "$QUIET" = false ]; then
        echo -e "${GREEN}SUCCESS:${NC} $1"
    fi
}

# Show usage
usage() {
    cat << EOF
ROM Collection Downloader

Usage: $0 [OPTIONS] JSON_FILE

Arguments:
    JSON_FILE    Path to JSON configuration file

Options:
    -o, --output DIR     Output directory (default: ~/Downloads)
    -d, --dry-run        Show what would be downloaded without downloading
    -q, --quiet          Suppress informational output
    -c, --concurrency N  Maximum concurrent downloads (default: 4)
    -h, --help           Show this help message

JSON Format:
{
  "title": "Collection Title",
  "description": "Collection Description",
  "platforms": {
    "platform_key": {
      "title": "Platform Name",
      "directory": "output/directory",
      "urls": ["url1", "url2", ...]
    }
  }
}
EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -o|--output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -q|--quiet)
            QUIET=true
            shift
            ;;
        -c|--concurrency)
            MAX_CONCURRENT="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        -*)
            log_error "Unknown option: $1"
            usage
            exit 1
            ;;
        *)
            if [ -z "$JSON_FILE" ]; then
                JSON_FILE="$1"
            else
                log_error "Multiple JSON files specified"
                exit 1
            fi
            shift
            ;;
    esac
done

# Validate arguments
if [ -z "$JSON_FILE" ]; then
    log_error "JSON file is required"
    usage
    exit 1
fi

if [ ! -f "$JSON_FILE" ]; then
    log_error "JSON file not found: $JSON_FILE"
    exit 1
fi

# Set default output directory
if [ -z "$OUTPUT_DIR" ]; then
    OUTPUT_DIR="$HOME/Downloads"
fi

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Parse JSON
if ! command -v jq &> /dev/null; then
    log_error "jq is required but not installed. Please install jq to use this script."
    exit 1
fi

# Validate JSON structure
if ! jq -e '.platforms' "$JSON_FILE" >/dev/null 2>&1; then
    log_error "Invalid JSON format: missing 'platforms' key"
    exit 1
fi

TITLE=$(jq -r '.title // "ROM Collection"' "$JSON_FILE")
DESCRIPTION=$(jq -r '.description // ""' "$JSON_FILE")

log_info "Processing collection: $TITLE"
if [ -n "$DESCRIPTION" ]; then
    log_info "Description: $DESCRIPTION"
fi

# Count total files
TOTAL_FILES=$(jq '[.platforms[]?.urls[]?] | length' "$JSON_FILE")
log_info "Total files to process: $TOTAL_FILES"

if [ "$DRY_RUN" = true ]; then
    log_info "DRY RUN MODE - No files will be downloaded"
fi

# Process each platform
PLATFORM_KEYS=$(jq -r '.platforms | keys[]' "$JSON_FILE")

DOWNLOAD_COUNT=0
ERROR_COUNT=0

for PLATFORM_KEY in $PLATFORM_KEYS; do
    PLATFORM_TITLE=$(jq -r ".platforms[\"$PLATFORM_KEY\"].title" "$JSON_FILE")
    PLATFORM_DIR=$(jq -r ".platforms[\"$PLATFORM_KEY\"].directory // \"$PLATFORM_KEY\"" "$JSON_FILE")
    PLATFORM_DIR="$OUTPUT_DIR/$PLATFORM_DIR"

    log_info "Processing platform: $PLATFORM_TITLE"

    # Create platform directory
    if [ "$DRY_RUN" = false ]; then
        mkdir -p "$PLATFORM_DIR"
    fi

    # Get URLs for this platform
    URLS=$(jq -r ".platforms[\"$PLATFORM_KEY\"].urls[]?" "$JSON_FILE")

    if [ -z "$URLS" ]; then
        log_warn "No URLs found for platform: $PLATFORM_TITLE"
        continue
    fi

    if [ "$DRY_RUN" = true ]; then
        while IFS= read -r URL; do
            if [ -z "$URL" ] || [ "$URL" = "null" ]; then
                continue
            fi
            FILENAME=$(basename "$URL")
            OUTPUT_FILE="$PLATFORM_DIR/$FILENAME"
            echo "Would download: $URL -> $OUTPUT_FILE"
        done <<< "$URLS"
    else
        log_info "Downloading files for $PLATFORM_TITLE"
        # Extract URLs and feed to wget via stdin
        URL_LIST=""
        URL_COUNT=0
        while IFS= read -r URL; do
            if [ -z "$URL" ] || [ "$URL" = "null" ]; then
                continue
            fi
            URL_LIST="${URL_LIST}${URL}\n"
            URL_COUNT=$((URL_COUNT + 1))
        done <<< "$URLS"

        # Download all URLs for this platform using wget with stdin input
        if printf "$URL_LIST" | wget -np -c -e robots=off -R "index.html*" -P "$PLATFORM_DIR" -i - 2>/dev/null; then
            DOWNLOAD_COUNT=$((DOWNLOAD_COUNT + URL_COUNT))
            log_success "Downloaded $URL_COUNT files for $PLATFORM_TITLE"
        else
            log_error "Some downloads failed for $PLATFORM_TITLE"
            ERROR_COUNT=$((ERROR_COUNT + 1))
        fi
    fi
done

# Summary
if [ "$DRY_RUN" = true ]; then
    log_info "Dry run complete. Would download $TOTAL_FILES files."
else
    log_success "Download complete!"
    log_info "Downloaded: $DOWNLOAD_COUNT files"
    if [ $ERROR_COUNT -gt 0 ]; then
        log_warn "Errors: $ERROR_COUNT files failed"
    fi
fi

log_info "Files saved to: $OUTPUT_DIR"
