#!/usr/bin/env bash
#
# build_repo.sh - deterministically construct the challenge git repository
# and package it as a tarball for players.
#
# The scenario: a developer accidentally committed a production credentials
# file, noticed, and "removed" it with `git reset --hard`. The bad commit is
# no longer reachable from any branch or tag, but it survives as a DANGLING
# commit (and its blob) inside .git/objects, and is referenced by the reflog.
#
# We intentionally DO NOT run `git gc` / `git prune`, so the dangling objects
# remain recoverable. This script is idempotent: it rebuilds from scratch.
#
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK="$(mktemp -d)"
REPO="$WORK/logparse-cli"
OUT="$HERE/logparse-cli.tar.gz"

# --- deterministic identity / dates so the tarball is reproducible ---------
export GIT_AUTHOR_NAME="Priya Raman"
export GIT_AUTHOR_EMAIL="priya@logparse.dev"
export GIT_COMMITTER_NAME="Priya Raman"
export GIT_COMMITTER_EMAIL="priya@logparse.dev"
D0="2024-02-03T09:14:00 +0000"
D1="2024-02-06T11:42:00 +0000"
D2="2024-02-09T15:03:00 +0000"   # the accidental secret commit
D3="2024-02-09T15:07:00 +0000"   # the "fix"
D4="2024-02-12T10:20:00 +0000"

FLAG='CTF{d4ngling_c0mmit_lives_in_ref10g}'

commit() {  # commit <date> <message>
  GIT_AUTHOR_DATE="$1" GIT_COMMITTER_DATE="$1" git commit -q -m "$2"
}

rm -rf "$REPO"
mkdir -p "$REPO"
cd "$REPO"
git init -q -b main
git config core.autocrlf false

# --- C0: initial project ---------------------------------------------------
cat > README.md <<'EOF'
# logparse-cli

A tiny CLI for slicing web-server access logs.

    ./logparse.py access.log --top 10

## Config

Runtime settings live in `config.ini`. Do not commit real credentials -
use `config.ini.example` as a template and keep the real file out of git.
EOF

cat > logparse.py <<'EOF'
#!/usr/bin/env python3
"""logparse - summarise access logs. (toy project)"""
import sys
import collections

def top_ips(path, n):
    counts = collections.Counter()
    with open(path) as fh:
        for line in fh:
            counts[line.split(" ", 1)[0]] += 1
    return counts.most_common(n)

if __name__ == "__main__":
    log = sys.argv[1]
    n = 10
    if "--top" in sys.argv:
        n = int(sys.argv[sys.argv.index("--top") + 1])
    for ip, c in top_ips(log, n):
        print(f"{c:>8}  {ip}")
EOF
chmod +x logparse.py

cat > config.ini.example <<'EOF'
[analytics]
# Fill in your own token; never commit the real one.
upload_token = REPLACE_ME
endpoint = https://ingest.example.internal/v1
EOF

cat > .gitignore <<'EOF'
*.pyc
__pycache__/
# config.ini is added later in history on purpose (that is the bug)
EOF

git add -A
commit "$D0" "Initial import: logparse CLI + example config"

# --- C1: a normal feature commit ------------------------------------------
cat >> logparse.py <<'EOF'

def status_breakdown(path):
    counts = collections.Counter()
    with open(path) as fh:
        for line in fh:
            parts = line.split()
            if len(parts) > 8:
                counts[parts[8]] += 1
    return counts
EOF
git add -A
commit "$D1" "Add HTTP status-code breakdown helper"

# --- C_bad: the accidental secret commit (will become dangling) -----------
# NB: .gitignore ignores config.ini, so the dev force-added it.
cat > config.ini <<EOF
[analytics]
# Production ingest credentials - DO NOT SHARE
upload_token = ${FLAG}
endpoint = https://ingest.logparse.dev/v1
EOF
git add -f config.ini
commit "$D2" "wire up analytics upload (temp: real token, will scrub)"

BAD_COMMIT="$(git rev-parse HEAD)"

# --- "remove" the secret by resetting the branch back one commit -----------
# This is the classic mistake: the working file is deleted and the branch
# pointer moves, but the object is still in .git and the reflog remembers it.
git reset --hard -q HEAD~1
rm -f config.ini   # scrub it from the working tree too

# --- C2: redo the feature the RIGHT way, without the secret ----------------
cat > config.ini.example <<'EOF'
[analytics]
# Fill in your own token; never commit the real one.
upload_token = REPLACE_ME
endpoint = https://ingest.example.internal/v1

[upload]
enabled = false
EOF
cat >> logparse.py <<'EOF'

def load_token():
    import configparser, os
    cfg = configparser.ConfigParser()
    cfg.read(os.environ.get("LOGPARSE_CONFIG", "config.ini"))
    return cfg.get("analytics", "upload_token", fallback=None)
EOF
git add -A
commit "$D3" "Add analytics upload (token loaded from local config, not committed)"

# --- C3: a DECOY. An old note file with a fake, obviously-bogus token. -----
# This is reachable from history via `git log -p` and looks tempting, but the
# value is plainly a placeholder and refutable in seconds.
cat > NOTES.txt <<'EOF'
TODO / scratch notes
--------------------
- staging token was rotated last week
- old placeholder we used in the demo video: CTF{example_token_not_the_real_flag}
  (this is a fake sample value, safe to keep in the repo)
- remember to add rate-limiting to the uploader
EOF
git add -A
commit "$D4" "Add scratch NOTES.txt"

# --- sanity: make sure the bad commit is dangling but still present --------
if git merge-base --is-ancestor "$BAD_COMMIT" HEAD 2>/dev/null; then
  echo "ERROR: secret commit is still reachable from HEAD!" >&2
  exit 1
fi
if ! git cat-file -e "$BAD_COMMIT" 2>/dev/null; then
  echo "ERROR: secret commit object is missing (was it gc'd)?" >&2
  exit 1
fi

# Do NOT gc/prune - that would destroy the challenge.
# Package the whole repo, .git included.
cd "$WORK"
tar --sort=name --owner=0 --group=0 --numeric-owner \
    --mtime='2024-02-12T10:20:00Z' \
    -czf "$OUT" logparse-cli

echo "Built $OUT"
echo "  dangling secret commit: $BAD_COMMIT"
echo "  flag: $FLAG"
rm -rf "$WORK"
