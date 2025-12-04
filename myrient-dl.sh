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

# Read each config
process_site_file() {
    local file="$1"

    log "Processing site: $file"

    json=$(parse_toml "$file")

    subdomain=$(printf "%s" "$json" | jq -r '.subdomain // empty')
    if [[ -z "$subdomain" ]]; then
        log "ERROR: subdomain missing in $file"
        exit 1
    fi

    mapfile -t files < <(printf "%s" "$json" | jq -r '.files[]')

    if [[ "${#files[@]}" -eq 0 ]]; then
        log "ERROR: files[] missing or empty in $file"
        exit 1
    fi

    for f in "${files[@]}"; do
        if [[ "$f" != *"%"* ]]; then
            log "WARNING: File entry '$f' does not contain '%', may be unencoded."
        fi

        full_url="${GLOBAL_BASE}${subdomain}${f}"
        URLS+=("$full_url")

        log "Prepared URL: $full_url"
    done
}

# Main
main() {
    : > "$LOG_FILE"

    # Load global config
    GLOBAL_TOML=$(parse_toml "./config.toml")

    GLOBAL_BASE=$(printf "%s" "$GLOBAL_TOML" | jq -r '.base_url')
    if [[ -z "$GLOBAL_BASE" ]]; then
        log "ERROR: base_url missing in global.toml"
        exit 1
    fi

    log "Global base URL: $GLOBAL_BASE"

    # Prepare URLs
    URLS=()
    for file in config/sites/*.toml; do
        process_site_file "$file"
    done

    log "Total files to download: ${#URLS[@]}"

    # Download
    for url in "${URLS[@]}"; do
        log "Downloading: $url"
        wget -m -np -c -e robots=off -R "index.html*" "$url" \
            >> "$LOG_FILE" 2>&1 || {
                log "ERROR downloading $url"
            }
    done

    log "Downloads complete."
}

main
