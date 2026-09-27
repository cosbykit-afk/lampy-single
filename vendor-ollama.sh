#!/bin/bash
# Re-vendor the Ollama binaries used by the Lampy Dockerfile.
#
# The Dockerfile COPYs from ollama-donor/ (not from the network), so the
# binaries must be extracted first. This script re-extracts them
# byte-identical from the pinned Ollama image digest.
#
# Usage: ./vendor-ollama.sh [output-dir]
#   output-dir defaults to ./ollama-donor
#
# Requirements: docker, internet access to Docker Hub.

set -euo pipefail

OUT="${1:-ollama-donor}"
# Pinned source — must match the comment in the Dockerfile.
OLLAMA_IMAGE="ollama/ollama:latest@sha256:da6e0dc5651df159e45686fd663c4dbe1624a52c44d7280eeac1551d8f865532"

echo "Pulling $OLLAMA_IMAGE ..."
docker pull "$OLLAMA_IMAGE"

CID=$(docker create "$OLLAMA_IMAGE")
trap 'docker rm "$CID" >/dev/null' EXIT

echo "Extracting binaries to $OUT ..."
mkdir -p "$OUT/usr/bin" "$OUT/usr/lib" "$OUT/usr/share"
docker cp "$CID:/usr/bin/ollama" "$OUT/usr/bin/ollama"
docker cp "$CID:/usr/lib/ollama" "$OUT/usr/lib/ollama"
docker cp "$CID:/usr/share/ollama" "$OUT/usr/share/ollama" 2>/dev/null || true

echo "Done:"
du -sh "$OUT"
find "$OUT" -type f | wc -l | xargs echo "files:"
