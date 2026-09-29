#!/usr/bin/env python3
"""Deterministic generator for the 'unit-eval' challenge.

Ships a systemd unit bundle for a periodic "report" job:

  * ``etc/systemd/system/report@.service`` - a *template* unit whose ExecStart
    passes the instance name ``%i`` straight into a shell script.
  * ``etc/systemd/system/report.timer``    - a timer that fires the specific
    instance ``report@main.service`` (so the enabled instance is ``main``).
  * ``usr/local/bin/genreport.sh``          - the script. It sources a config and
    builds a label with ``eval`` (the injectable spot), then emits a report
    token to the journal.
  * ``etc/report/report.conf``              - config with an *obviously fake*
    ``SITE_ID`` and ``BUILD_KEY``.

The token the job prints is a pure function of the shipped inputs::

    label = "report-<instance>-<SITE_ID>"          # instance = main
    token = sha256(label + BUILD_KEY).hexdigest()[:16]
    flag  = "NCTF{systemd_eval_" + token + "}"

so the challenge is to reconstruct that journal line offline. The flag is never
written to any artifact; it is computed from the config + unit wiring.
"""

import hashlib
import os

SITE_ID = "kekeli-prod-07"
BUILD_KEY = "dev-build-key-not-secret"  # obviously-fake dev value
INSTANCE = "main"  # the timer enables report@main.service

REPORT_CONF = f"""\
# /etc/report/report.conf  -- sourced by genreport.sh
# Placeholder dev values. Real deploy injects these from Vault (it doesn't).
SITE_ID={SITE_ID}
BUILD_KEY={BUILD_KEY}
"""

SERVICE = """\
[Unit]
Description=Kekeli periodic report generator (instance %i)

[Service]
Type=oneshot
# BAD: the instance name %i is passed unquoted to a script that eval's it.
ExecStart=/usr/local/bin/genreport.sh %i
"""

TIMER = """\
[Unit]
Description=Run the kekeli report job hourly

[Timer]
OnCalendar=hourly
Unit=report@main.service

[Install]
WantedBy=timers.target
"""

GENREPORT = """\
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
"""


def compute_flag() -> str:
    label = f"report-{INSTANCE}-{SITE_ID}"
    token = hashlib.sha256((label + BUILD_KEY).encode()).hexdigest()[:16]
    return "NCTF{systemd_eval_" + token + "}"


def main() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.normpath(os.path.join(here, ".."))

    sysd = os.path.join(root, "etc", "systemd", "system")
    os.makedirs(sysd, exist_ok=True)
    os.makedirs(os.path.join(root, "usr", "local", "bin"), exist_ok=True)
    os.makedirs(os.path.join(root, "etc", "report"), exist_ok=True)

    with open(os.path.join(sysd, "report@.service"), "w", encoding="utf-8") as fh:
        fh.write(SERVICE)
    with open(os.path.join(sysd, "report.timer"), "w", encoding="utf-8") as fh:
        fh.write(TIMER)
    script_path = os.path.join(root, "usr", "local", "bin", "genreport.sh")
    with open(script_path, "w", encoding="utf-8") as fh:
        fh.write(GENREPORT)
    os.chmod(script_path, 0o755)
    with open(
        os.path.join(root, "etc", "report", "report.conf"), "w", encoding="utf-8"
    ) as fh:
        fh.write(REPORT_CONF)

    print("wrote unit bundle under", root)
    print("flag:", compute_flag())


if __name__ == "__main__":
    main()
