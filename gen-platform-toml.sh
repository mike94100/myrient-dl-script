#!/usr/bin/env bash
set -uo pipefail

# Source utility functions
. ./url-utils.sh

# Source progress bar functions
. ./progress.sh


# Generate platform TOML by scraping Myrient page
# Usage: gen-platform-toml.sh [OPTIONS] <subdomain_path> <output_file>
# Usage: gen-platform-toml.sh [OPTIONS] <base_url> <subdomain_path> <output_file>

log() {
    echo "$*" >&2
}

# Validate subdomain path
validate_subdomain_path() {
    local path="$1"

    # Check if it looks like a full URL
    if [[ "$path" =~ ^https?:// ]]; then
        log "ERROR: subdomain_path should not be a full URL. Use only the path part."
        log "Example: 'No-Intro/Nintendo%20-%20Game%20Boy/'"
        return 1
    fi

    # Check for protocol separators
    if [[ "$path" =~ :// ]]; then
        log "ERROR: subdomain_path should not contain protocol separators."
        return 1
    fi

    # Check if it looks like an absolute file path
    if [[ "$path" =~ ^/ ]]; then
        log "ERROR: subdomain_path should be a relative path, not an absolute file path."
        return 1
    fi

    # Check if it ends with a file extension
    if [[ "$path" =~ \.[a-zA-Z0-9]+$ ]]; then
        log "ERROR: subdomain_path should not end with a file extension."
        log "It should be a directory path, not a file path."
        return 1
    fi

    # Should contain at least one path separator to look like a proper subdomain
    if [[ "$path" != *"/"* ]]; then
        log "ERROR: subdomain_path should contain path separators (e.g., 'No-Intro/Nintendo%20-%20Game%20Boy/')"
        return 1
    fi

    return 0
}

# Parse patterns from a group string
# Returns an array of patterns via the patterns_array variable
parse_group_patterns() {
    local group="$1"
    # Use a global array to return results
    patterns_array=()

    quoted_patterns=$(echo "$group" | sed "s/'/ /g")
    quoted_patterns=$(echo "$quoted_patterns" | sed 's/^ *//;s/ *$//')
    if [[ -n "$quoted_patterns" ]]; then
        # Split by spaces into array
        IFS=' ' read -ra patterns_array <<< "$quoted_patterns"
    fi
    # If no patterns found, treat the whole string as one pattern
    if [[ ${#patterns_array[@]} -eq 0 && -n "$group" ]]; then
        patterns_array=("$group")
    fi
}

show_help() {
    cat << EOF
NAME
    gen-platform-toml.sh - Generate platform TOML files by scraping Myrient pages

SYNOPSIS
    gen-platform-toml.sh [OPTIONS] <subdomain_path> <output_file>
    gen-platform-toml.sh [OPTIONS] <base_url> <subdomain_path> <output_file>

DESCRIPTION
    This script generates TOML configuration files for the myrient-dl.sh ROM downloader
    by scraping Myrient download pages. It automatically discovers all available .zip
    files on a given platform page and creates a properly formatted TOML file.

ARGUMENTS
    base_url (optional)
        The base URL for Myrient. Defaults to 'https://myrient.erista.me/files/'
        Only specify this if you need to use a different Myrient instance.

    subdomain_path
        The platform-specific path under the base URL. This should include the
        collection and platform directories (e.g., 'No-Intro/Nintendo%20-%20Game%20Boy/')
        Must be a relative subdomain path, not a full URL or file path.

    output_file
        The path of the TOML file to generate (e.g., gb.toml or n64/n64.toml).
        Any directories in the path will be created automatically. The directory
        field in the TOML will be derived from the full path.

OPTIONS
    -e, --exclude PATTERNS...
        Exclude files whose names contain any of the specified PATTERNS.
        Multiple patterns can be provided as separate arguments after -e/--exclude.
        Example: -e '(Beta)' '(Proto)' '(Demo)'

    -i, --include PATTERNS...
        Include only files whose names contain patterns from all specified groups.
        Each -i option defines a pattern group (OR logic within group).
        Files must match at least one pattern from each group (AND logic between groups).
        Multiple patterns can be provided as separate arguments after each -i/--include.
        Example (single pattern): -i "Pokemon"
        Example (multiple patterns): -i "'Pokemon' 'Mario'" -i "(USA"

    -f, --filter-file FILE
        Load filter patterns from a TOML file. The file can import other filter files
        and combine exclude patterns and include groups recursively.
        Cannot be used with -i or -e options.
        Example: -f "testfilter/testfilter.toml"

    -g, --gen-readme
        Automatically generate a README.md file for the created TOML configuration.

    --cache-ttl SECONDS
        Set cache validity time in seconds (default: 604800 = 7 days).
        Cached content will be reused if newer than this TTL.

    --no-cache
        Disable caching and always fetch fresh content.

    -h, --help
        Display this help message and exit.

EXAMPLES
    Generate a Game Boy TOML file (using default base URL):
        gen-platform-toml.sh 'No-Intro/Nintendo%20-%20Game%20Boy/' gb.toml

    Generate a GBA TOML file including Pokemon games and excluding beta versions:
        gen-platform-toml.sh 'No-Intro/Nintendo%20-%20Game%20Boy%20Advance/' gba.toml -i 'Pokemon' -e '(Beta)'

    Use custom base URL:
        gen-platform-toml.sh 'https://custom.myrient.com/files/' 'No-Intro/Nintendo%20-%20Game%20Boy/' gb.toml

    Generate TOML file in subdirectory (creates directory automatically):
        gen-platform-toml.sh 'No-Intro/Nintendo%20-%20Nintendo%2064%20%28BigEndian%29/' n64/n64.toml

    Generate TOML file with automatic README generation:
        gen-platform-toml.sh -g 'No-Intro/Nintendo%20-%20Game%20Boy/' gb.toml

OUTPUT FORMAT
    The generated TOML file contains the following fields:

    base_url
        The base URL used for constructing download URLs

    subdomain
        The provided subdomain_path (used to construct download URLs)

    directory
        Automatically derived from output_file (e.g., gb.toml → "gb/")

    exclude_patterns (optional)
        Array of patterns that were used to filter files during generation.
        Only present when -e/--exclude option was used.

    include_groups (optional)
        Array of pattern groups that were used to filter files during generation.
        Only present when -i/--include option was used.

    files
        An array of human-readable .zip filenames found on the page, sorted alphabetically

BEHAVIOR
    - Files are scraped from the constructed URL: base_url + subdomain_path
    - Only .zip files are included in the files array
    - Files are listed in alphabetical order
    - The script requires internet access to scrape Myrient pages
    - Generated TOML files are compatible with myrient-dl.sh
EOF
}

# Parse options using getopt
TEMP=$(getopt -o 'hi:e:f:g' --long 'help,include:,exclude:,filter-file:,gen-readme,cache-ttl:,no-cache' -n 'gen-platform-toml' -- "$@")
if [[ $? -ne 0 ]]; then
    log "Use -h or --help for usage"
    exit 1
fi

eval set -- "$TEMP"

EXCLUDE_PATTERNS=()
INCLUDE_PATTERNS=()
FILTER_FILE=""
GEN_README=false
CACHE_TTL=604800  # 7 days in seconds
NO_CACHE=false

while true; do
    case "$1" in
        -h|--help)
            show_help
            exit 0
            ;;
        -i|--include)
            INCLUDE_PATTERNS+=("$2")
            shift 2
            ;;
        -e|--exclude)
            EXCLUDE_PATTERNS+=("$2")
            shift 2
            ;;
        -f|--filter-file)
            FILTER_FILE="$2"
            shift 2
            ;;
        -g|--gen-readme)
            GEN_README=true
            shift
            ;;
        --cache-ttl)
            CACHE_TTL="$2"
            shift 2
            ;;
        --no-cache)
            NO_CACHE=true
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

# Validate that -f is exclusive from -i and -e
if [[ -n "$FILTER_FILE" && (${#INCLUDE_PATTERNS[@]} -gt 0 || ${#EXCLUDE_PATTERNS[@]} -gt 0) ]]; then
    log "ERROR: -f/--filter-file cannot be used with -i/--include or -e/--exclude options"
    exit 1
fi

# Load filter file if specified
if [[ -n "$FILTER_FILE" ]]; then
    log "Loading filter file: $FILTER_FILE"
    FILTER_DATA=$(python3 -c '
import sys
import tomllib
import os
from pathlib import Path

def load_filter_recursive(filepath, processed=None):
    if processed is None:
        processed = set()
    
    # Avoid circular imports
    abs_path = os.path.abspath(filepath)
    if abs_path in processed:
        return {}
    processed.add(abs_path)
    
    if not os.path.exists(filepath):
        print(f"ERROR: Filter file not found: {filepath}", file=sys.stderr)
        sys.exit(1)
    
    with open(filepath, "rb") as f:
        data = tomllib.load(f)
    
    combined = {
        "exclude_patterns": data.get("exclude_patterns", []),
        "include_groups": data.get("include_groups", [])
    }
    
    # Process imports
    imports = data.get("filter_imports", [])
    base_dir = os.path.dirname(filepath)
    for imp in imports:
        imp_path = os.path.join(base_dir, imp)
        imported = load_filter_recursive(imp_path, processed)
        combined["exclude_patterns"].extend(imported.get("exclude_patterns", []))
        combined["include_groups"].extend(imported.get("include_groups", []))
    
    # Deduplicate
    combined["exclude_patterns"] = list(dict.fromkeys(combined["exclude_patterns"]))
    # For include_groups, deduplicate by converting to tuples
    seen = set()
    deduped_groups = []
    for group in combined["include_groups"]:
        group_tuple = tuple(group) if isinstance(group, list) else (group,)
        if group_tuple not in seen:
            seen.add(group_tuple)
            deduped_groups.append(group)
    combined["include_groups"] = deduped_groups
    
    return combined

result = load_filter_recursive("'$FILTER_FILE'")
# Normalize include_groups to list of lists
normalized_include_groups = []
for g in result["include_groups"]:
    if isinstance(g, list):
        normalized_include_groups.append(g)
    else:
        normalized_include_groups.append([g])
result["include_groups"] = normalized_include_groups
print("EXCLUDE_PATTERNS=(" + " ".join(result["exclude_patterns"]) + ")")
include_groups_str = "|".join(" ".join(group) for group in result["include_groups"])
print("INCLUDE_GROUPS=(" + include_groups_str + ")")
' 2>&1)

    if [[ $? -ne 0 ]]; then
        log "ERROR: Failed to load filter file"
        log "$FILTER_DATA"
        exit 1
    fi

    # Parse the output
    while IFS= read -r line; do
        if [[ "$line" =~ ^EXCLUDE_PATTERNS=\((.*)\)$ ]]; then
            EXCLUDE_PATTERNS_STR="${BASH_REMATCH[1]}"
            # Parse space-separated values
            EXCLUDE_PATTERNS=($EXCLUDE_PATTERNS_STR)
        elif [[ "$line" =~ ^INCLUDE_GROUPS=\((.*)\)$ ]]; then
            INCLUDE_GROUPS_STR="${BASH_REMATCH[1]}"
            # For simplicity, convert to the format expected by the existing code
            # Each group becomes a string like "'pattern1' 'pattern2'"
            INCLUDE_PATTERNS=()
            # Split by |
            IFS='|' read -ra groups <<< "$INCLUDE_GROUPS_STR"
            for group in "${groups[@]}"; do
                # Trim spaces
                group_clean=$(echo "$group" | sed 's/^ *//;s/ *$//')
                if [[ -n "$group_clean" ]]; then
                    # Convert array format to quoted string format
                    quoted_group=""
                    for item in $group_clean; do
                        quoted_group="$quoted_group '$item'"
                    done
                    quoted_group=$(echo "$quoted_group" | sed 's/^ *//')
                    INCLUDE_PATTERNS+=("$quoted_group")
                fi
            done
        fi
    done <<< "$FILTER_DATA"

    log "Loaded exclude patterns: ${EXCLUDE_PATTERNS[*]}"
    log "Loaded include groups: ${INCLUDE_PATTERNS[*]}"
fi

# Check remaining arguments - support both 2 and 3 argument formats
if [[ $# -eq 2 ]]; then
    # 2 args: subdomain_path output_file (use default base URL)
    BASE_URL_DEC="https://myrient.erista.me/files/"
    BASE_URL_ENC="https://myrient.erista.me/files/"
    SUBDOMAIN_PATH_DEC=$(url_decode "$1")
    SUBDOMAIN_PATH_ENC=$(url_encode "$1")
    OUTPUT_FILE="$2"
elif [[ $# -eq 3 ]]; then
    # 3 args: base_url subdomain_path output_file
    BASE_URL_DEC=$(url_decode "$1")
    BASE_URL_ENC=$(url_encode "$1")
    SUBDOMAIN_PATH_DEC=$(url_decode "$2")
    SUBDOMAIN_PATH_ENC=$(url_encode "$2")
    OUTPUT_FILE="$3"
else
    log "Usage: gen-platform-toml.sh [OPTIONS] <subdomain_path> <output_file>"
    log "   or: gen-platform-toml.sh [OPTIONS] <base_url> <subdomain_path> <output_file>"
    log "Use -h or --help for detailed help"
    exit 1
fi

# Validate subdomain path
if ! validate_subdomain_path "$SUBDOMAIN_PATH_DEC"; then
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

# Construct full URL
FULL_URL_ENC="${BASE_URL_ENC%/}/${SUBDOMAIN_PATH_ENC#/}"

log "Scraping: $FULL_URL_ENC"
log "Base URL: $BASE_URL_DEC"
log "Subdomain: $SUBDOMAIN_PATH_DEC"
log "Directory: $DIRECTORY"
log "Output: $OUTPUT_PATH"

# Cache functions
get_cache_dir() {
    echo "${XDG_CACHE_HOME:-$HOME/.cache}/myrient-dl"
}

get_cache_key() {
    echo "$FULL_URL_ENC" | sha256sum | cut -d' ' -f1
}

is_cache_valid() {
    local cache_file="$1"
    local meta_file="${cache_file}.meta"
    
    if [[ ! -f "$cache_file" || ! -f "$meta_file" ]]; then
        return 1
    fi
    
    local cache_time
    cache_time=$(stat -c %Y "$cache_file" 2>/dev/null || stat -f %m "$cache_file" 2>/dev/null)
    if [[ -z "$cache_time" ]]; then
        return 1
    fi
    
    local current_time
    current_time=$(date +%s)
    
    if (( current_time - cache_time > CACHE_TTL )); then
        return 1
    fi
    
    return 0
}

# Scrape the page with caching
if [[ "$NO_CACHE" == false ]]; then
    CACHE_DIR=$(get_cache_dir)
    CACHE_KEY=$(get_cache_key)
    CACHE_FILE="${CACHE_DIR}/${CACHE_KEY}"
    
    mkdir -p "$CACHE_DIR"
    
    if is_cache_valid "$CACHE_FILE"; then
        log "Using cached content"
        HTML=$(cat "$CACHE_FILE")
    else
        log "Fetching fresh content"
        HTML=$(curl -s "$FULL_URL_ENC")
        if [[ -n "$HTML" ]]; then
            echo "$HTML" > "$CACHE_FILE"
        fi
    fi
else
    log "Fetching fresh content (cache disabled)"
    HTML=$(curl -s "$FULL_URL_ENC")
fi

# Extract file links - capture link text only
FILES=$(echo "$HTML" | grep -o '<a href="[^"]*\.zip"[^>]*>[^<]*</a>' | sed 's|<a href="[^"]*"[^>]*>\([^<]*\)</a>|\1|g' | sort)

if [[ -z "$FILES" ]]; then
    log "ERROR: No .zip files found on the page"
    exit 1
fi

# Apply filtering patterns if any exist
if [[ ${#INCLUDE_PATTERNS[@]} -gt 0 || ${#EXCLUDE_PATTERNS[@]} -gt 0 ]]; then
    if [[ ${#INCLUDE_PATTERNS[@]} -gt 0 ]]; then
        # Format the groups for readable display
        group_descriptions=()
        for group in "${INCLUDE_PATTERNS[@]}"; do
            parse_group_patterns "$group"
            # Join patterns with " | " for display
            group_descriptions+=("($(printf '%s | ' "${patterns_array[@]}" | sed 's/ | $//'))")
        done
        # Join groups with " AND " for display
        logic_description=$(printf '%s AND ' "${group_descriptions[@]}" | sed 's/ AND $//')
        log "Including only files matching: $logic_description"
    fi
    if [[ ${#EXCLUDE_PATTERNS[@]} -gt 0 ]]; then
        log "Excluding files matching patterns: ${EXCLUDE_PATTERNS[*]}"
    fi

    FILTERED_FILES=""
    included_count=0
    excluded_count=0
    total_processed=0
    total_files=$(echo "$FILES" | wc -l)

    while IFS= read -r file; do
        if [[ -n "$file" ]]; then  # Skip empty lines
            ((total_processed++))
            # Show progress
            if [[ -t 1 ]]; then
                show_progress -c $total_processed -t $total_files
            else
                if (( total_processed % 100 == 0 )); then
                    log "Processing files... ($total_processed/$total_files)"
                fi
            fi

            # Check excludes first - short circuit if matched
            if [[ ${#EXCLUDE_PATTERNS[@]} -gt 0 ]]; then
                for pattern in "${EXCLUDE_PATTERNS[@]}"; do
                    if [[ "$file" == *"$pattern"* ]]; then
                        ((excluded_count++))
                        continue 2  # Skip to next file
                    fi
                done
            fi

            # Check includes only if not excluded
            if [[ ${#INCLUDE_PATTERNS[@]} -gt 0 ]]; then
                # Must match at least one pattern from EACH include group (AND logic)
                group_index=0

                for group in "${INCLUDE_PATTERNS[@]}"; do
                    ((group_index++))
                    parse_group_patterns "$group"

                    # Check if file matches at least one pattern in this group
                    for pattern in "${patterns_array[@]}"; do
                        if [[ "$file" == *"$pattern"* ]]; then
                            # If we matched all groups, include the file
                            if [[ $group_index -eq ${#INCLUDE_PATTERNS[@]} ]]; then
                                FILTERED_FILES="${FILTERED_FILES}${file}\n"
                                ((included_count++))
                            fi
                            # Found match for this group, move to next group
                            continue 2
                        fi
                    done
                    # No pattern in this group matched - exclude this file
                    ((excluded_count++))
                    continue 2
                done
            else
                # No includes specified - include by default
                FILTERED_FILES="${FILTERED_FILES}${file}\n"
                ((included_count++))
            fi
        fi
    done <<< "$FILES"

    # Clear progress bar line
    if [[ -t 1 ]]; then
        printf "\r%*s\r" "$(tput cols)" "" >&2
    fi

    FILES=$(printf '%b\n' "$FILTERED_FILES" | sed '/^$/d')

    log "Processed $total_processed files"
    if [[ ${#EXCLUDE_PATTERNS[@]} -gt 0 ]]; then
        log "Excluded $excluded_count files"
    fi
    if [[ ${#INCLUDE_PATTERNS[@]} -gt 0 ]]; then
        log "Included $included_count files"
    fi
fi

log "Found $(echo "$FILES" | wc -l) files"

# Write TOML
{
    echo "# Base URL used for downloading files:"
    echo "base_url = \"$BASE_URL_DEC\""
    echo ""

    echo "# Subdomain path appended to base_url:"
    echo "subdomain = \"$SUBDOMAIN_PATH_DEC\""
    echo ""

    echo "# Directory where files will be downloaded:"
    echo "directory = \"$DIRECTORY\""
    echo ""

    # Include exclude patterns if any were used
    if [[ ${#EXCLUDE_PATTERNS[@]} -gt 0 ]]; then
        echo "# Exclude patterns used during generation:"
        echo "exclude_patterns = ["
        for pattern in "${EXCLUDE_PATTERNS[@]}"; do
            echo "  \"$pattern\","
        done
        echo "]"
        echo ""
    fi

    # Include include groups if any were used
    if [[ ${#INCLUDE_PATTERNS[@]} -gt 0 ]]; then
        echo "# Include pattern groups used during generation:"
        echo "include_groups = ["
        for group in "${INCLUDE_PATTERNS[@]}"; do
            echo "  ["
            parse_group_patterns "$group"
            for pattern in "${patterns_array[@]}"; do
                echo "    \"$pattern\","
            done
            echo "  ],"
        done
        echo "]"
        echo ""
    fi

    echo "# List of files to download:"
    echo "files = ["
    echo "$FILES" | while IFS= read -r file; do
        if [[ -n "$file" ]]; then

            echo "  \"$file\","
        fi
    done
    echo "]"
} > "$OUTPUT_PATH"

log "Generated $OUTPUT_PATH"

# Generate README if requested
if [[ "$GEN_README" == true ]]; then
    log "Generating README.md for $OUTPUT_PATH"
    if ./gen-readme.sh "$OUTPUT_PATH" 2>/dev/null; then
        log "README.md generated successfully"
    else
        log "Warning: Failed to generate README.md"
    fi
fi
