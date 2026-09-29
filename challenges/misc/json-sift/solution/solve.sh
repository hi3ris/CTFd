#!/usr/bin/env bash
# Select the records matching both halves of the predicate, order by seq,
# and concatenate their single-character payloads.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
jq -r '[.[] | select(.tag == "delta" and .active == true)]
        | sort_by(.seq) | map(.ch) | join("")' "$here/../telemetry.json"
