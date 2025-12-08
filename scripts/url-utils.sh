#!/bin/bash
# URL encoding/decoding utility functions

# URL decode using Python
url_decode() {
    python3 -c "import sys, urllib.parse; print(urllib.parse.unquote(sys.argv[1]))" "$1"
}

# URL encode using Python
url_encode() {
    python3 -c "import sys, urllib.parse; print(urllib.parse.quote(sys.argv[1]))" "$1"
}

# Validate and format directory path
# Ensures it's not a host/hostname/file and formats as "/path/"
validate_directory_path() {
    local path="$1"

    # Check if empty
    if [[ -z "$path" ]]; then
        echo "ERROR: directory path missing" >&2
        return 1
    fi

    # Check if it looks like a URL or hostname
    if [[ "$path" =~ :// ]] || [[ "$path" =~ ^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,} ]]; then
        echo "ERROR: directory path cannot be a host or URL: $path" >&2
        return 1
    fi

    # Check if it looks like a file (has an extension)
    if [[ "$path" =~ \.[a-zA-Z0-9]+$ ]]; then
        echo "ERROR: directory path cannot be a file: $path" >&2
        return 1
    fi

    # Ensure it starts with slash
    if [[ "$path" != /* ]]; then
        path="/$path"
    fi

    # Ensure it ends with slash
    if [[ "$path" != */ ]]; then
        path="$path/"
    fi

    echo "$path"
}
