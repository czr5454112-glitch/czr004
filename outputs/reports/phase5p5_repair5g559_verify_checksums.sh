#!/usr/bin/env bash
set -euo pipefail
cd "${CZR004_ROOT:-/root/czr004}"
sha256sum -c outputs/tables/phase5p5_repair5g559_checksums.sha256
