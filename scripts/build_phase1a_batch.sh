#!/usr/bin/env bash
set -euo pipefail

build_dir="${1:-build/phase1a-batch}"
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cmake -S "$root/cpp/ltm" -B "$root/$build_dir" -G Ninja
cmake --build "$root/$build_dir" --config Release --target phase1a_batch

echo "Phase1a batch build: $root/$build_dir"
