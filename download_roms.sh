#!/bin/bash
# Myrient ROM Downloader Bootstrap Script
# Downloads Python code from main repo and handles TOML resolution

set -e

# Default to sample meta TOML
DEFAULT_TOML="https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/dl/sample/sample.toml"
TOML_SOURCE=${1:-$DEFAULT_TOML}
OUTPUT_DIR=${2:-"./roms"}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Myrient ROM Downloader${NC}"
echo "TOML Source: $TOML_SOURCE"
echo "Output Directory: $OUTPUT_DIR"
echo

# Create temp directory
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

echo -e "${YELLOW}Step 1: Downloading Python code from main repo...${NC}"
cd "$TEMP_DIR"
git clone --depth=1 --quiet https://github.com/mike94100/myrient-dl-script.git repo
cd repo

echo -e "${YELLOW}Step 2: Installing dependencies...${NC}"
python3 -m pip install --quiet -r requirements.txt

echo -e "${YELLOW}Step 3: Processing TOML configuration...${NC}"

# Function to download file
download_file() {
    local url=$1
    local dest=$2
    if command -v curl &> /dev/null; then
        curl -s -L "$url" -o "$dest"
    elif command -v wget &> /dev/null; then
        wget -q "$url" -O "$dest"
    else
        echo -e "${RED}Error: Neither curl nor wget found${NC}"
        exit 1
    fi
}

# Function to resolve URL relative to base
resolve_url() {
    local base=$1
    local rel=$2

    # If rel starts with http, it's already absolute
    if [[ $rel == http* ]]; then
        echo "$rel"
        return
    fi

    # Remove filename from base URL to get directory
    local base_dir=$(dirname "$base")

    # If rel starts with /, it's absolute from domain
    if [[ $rel == /* ]]; then
        # Extract protocol and domain from base
        local proto=$(echo "$base" | sed 's|^\(.*://\).*|\1|')
        local domain=$(echo "$base" | sed 's|.*://\([^/]*\).*|\1|')
        echo "${proto}${domain}${rel}"
    else
        # Relative path - combine with base directory
        echo "${base_dir}/${rel}"
    fi
}

# Check if TOML is meta (contains platform_tomls)
is_meta_toml() {
    local file=$1
    grep -q "platform_tomls" "$file"
}

# Download and process TOML
TOML_FILE="$TEMP_DIR/toml_source.toml"
download_file "$TOML_SOURCE" "$TOML_FILE"

if is_meta_toml "$TOML_FILE"; then
    echo "Detected meta TOML - downloading platform TOMLs..."

    # Platform TOMLs will be downloaded directly to temp dir
    PLATFORM_DIR="$TEMP_DIR"

    # Extract platform_tomls array and download each
    # This is a simple extraction - assumes TOML format with platform_tomls = [...]
    PLATFORM_TOMLS=$(sed -n '/platform_tomls = \[/,/]/p' "$TOML_FILE" | grep '"' | sed 's/.*"\([^"]*\)".*/\1/')

    # Create new meta TOML with local paths
    NEW_META="$TEMP_DIR/meta_local.toml"
    cp "$TOML_FILE" "$NEW_META"

    local_paths=()
    while IFS= read -r platform_ref; do
        if [[ -n "$platform_ref" ]]; then
            # Resolve URL
            resolved_url=$(resolve_url "$TOML_SOURCE" "$platform_ref")

            # Download to local file
            local_file="$PLATFORM_DIR/$(basename "$platform_ref")"
            echo "Downloading $resolved_url -> $local_file"
            download_file "$resolved_url" "$local_file"

            # Store local path for meta TOML
            local_paths+=("$local_file")
        fi
    done <<< "$PLATFORM_TOMLS"

    # Update meta TOML with local paths
    # Simple replacement - replace the platform_tomls array
    local_paths_str=$(printf '"%s", ' "${local_paths[@]}")
    local_paths_str="[${local_paths_str%, }]"
    sed -i.bak "s|platform_tomls = \[.*\]|platform_tomls = $local_paths_str|" "$NEW_META"

    FINAL_TOML="$NEW_META"
else
    echo "Using platform TOML directly"
    FINAL_TOML="$TOML_FILE"
fi

echo -e "${YELLOW}Step 4: Starting ROM download...${NC}"
echo "Using TOML: $FINAL_TOML"
echo "Output: $OUTPUT_DIR"
echo

# Run the download
python3 myrient_dl.py "$FINAL_TOML" -o "$OUTPUT_DIR"

echo
echo -e "${GREEN}Download complete! ROMs saved to: $OUTPUT_DIR${NC}"
