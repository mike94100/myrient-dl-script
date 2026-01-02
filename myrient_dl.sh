#!/usr/bin/env bash
# Myrient Download Script
# Downloads files from any TOML collection configuration

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() { echo -e "${GREEN}[$(date '+%H:%M:%S')] INFO: $1${NC}"; }
log_warn() { echo -e "${YELLOW}[$(date '+%H:%M:%S')] WARN: $1${NC}"; }
log_error() { echo -e "${RED}[$(date '+%H:%M:%S')] ERROR: $1${NC}"; exit 1; }

# Global variables
OUTPUT_DIR="$HOME/Downloads"
SELECTED_PLATFORMS=()
RESOLVED_URLS=()
TOML_URL=""
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if required tools are available
check_dependencies() {
    local missing=()
    command -v curl >/dev/null 2>&1 || missing+=("curl")
    command -v wget >/dev/null 2>&1 || missing+=("wget")

    if [ ${#missing[@]} -ne 0 ]; then
        echo "Error: Missing required tools: ${missing[*]}" >&2
        echo "Please install them and try again." >&2
        exit 1
    fi
}

# Fetch and parse TOML from URL or local file
fetch_toml() {
    local url="$1"

    if [[ "$url" =~ ^https?:// ]]; then
        # Remote URL
        log_info "Fetching TOML from: $url"
        local content=$(curl -s -A "Mozilla/5.0" "$url")
        if [ -z "$content" ]; then
            log_error "Failed to fetch TOML from $url - empty response"
        fi
        echo "$content"
    else
        # Local file - make path absolute relative to script directory
        local abs_path="$SCRIPT_DIR/$url"
        if [ -f "$abs_path" ]; then
            log_info "Reading TOML from local file: $abs_path"
            cat "$abs_path"
        else
            echo "Error: Local file not found: $abs_path" >&2
            exit 1
        fi
    fi
}

# Get platforms by type and selection status
get_platforms_by_type_and_status() {
    local type="$1"
    local selected="$2"
    local platforms_by_type=()
    for i in "${!PLATFORM_NAMES[@]}"; do
        local is_selected=false
        if [[ " ${SELECTED_PLATFORMS[*]} " == *" ${PLATFORM_NAMES[$i]} "* ]]; then
            is_selected=true
        fi

        if [ "${PLATFORM_TYPES[$i]}" = "$type" ] && [ "$is_selected" = "$selected" ]; then
            platforms_by_type+=("${PLATFORM_NAMES[$i]}")
        fi
    done
    echo "${platforms_by_type[*]:-"None"}"
}

# Parse platforms directly from TOML
parse_platforms_from_toml() {
    local toml_content="$1"

    # Extract platform sections and their data
    echo "$toml_content" | grep -A 10 '^\[roms\.' | grep -E '^\[|^\s*[^#].*=' | sed 's/^\[//' | sed 's/\]$//' || true
}

# Resolve relative URL
resolve_relative_url() {
    local toml_url="$1"
    local relative_path="$2"

    if [[ "$toml_url" =~ ^https?:// ]]; then
        # Remote URL: handle GitHub URLs properly
        if [[ "$toml_url" =~ ^https://raw\.githubusercontent\.com/[^/]+/[^/]+/[^/]+/ ]]; then
            # GitHub raw URL: https://raw.githubusercontent.com/user/repo/branch/...
            # Extract repo root: https://raw.githubusercontent.com/user/repo/branch/
            local repo_root=$(echo "$toml_url" | sed -E 's|^(https://raw\.githubusercontent\.com/[^/]+/[^/]+/[^/]+)/.*|\1|')
            local resolved_url="${repo_root}/${relative_path}"
            echo "$resolved_url"
        else
            # Generic remote URL: remove filename from TOML URL
            local base_url="${toml_url%/*}"
            local resolved_url="${base_url}/${relative_path}"
            echo "$resolved_url"
        fi
    else
        # Local file: paths are relative to repo root
        local resolved_path="$SCRIPT_DIR/$relative_path"
        echo "$resolved_path"
    fi
}

# Show interactive menu
show_menu() {
    while true; do
        echo "=== Myrient Download Script ==="
        echo "Collection: $TOML_URL"
        echo "Output directory: $OUTPUT_DIR"

        # Display platforms by type and status
        echo "Selected ROM platforms: $(get_platforms_by_type_and_status "roms" "true")"
        echo "Selected BIOS platforms: $(get_platforms_by_type_and_status "bios" "true")"
        echo "Unselected ROM platforms: $(get_platforms_by_type_and_status "roms" "false")"
        echo "Unselected BIOS platforms: $(get_platforms_by_type_and_status "bios" "false")"
        echo ""

        echo "Options:"
        echo "  1) Toggle platform selection"
        echo "  2) Set output directory"
        echo "  3) Dry run (preview download)"
        echo "  4) Start download"
        echo "  5) Cancel"
        echo ""

        read -p "Choose option (1-5): " choice

        case $choice in
            1)
                select_platforms
                ;;
            2)
                set_output_dir
                ;;
            3)
                if [ ${#SELECTED_PLATFORMS[@]} -eq 0 ]; then
                    echo "Error: Please select at least one platform first."
                    read -p "Press Enter to continue..."
                    continue
                fi
                dry_run
                ;;
            4)
                if [ ${#SELECTED_PLATFORMS[@]} -eq 0 ]; then
                    echo "Error: Please select at least one platform first."
                    read -p "Press Enter to continue..."
                    continue
                fi
                return 0
                ;;
            5)
                echo "Download cancelled."
                exit 0
                ;;
            *)
                echo "Invalid option. Please try again."
                read -p "Press Enter to continue..."
                ;;
        esac
    done
}

# Platform selection
select_platforms() {
    echo ""

    # Display ROM platforms
    local rom_count=0
    echo "ROM Platforms:"
    for i in "${!PLATFORM_NAMES[@]}"; do
        if [ "${PLATFORM_TYPES[$i]}" = "roms" ]; then
            local platform="${PLATFORM_NAMES[$i]}"
            local marker=" "
            if [[ " ${SELECTED_PLATFORMS[*]} " == *" $platform "* ]]; then
                marker="✓"
            fi
            printf "  [%s] %2d) %s" "$marker" "$((i+1))" "$platform"
            # Print in columns for better readability
            rom_count=$((rom_count + 1))
            if [ $((rom_count % 3)) -eq 0 ]; then
                echo ""
            else
                echo -n "    "
            fi
        fi
    done
    if [ $((rom_count % 3)) -ne 0 ]; then
        echo ""
    fi

    echo ""

    # Display BIOS platforms
    local bios_count=0
    echo "BIOS Platforms:"
    for i in "${!PLATFORM_NAMES[@]}"; do
        if [ "${PLATFORM_TYPES[$i]}" = "bios" ]; then
            local platform="${PLATFORM_NAMES[$i]}"
            local marker=" "
            if [[ " ${SELECTED_PLATFORMS[*]} " == *" $platform "* ]]; then
                marker="✓"
            fi
            printf "  [%s] %2d) %s" "$marker" "$((i+1))" "$platform"
            # Print in columns for better readability
            bios_count=$((bios_count + 1))
            if [ $((bios_count % 3)) -eq 0 ]; then
                echo ""
            else
                echo -n "    "
            fi
        fi
    done
    if [ $((bios_count % 3)) -ne 0 ]; then
        echo ""
    fi

    echo ""
    echo "Enter platform numbers to toggle (space-separated) or 'all'/'none':"
    read -r input

    case $input in
        all)
            SELECTED_PLATFORMS=("${PLATFORM_NAMES[@]}")
            ;;
        none)
            SELECTED_PLATFORMS=()
            ;;
        *)
            for num in $input; do
                if [[ $num =~ ^[0-9]+$ ]] && [ $num -ge 1 ] && [ $num -le ${#PLATFORM_NAMES[@]} ]; then
                    local platform="${PLATFORM_NAMES[$((num-1))]}"
                    local found=0
                    local new_selected=()

                    # Check if platform is already selected and rebuild array
                    for selected in "${SELECTED_PLATFORMS[@]}"; do
                        if [ "$selected" = "$platform" ]; then
                            found=1
                        else
                            new_selected+=("$selected")
                        fi
                    done

                    if [ $found -eq 0 ]; then
                        # Add to selected
                        new_selected+=("$platform")
                    fi

                    SELECTED_PLATFORMS=("${new_selected[@]}")
                fi
            done
            ;;
    esac
}

# Set output directory
set_output_dir() {
    echo ""
    echo "Current output directory: $OUTPUT_DIR"
    echo "Enter new output directory (press Enter for ~/Downloads):"
    read -r new_dir
    if [ -n "$new_dir" ]; then
        OUTPUT_DIR="$new_dir"
    elif [ -z "$OUTPUT_DIR" ]; then
        OUTPUT_DIR="$HOME/Downloads"
    fi
}

# Dry run - show what will be downloaded
dry_run() {
    echo ""
    echo "=== DRY RUN - Preview Download ==="
    echo "Output directory: $OUTPUT_DIR"
    echo "Selected ROM platforms: $(get_platforms_by_type_and_status "roms" "true")"
    echo "Selected BIOS platforms: $(get_platforms_by_type_and_status "bios" "true")"
    echo ""

    echo "Directories that will be created:"

    for platform_name in "${SELECTED_PLATFORMS[@]}"; do
        # Find platform data
        for i in "${!PLATFORM_NAMES[@]}"; do
            if [ "${PLATFORM_NAMES[$i]}" = "$platform_name" ]; then
                local platform_dir="${PLATFORM_DIRS[$i]}"
                local full_platform_dir="$OUTPUT_DIR/$platform_dir"

                # Try to fetch URL list to show count
                local urllist_path="${URL_LISTS[$i]}"
                local urllist_url="$(resolve_relative_url "$TOML_URL" "$urllist_path")"

                if [[ "$urllist_url" =~ ^https?:// ]]; then
                    local url_count=$(curl -s -A "Mozilla/5.0" "$urllist_url" | grep -v '^#' | grep -v '^$' | wc -l)
                else
                    local url_count=$(grep -v '^#' "$urllist_url" 2>/dev/null | grep -v '^$' | wc -l)
                fi

                if [ "$url_count" -gt 0 ]; then
                    echo "  $full_platform_dir ($url_count files)"
                else
                    echo "  $full_platform_dir (Could not fetch URL list)"
                fi
                break
            fi
        done
    done

    echo ""
    read -p "Press Enter to return to menu..."
}

# Download files for a platform
download_platform() {
    local platform_name="$1"
    local platform_dir="$2"
    local urllist_url="$3"
    local should_extract="$4"

    log_info "Processing platform: $platform_name"

    # Create platform directory
    mkdir -p "$OUTPUT_DIR/$platform_dir"

    # Fetch URL list
    local urls=""
    if [[ "$urllist_url" =~ ^https?:// ]]; then
        log_info "Fetching URL list from remote: $urllist_url"
        local raw_urls=$(curl -s -A "Mozilla/5.0" "$urllist_url")
        if [ -z "$raw_urls" ]; then
            log_warn "curl returned empty response for $urllist_url"
        else
            urls=$(echo "$raw_urls" | grep -v '^#' | grep -v '^$')
        fi
    else
    log_info "Reading URL list from local file: $urllist_url"
    if [ -f "$urllist_url" ]; then
        urls=$(grep -v '^#' "$urllist_url" | grep -v '^$')
        if [ -z "$urls" ]; then
            log_warn "No URLs found in local file $urllist_url"
        fi
    else
        log_warn "Could not read URL list file: $urllist_url"
        urls=""
    fi
    fi

    if [ -z "$urls" ]; then
        log_warn "No URLs found for $platform_name"
        return
    fi

    # Create temporary URL list file for wget
    local url_list_file=$(mktemp)
    echo "$urls" > "$url_list_file"

    # Download files
    log_info "Downloading files for $platform_name"
    if wget -q -np -c -i "$url_list_file" -P "$OUTPUT_DIR/$platform_dir"; then
        # Clean up URL list file
        rm -f "$url_list_file"

        # Extract if needed
        if [ "$should_extract" = "true" ]; then
            log_info "Extracting files for $platform_name"
            cd "$OUTPUT_DIR/$platform_dir"
            for zip_file in *.zip; do
                if [ -f "$zip_file" ]; then
                    if command -v unzip >/dev/null 2>&1; then
                        unzip -q "$zip_file" && rm "$zip_file"
                    else
                        log_error "unzip command not available for extraction"
                    fi
                fi
            done
            cd - >/dev/null
        fi
    else
        rm -f "$url_list_file"
        log_error "wget failed for $platform_name"
    fi
}

# Main function
main() {
    # Check dependencies
    check_dependencies

    # Parse arguments
    if [ $# -lt 1 ]; then
        echo "Usage: $0 <collection_url> [-o output_dir] [--non-interactive]" >&2
        exit 1
    fi

    TOML_URL="$1"
    shift

    while [ $# -gt 0 ]; do
        case $1 in
            -o|--output)
                OUTPUT_DIR="$2"
                shift 2
                ;;
            --non-interactive)
                NON_INTERACTIVE=1
                shift
                ;;
            *)
                echo "Unknown option: $1" >&2
                exit 1
                ;;
        esac
    done

    # Set default output directory
    OUTPUT_DIR="${OUTPUT_DIR:-$HOME/Downloads}"

    # Fetch and parse TOML
    local toml_content=$(fetch_toml "$TOML_URL")

    # Parse platforms directly from TOML
    # Find all platform sections and process them
    local platform_sections=$(echo "$toml_content" | grep '^\[roms\.' | sed 's/^\[//' | sed 's/\]$//' && echo "$toml_content" | grep '^\[bios\.' | sed 's/^\[//' | sed 's/\]$//')

    for section in $platform_sections; do
        if [[ "$section" =~ ^(roms|bios)\.(.+)$ ]]; then
            local section_type="${BASH_REMATCH[1]}"
            local platform_name="${BASH_REMATCH[2]}"

            # Extract the section content (between section header and next section or end)
            local section_content=$(echo "$toml_content" | awk -v section="[$section_type.$platform_name]" '
            BEGIN { in_section = 0 }
            /^\[/ { if (in_section && $0 != section) exit; if ($0 == section) in_section = 1; next }
            in_section { print }
            ')

            # Parse the key=value pairs
            local directory=""
            local urllist=""
            local extract="false"

            while IFS= read -r line; do
                # Skip comments and empty lines
                [[ "$line" =~ ^[[:space:]]*# ]] && continue
                [[ "$line" =~ ^[[:space:]]*$ ]] && continue

                if [[ "$line" =~ ^[[:space:]]*([^=]+)[[:space:]]*=[[:space:]]*(.+)[[:space:]]*$ ]]; then
                    local key="${BASH_REMATCH[1]}"
                    local value="${BASH_REMATCH[2]}"

                    # Trim key
                    key="${key// /}"

                    # Remove quotes
                    value="${value#\"}"
                    value="${value%\"}"

                    case "$key" in
                        directory) directory="$value" ;;
                        urllist) urllist="$value" ;;
                        extract) extract="$value" ;;
                    esac
                fi
            done <<< "$section_content"

            # Add platform if we have required fields
            if [ -n "$platform_name" ] && [ -n "$directory" ] && [ -n "$urllist" ]; then
                PLATFORM_NAMES+=("$platform_name")
                PLATFORM_DIRS+=("$directory")
                URL_LISTS+=("$urllist")
                SHOULD_EXTRACT+=("$extract")
                PLATFORM_TYPES+=("$section_type")
            fi
        fi
    done

    if [ ${#PLATFORM_NAMES[@]} -eq 0 ]; then
        echo "Error: No platforms found in collection" >&2
        exit 1
    fi

    # Initialize selected platforms
    if [ "$NON_INTERACTIVE" = "1" ]; then
        SELECTED_PLATFORMS=("${PLATFORM_NAMES[@]}")
    else
        SELECTED_PLATFORMS=("${PLATFORM_NAMES[@]}")
        show_menu
    fi

    # Resolve URL list paths before changing directories
    for i in "${!PLATFORM_NAMES[@]}"; do
        local platform_name="${PLATFORM_NAMES[$i]}"
        if [[ " ${SELECTED_PLATFORMS[*]} " == *" $platform_name "* ]]; then
            local urllist_path="${URL_LISTS[$i]}"
            local resolved_url=$(resolve_relative_url "$TOML_URL" "$urllist_path")
            RESOLVED_URLS[$i]="$resolved_url"
        fi
    done

    # Create output directory
    mkdir -p "$OUTPUT_DIR"
    cd "$OUTPUT_DIR"

    # Download selected platforms
    log_info "Starting download to $OUTPUT_DIR"

    for i in "${!PLATFORM_NAMES[@]}"; do
        local platform_name="${PLATFORM_NAMES[$i]}"
        if [[ " ${SELECTED_PLATFORMS[*]} " == *" $platform_name "* ]]; then
            local platform_dir="${PLATFORM_DIRS[$i]}"
            local urllist_path="${URL_LISTS[$i]}"
            local urllist_url=$(resolve_relative_url "$TOML_URL" "$urllist_path")
            local should_extract="${SHOULD_EXTRACT[$i]}"

            download_platform "$platform_name" "$platform_dir" "$urllist_url" "$should_extract"
        fi
    done

    log_info "Download completed successfully"
}

# Run main function
main "$@"
