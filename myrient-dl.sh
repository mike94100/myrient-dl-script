#!/usr/bin/env bash
set -euo pipefail

LOG_FILE="myrient-dl.log"

log() {
    printf "[%s] %s\n" "$(date '+%Y-%m-%d %H:%M:%S')" "$*" | tee -a "$LOG_FILE"
}

# Parse TOML using Python
parse_toml() {
python3 - "$1" <<'EOF'
import sys, json

try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # fallback for older Python

with open(sys.argv[1], "rb") as f:
    data = tomllib.load(f)

print(json.dumps(data))
EOF
}

# URL decode using Python
url_decode() {
python3 -c "import sys, urllib.parse; print(urllib.parse.unquote(sys.argv[1]))" "$1"
}

# Get human-readable filename from URL
get_filename() {
    local url="$1"
    local filename="${url##*/}"
    url_decode "$filename"
}

# Read each platform toml
process_platform_toml() {
    local file="$1"

    log "Processing site: $file"

    json=$(parse_toml "$file")

    subdomain=$(printf "%s" "$json" | jq -r '.subdomain // empty')
    if [[ -z "$subdomain" ]]; then
        log "ERROR: subdomain missing in $file"
        exit 1
    fi

    directory=$(printf "%s" "$json" | jq -r '.directory // empty')
    if [[ -z "$directory" ]]; then
        directory=""
    fi

    full_dir="${GLOBAL_BASE_DIRECTORY}${directory}"

    mapfile -t files < <(printf "%s" "$json" | jq -r '.files[]')

    if [[ "${#files[@]}" -eq 0 ]]; then
        log "ERROR: files[] missing or empty in $file"
        exit 1
    fi

    local URLS=()
    for f in "${files[@]}"; do
        if [[ "$f" =~ [[:space:]\(\)\[\]\{\}\|\\\^\~\'\"\<\>\#] ]]; then
            log "WARNING: File entry '$f' contains characters that may need URL encoding."
        fi

        full_url="${GLOBAL_BASE}${subdomain}${f}"
        URLS+=("$full_url")

        log "Prepared URL: $full_url -> $full_dir"
    done

    log "Total files for $file: ${#URLS[@]}"

    if [[ "$DRY_RUN" != true ]]; then
        # Download for this site
        mkdir -p "$full_dir"
        log "Create directory: $full_dir"
        for url in "${URLS[@]}"; do
            filename=$(get_filename "$url")
            log "Downloading: $filename"
            wget -P "$full_dir" -nd -c -e robots=off -R "index.html*" "$url" \
                >> "$LOG_FILE" 2>&1 || {
                    log "ERROR downloading $url"
                }
        done
    else
        log "DRYRUN: Create directory: $full_dir"
        for url in "${URLS[@]}"; do
            filename=$(get_filename "$url")
            log "DRYRUN: Downloading: $filename"
        done
    fi
}

# Check if a TOML is a meta config (contains platform_tomls[] array)
is_meta_toml() {
    local file="$1"
    local json=$(parse_toml "$file")
    local platform_tomls=$(printf "%s" "$json" | jq -r '.platform_tomls // empty')
    [[ -n "$platform_tomls" ]]
}

# Process a meta TOML that lists other TOMLs
process_meta_toml() {
    local meta_file="$1"
    local meta_dir=$(dirname "$meta_file")
    
    log "Processing meta TOML: $meta_file"
    
    json=$(parse_toml "$meta_file")
    mapfile -t platform_tomls < <(printf "%s" "$json" | jq -r '.platform_tomls[]')

    if [[ "${#platform_tomls[@]}" -eq 0 ]]; then
        log "ERROR: platform_tomls[] missing or empty in $meta_file"
        exit 1
    fi

    for config in "${platform_tomls[@]}"; do
        # Resolve path relative to meta TOML directory
        local config_path
        if [[ "$config" = /* ]]; then
            # Absolute path
            config_path="$config"
        else
            # Relative path
            config_path="$meta_dir/$config"
        fi
        
        if [[ ! -f "$config_path" ]]; then
            log "ERROR: Config file not found: $config_path"
            exit 1
        fi
        
        process_platform_toml "$config_path"
    done
}

# Show help
show_help() {
    cat << EOF
Usage: myrient-dl.sh [OPTIONS] [TOML_FILES...]

Download ROMs from Myrient based on TOML configuration files.

OPTIONS:
  -i, --input FILES     Input TOML files, space-separated.
  -o, --output DIR      Output directory for downloads.
  -h, --help            Shows this help message.
  --dry-run             Commands are not run, but logged for testing.

ARGUMENTS:
  TOML_FILES             One or more TOML files or meta TOML files.

EXAMPLES:
  myrient-dl.sh -i "testconfigs/gb.toml testconfigs/gbc.toml"
  myrient-dl.sh --dry-run testconfigs/testconfigs.toml
  myrient-dl.sh -o ~/Games testconfigs/gb.toml
  myrient-dl.sh -h

CONFIGURATION:
  - config.toml: Contains base_url and base_directory
  - Meta TOML: Contains platform_tomls array of Platform TOMLs
  - Platform TOML: Contains subdomain, directory, and files array

EOF
}

# Main
main() {
    : > "$LOG_FILE"

    local inputs=()
    local dry_run=false
    local output_dir=""

    # Parse options
    while [[ $# -gt 0 ]]; do
        case $1 in
            -i|--input)
                if [[ -n "$2" ]]; then
                    # Split $2 by spaces into array
                    IFS=' ' read -r -a files <<< "$2"
                    inputs+=("${files[@]}")
                    shift 2
                else
                    log "ERROR: -i/--input requires file arguments"
                    exit 1
                fi
                ;;
            -o|--output)
                if [[ -n "$2" && "$2" != -* ]]; then
                    output_dir="$2"
                    shift 2
                else
                    log "ERROR: -o/--output requires a directory argument"
                    exit 1
                fi
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            --dry-run)
                dry_run=true
                shift
                ;;
            -*)
                show_help
                log "ERROR: Unknown option: $1"
                exit 1
                ;;
            *)
                # Positional arguments for backward compatibility
                inputs+=("$1")
                shift
                ;;
        esac
    done

    # Check for arguments
    if [[ ${#inputs[@]} -eq 0 ]]; then
        log "ERROR: No input files specified"
        log "Use -h or --help for usage"
        exit 1
    fi

    # Load global config
    if [[ ! -f "./config.toml" ]]; then
        log "ERROR: config.toml not found in current directory"
        exit 1
    fi

    GLOBAL_TOML=$(parse_toml "./config.toml")

    GLOBAL_BASE=$(printf "%s" "$GLOBAL_TOML" | jq -r '.base_url')
    if [[ -z "$GLOBAL_BASE" ]]; then
        log "ERROR: base_url missing in config.toml"
        exit 1
    fi

    GLOBAL_BASE_DIRECTORY=$(printf "%s" "$GLOBAL_TOML" | jq -r '.base_directory // empty')
    if [[ -z "$GLOBAL_BASE_DIRECTORY" ]]; then
        GLOBAL_BASE_DIRECTORY="./roms/"
    fi

    # Apply output directory override
    if [[ -n "$output_dir" ]]; then
        # Remove leading ./ from base_directory if present
        base_dir="${GLOBAL_BASE_DIRECTORY#./}"
        GLOBAL_BASE_DIRECTORY="${output_dir%/}/${base_dir}"
    fi

    DRY_RUN=$dry_run

    log "Global base URL: $GLOBAL_BASE"
    log "Global base directory: $GLOBAL_BASE_DIRECTORY"
    if [[ "$DRY_RUN" == true ]]; then
        log "Dry run mode: no downloads will be performed"
    fi

    # Process each input file
    for toml_arg in "${inputs[@]}"; do
        if [[ ! -f "$toml_arg" ]]; then
            log "ERROR: File not found: $toml_arg"
            exit 1
        fi

        # Check if it's a meta TOML or a site TOML
        if is_meta_toml "$toml_arg"; then
            process_meta_toml "$toml_arg"
        else
            process_platform_toml "$toml_arg"
        fi
    done

    if [[ "$DRY_RUN" == true ]]; then
        log "Dry run complete."
    else
        log "All downloads complete."
    fi
}

main "$@"
