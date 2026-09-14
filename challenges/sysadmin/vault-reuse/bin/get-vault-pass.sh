#!/bin/sh
# bin/get-vault-pass.sh
# BAD: derives the vault password from committed, non-secret metadata.
# Anyone with the repo can reproduce this exact string.
set -eu

here=$(dirname "$0")
gv="$here/../group_vars/all.yml"

proj=$(awk '/^project:/ {print $2}' "$gv")
env=$(awk '/^deploy_env:/ {print $2}' "$gv")

printf '%s-%s-vault-v1' "$proj" "$env"
