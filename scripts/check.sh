#!/usr/bin/env bash
# The repository's full check; exit 0 only if every part passes:
#   1. the document checks: links, anchors, code and mermaid fences, the README's headline table
#      and figures against docs/results.md, the arithmetic behind results.md's computed figures,
#      and the forbidden-terms scan (scripts/check_docs.py). Set FORBIDDEN_TERMS_FILE to a private
#      pattern file outside the repository to scan for more terms;
#   2. the same checks' self-test: each must go red on a planted defect and stay green on the
#      untouched copy, so a check that has silently stopped working fails here;
#   3. the reading demo.
# The runnable stand-in lives in its own repository, qts-platform-demo, with its own checks.
# Standard library only.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 scripts/check_docs.py
python3 scripts/check_docs.py --self-test
bash scripts/demo.sh >/dev/null
echo "PASS  demo"
