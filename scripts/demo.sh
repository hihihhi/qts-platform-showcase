#!/usr/bin/env bash
# The reading demo. Standard library only; runs in seconds. The platform's source is closed, so
# there is nothing of it to execute. This prints the headline numbers from docs/results.md, then
# recomputes every computed figure there (totals, the 700B+ sum and its duplicate shares, the
# duplicate rate, the read count) from the page's raw counts, and exits 1 if the page states any of
# them differently. The runnable stand-in, on SYNTHETIC data, is the separate repository
# qts-platform-demo.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 scripts/figures.py
