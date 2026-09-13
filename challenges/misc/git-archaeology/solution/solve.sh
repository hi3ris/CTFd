#!/usr/bin/env bash
#
# Automated solver for misc/git-archaeology.
# Usage: ./solve.sh [path-to-logparse-cli.tar.gz]
#
# Strategy: the leaked commit is unreachable from any branch but survives as a
# dangling object. Recover it via reflog (or `git fsck --lost-found`), then read
# the scrubbed config.ini out of that commit's tree.
set -euo pipefail

TARBALL="${1:-$(dirname "$0")/../logparse-cli.tar.gz}"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

tar xzf "$TARBALL" -C "$WORK"
cd "$WORK/logparse-cli"

# 1) Find the dangling commit. Two independent ways:
#    (a) reflog remembers the reset:
DANGLE="$(git rev-parse HEAD~0 >/dev/null 2>&1 && \
          git log -g --grep='temp: real token' --format='%H' | head -1 || true)"
#    (b) fallback: fsck lists dangling commits directly.
if [ -z "${DANGLE:-}" ]; then
  DANGLE="$(git fsck --no-reflogs 2>/dev/null | awk '/dangling commit/{print $3; exit}')"
fi

if [ -z "${DANGLE:-}" ]; then
  echo "could not locate dangling commit" >&2
  exit 1
fi
echo "[*] recovered dangling commit: $DANGLE" >&2

# 2) Read the scrubbed credentials file from that commit and extract the flag.
FLAG="$(git show "$DANGLE:config.ini" | grep -oE 'NCTF\{[^}]+\}' | head -1)"
echo "$FLAG"
