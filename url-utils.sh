#!/bin/bash
# URL encoding/decoding utility functions

# URL decode using Python
url_decode() {
    python3 -c "import sys, urllib.parse; print(urllib.parse.unquote(sys.argv[1]))" "$1"
}

# URL encode using Python (handles both encoded and decoded input by decoding first)
url_encode() {
    local decoded=$(url_decode "$1")
    python3 -c "import sys, urllib.parse; print(urllib.parse.quote('$decoded'))"
}
