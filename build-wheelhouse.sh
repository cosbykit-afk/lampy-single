#!/bin/bash
# Rebuild the Lampy offline wheelhouse from PyPI.
#
# The Docker build uses a pre-downloaded wheelhouse so the image can be
# built without internet access at build time. This script re-creates that
# wheelhouse from the pinned package list.
#
# Usage: ./build-wheelhouse.sh [output-dir]
#   output-dir defaults to ./wheelhouse
#
# Requirements: Python 3.10, pip, internet access.
# Target platform: Linux x86_64 (matches the Docker build).

set -euo pipefail

OUT="${1:-wheelhouse}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Building wheelhouse in $OUT ..."
mkdir -p "$OUT"

pip download \
  --dest "$OUT" \
  --python-version 310 \
  --platform manylinux2014_x86_64 \
  --platform manylinux_2_17_x86_64 \
  --platform manylinux_2_28_x86_64 \
  --platform linux_x86_64 \
  --abi cp310 \
  --abi abi3 \
  --abi none \
  --only-binary=:all: \
  -r "$SCRIPT_DIR/wheelhouse-packages.txt"

COUNT=$(ls "$OUT"/*.whl 2>/dev/null | wc -l)
echo "Done: $COUNT wheels in $OUT"
