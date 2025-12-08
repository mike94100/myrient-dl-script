#!/usr/bin/env bash
set -euo pipefail

# Source utility functions
. ./scripts/toml-utils.sh
. ./scripts/url-utils.sh
. ./scripts/progress.sh
. ./scripts/log.sh

# Read each platform toml
process_platform_toml() {
    local file="$1"

    log "Processing site: $file"

    json=$(parse_toml "$file")

    path_directory=$(validate_directory_path "$(printf "%s" "$json" | jq -r '.path_directory // empty')")
    if [[ $? -ne 0 ]]; then
        log "ERROR: Invalid directory path in $file"
        exit 1
    fi

    directory=$(printf "%s" "$json" | jq -r '.directory // empty')
    if [[ -z "$directory" ]]; then
        directory=""
    fi

    full_dir="${ROOT_DIRECTORY}${directory}"

    mapfile -t files < <(printf "%s" "$json" | jq -r '.files[]')

    if [[ "${#files[@]}" -eq 0 ]]; then
        log "ERROR: files[] missing or empty in $file"
        exit 1
    fi

    if [[ "$DRY_RUN" != true ]]; then
        # Create output directory
        mkdir -p "$full_dir"
        log "Create directory: $full_dir"

        # Generate encoded urls
        for i in "${!files[@]}"; do
            files[$i]="${SITE}$(url_encode "${path_directory}${files[$i]}")"
        done

        # Download files
        printf '%s\n' "${files[@]}" | wget --progress=bar -i - -P "$full_dir" -np -c -e robots=off -R "index.html*"

    else
        log "DRYRUN: Create directory: $full_dir"
        log "DRYRUN: Download ${#files[@]} files"
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

    # Load config
    if [[ ! -f "./config.toml" ]]; then
        log "ERROR: config.toml not found in current directory"
        exit 1
    fi

    CONFIG_TOML=$(parse_toml "./config.toml")

    SITE=$(printf "%s" "$CONFIG_TOML" | jq -r '.site')
    if [[ -z "$SITE" ]]; then
        log "ERROR: site is missing in config.toml"
        exit 1
    fi

    ROOT_DIRECTORY=$(printf "%s" "$CONFIG_TOML" | jq -r '.root_directory // empty')
    if [[ -z "$ROOT_DIRECTORY" ]]; then
        ROOT_DIRECTORY="./roms/"
    fi

    # Apply output directory override
    if [[ -n "$output_dir" ]]; then
        # Remove leading ./ from base_directory if present
        base_dir="${ROOT_DIRECTORY#./}"
        ROOT_DIRECTORY="${output_dir%/}/${base_dir}"
    fi

    DRY_RUN=$dry_run

    log "SITE URL: $SITE"
    log "Root directory: $ROOT_DIRECTORY"
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
