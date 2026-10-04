#!/usr/bin/env bash
# The demo, in two parts. Standard library only; runs in seconds.
#   1. The reading demo. The platform's source is closed, so there is nothing of it to execute.
#      This prints the headline numbers from docs/results.md, then recomputes every computed figure
#      there (totals, the 700B+ sum and its duplicate shares, the duplicate rate, the read count) from the page's raw
#      counts, and exits 1 if the page states any of them differently.
#   2. The stand-in (demo/minilake): an independent demonstration system, written only from this
#      write-up; not the platform's code.
#      It builds every layer on SYNTHETIC data, prints what each layer did, and exits 1 unless
#      every gate passes.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 scripts/figures.py
echo
cd demo && python3 -m minilake
