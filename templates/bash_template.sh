#!/bin/bash
# Auto-generated download script for {TITLE}
# Generated on {DATE}

set -e

echo "Creating directory: {DIRECTORY}"
mkdir -p "{DIRECTORY}"
cd "{DIRECTORY}"

echo "Downloading {FILE_COUNT} files..."
{FILE_DOWNLOADS}

{E_EXTRACTION}

echo "Download complete!"
echo "Files saved to: {DIRECTORY}"
