#!/bin/sh
# /usr/local/bin/genreport.sh <instance>
# Emits a signed report token to the journal.
set -eu

. /etc/report/report.conf

region="$1"

# BAD: 'region' comes from the systemd instance name (%i) and is fed to eval.
# For the enabled instance (main) it simply expands to a fixed label, but any
# attacker-controlled instance name would be evaluated as shell here.
eval "label=report-$region-$SITE_ID"

token=$(printf '%s' "$label$BUILD_KEY" | sha256sum | cut -c1-16)
echo "NCTF{systemd_eval_${token}}"
