#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ffmpeg -hide_banner -loglevel error -y \
    -i "$ROOT/output/pick_and_place_demo_intermediate.mp4" \
    -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p \
    -movflags +faststart -an \
    "$ROOT/output/PAI_pick_and_place_demo.mp4"
