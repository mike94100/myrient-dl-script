#!/usr/bin/env bash

# Utility functions for TOML parsing
# This script provides common TOML parsing functionality used by multiple scripts

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
