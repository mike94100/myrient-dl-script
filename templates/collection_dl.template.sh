#!/usr/bin/env bash
# Generated ROM/BIOS download script
# This script downloads files using wget

set -e

# Global variables
OUTPUT_DIR=""
SELECTED_PLATFORMS=()

# Platform configuration arrays
{PLATFORM_ARRAYS}

show_menu() {{
    echo "=== ROM/BIOS Download Script ==="
    echo ""
    echo "Current settings:"
    echo "  Platforms: ${{SELECTED_PLATFORMS[*]:-"None selected"}}"
    echo "  Output directory: ${{OUTPUT_DIR:-"Not set"}}"
    echo ""
    echo "Available platforms:"
    for i in "${{!PLATFORM_NAMES[@]}}"; do
        platform="${{PLATFORM_NAMES[$i]}}"
        if [[ " ${{SELECTED_PLATFORMS[*]}} " =~ " $platform " ]]; then
            echo "  [✓] $(($i+1))) $platform"
        else
            echo "  [ ] $(($i+1))) $platform"
        fi
    done
    echo ""
    echo "Options:"
    echo "  1) Select platforms"
    echo "  2) Set output directory"
    echo "  3) Continue with download"
    echo "  4) Cancel"
    echo ""
    read -p "Choose option (1-4): " choice
    case $choice in
        1)
            select_platforms
            ;;
        2)
            set_output_dir
            ;;
        3)
            if [ ${{SELECTED_PLATFORMS[@]}} -eq 0 ] || [ -z "$OUTPUT_DIR" ]; then
                echo "Error: Please select platforms and set output directory first."
                echo ""
                show_menu
                return
            fi
            confirm_download
            return
            ;;
        4)
            echo "Download cancelled."
            exit 0
            ;;
        *)
            echo "Invalid option. Please try again."
            echo ""
            show_menu
            return
            ;;
    esac
}}

select_platforms() {{
    echo ""
    echo "Enter platform numbers to toggle (space-separated) or 'all'/'none':"
    read -r input
    case $input in
        all)
            SELECTED_PLATFORMS=("${{PLATFORM_NAMES[@]}}")
            ;;
        none)
            SELECTED_PLATFORMS=()
            ;;
        *)
            for num in $input; do
                if [[ $num =~ ^[0-9]+$ ]] && [ $num -ge 1 ] && [ $num -le ${{PLATFORM_NAMES[@]}} ]; then
                    platform="${{PLATFORM_NAMES[$((num-1))]]}}"
                    if [[ " ${{SELECTED_PLATFORMS[*]}} " =~ " $platform " ]]; then
                        # Remove from selected
                        SELECTED_PLATFORMS=("${{SELECTED_PLATFORMS[@]/$platform}}")
                    else
                        # Add to selected
                        SELECTED_PLATFORMS+=("$platform")
                    fi
                fi
            done
            ;;
    esac
    show_menu
}}

set_output_dir() {{
    echo ""
    echo "Current output directory: ${{OUTPUT_DIR:-"Not set"}}"
    echo "Enter new output directory (press Enter for ~/Downloads):"
    read -r new_dir
    if [ -n "$new_dir" ]; then
        OUTPUT_DIR="$new_dir"
    elif [ -z "$OUTPUT_DIR" ]; then
        OUTPUT_DIR="$HOME/Downloads"
    fi
    show_menu
}}

confirm_download() {{
    echo ""
    echo "Ready to download:"
    echo "  Platforms: ${{SELECTED_PLATFORMS[*]}}"
    echo "  Output directory: $OUTPUT_DIR"
    echo ""
    read -p "Start download? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Download cancelled."
        show_menu
        return
    fi
}}

# Initialize with defaults
SELECTED_PLATFORMS={DEFAULT_PLATFORMS}
OUTPUT_DIR="$HOME/Downloads"

# Show initial menu
show_menu

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {{ echo -e "${{GREEN}}[$(date '+%H:%M:%S')] INFO: $1${{NC}}"; }}
log_warn() {{ echo -e "${{YELLOW}}[$(date '+%H:%M:%S')] WARN: $1${{NC}}"; }}
log_error() {{ echo -e "${{RED}}[$(date '+%H:%M:%S')] ERROR: $1${{NC}}"; }}

log_info "Starting {TOML_STEM} download to $OUTPUT_DIR"

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"
cd "$OUTPUT_DIR"

# Process selected platforms
for platform_name in "${{SELECTED_PLATFORMS[@]}}"; do
    log_info "Processing platform: $platform_name"

# Function to process a single platform by index
process_platform() {{
    local index=$1
    local platform_name="${{PLATFORM_NAMES[$index]}}"
    local platform_dir="${{PLATFORM_DIRS[$index]}}"
    local platform_url="${{PLATFORM_URLS[$index]}}"
    local should_extract="${{PLATFORM_EXTRACTS[$index]}}"

    log_info "Processing platform: $platform_name"

    # Create platform directory
    mkdir -p "$platform_dir"

    # Download URL list and filter comments
    local url_list_file=$(mktemp)
    curl -s "$platform_url" | grep -v "^#" | grep -v "^$" | tr -d "\\r" > "$url_list_file"

    # Check if we have any URLs
    if [ ! -s "$url_list_file" ]; then
        log_warn "No URLs found for $platform_name"
        rm -f "$url_list_file"
        return
    fi

    # Download all files using wget with URL list file
    log_info "Downloading files for $platform_name"
    wget -m -np -c -e robots=off -R "index.html*" --progress=bar -i "$url_list_file" -P "$platform_dir"

    # Clean up URL list file
    rm -f "$url_list_file"

    # Extract if needed
    if [ "$should_extract" = "1" ]; then
        log_info "Extracting files for $platform_name"
        cd "$platform_dir"
        for zip_file in *.zip; do
            if [ -f "$zip_file" ]; then
                log_info "Extracting $zip_file"
                if command -v unzip &> /dev/null; then
                    unzip -q "$zip_file"
                    rm "$zip_file"
                else
                    log_error "unzip command not available for extraction"
                    exit 1
                fi
            fi
        done
        cd ..
    fi

    log_info "Completed $platform_name"
}}

# Process selected platforms
for i in "${{!PLATFORM_NAMES[@]}}"; do
    platform_name="${{PLATFORM_NAMES[$i]}}"
    # Check if this platform was selected
    if [[ " ${{SELECTED_PLATFORMS[*]}} " =~ " $platform_name " ]]; then
        process_platform $i
    fi
done

log_info "Download completed successfully"
exit 0
