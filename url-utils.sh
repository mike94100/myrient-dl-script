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
