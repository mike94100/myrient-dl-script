#!/usr/bin/env bash
set -euo pipefail

# Build the Docker image and run the build for the Tauri Rust backend.
# Artifacts will be inside the image; to extract the built artifacts, run the image and copy them out,
# or mount a host directory to /work/target for incremental builds.

IMAGE_NAME="roms-as-code-tauri-builder"
DOCKERFILE="docker/tauri-builder/Dockerfile"

echo "Building Docker image ${IMAGE_NAME}..."
docker build --no-cache -f "${DOCKERFILE}" -t "${IMAGE_NAME}" ..

echo "To run an interactive container with the built artifacts mounted to ./target-host, run:"
echo "  mkdir -p target-host && docker run --rm -it -v $(pwd)/target-host:/work/src-tauri/target ${IMAGE_NAME}"

echo "Or to inspect the image: docker run --rm -it ${IMAGE_NAME}"
