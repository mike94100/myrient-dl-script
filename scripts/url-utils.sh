#!/bin/bash

# Source utility functions
. ./scripts/log.sh

url_decode() {
    jq -nr --arg url "$1" '$url | @urid'
}

url_encode() {
    # Encode with jq but preserve forward slashes (path separators)
    jq -nr --arg url "$1" '$url | @uri' | sed 's/%2F/\//g'
}

# Validate and format directory path
# Ensures it's not a host/hostname/file and formats as "/path/"
validate_directory_path() {
    local path="$1"

    # Check if empty
    if [[ -z "$path" ]]; then
        error "Directory path missing"
        return 1
    fi

    # Check if it looks like a URL or hostname
    if [[ "$path" =~ :// ]] || [[ "$path" =~ ^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,} ]]; then
        error "Directory path cannot be a host or URL: $path"
        return 1
    fi

    # Check if file (has an extension)
    if [[ "$path" =~ \.[a-zA-Z0-9]+$ ]]; then
        error "Directory path cannot be a file: $path"
        return 1
    fi

    # Ensure path starts and ends with slash "/path/"
    if [[ "$path" != /* ]]; then path="/$path"; fi
    if [[ "$path" != */ ]]; then path="$path/"; fi

    echo "$path"
}
