#!/usr/bin/env python3
"""Reference solver for 'unit-eval'.

Trace the systemd wiring and reproduce the journal line the report job prints:

  1. ``report.timer`` fires ``Unit=report@main.service`` -> instance = "main".
  2. ``report@.service`` runs ``genreport.sh %i`` -> arg = "main".
  3. ``genreport.sh`` sources ``etc/report/report.conf`` for ``SITE_ID`` /
     ``BUILD_KEY``, builds ``label = report-<instance>-<SITE_ID>`` and prints
     ``NCTF{systemd_eval_<sha256(label+BUILD_KEY)[:16]>}``.

We parse the config values from the shipped files and recompute that hex.
Pure standard library.
"""

import hashlib
import os
import re


def read_conf(path: str) -> dict:
    out = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip()
    return out


def instance_from_timer(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    m = re.search(r"Unit=report@([^.\s]+)\.service", text)
    if not m:
        raise SystemExit("could not find enabled instance in report.timer")
    return m.group(1)


def solve(root: str) -> str:
    conf = read_conf(os.path.join(root, "etc", "report", "report.conf"))
    site_id = conf["SITE_ID"]
    build_key = conf["BUILD_KEY"]
    instance = instance_from_timer(
        os.path.join(root, "etc", "systemd", "system", "report.timer")
    )
    print(f"[+] enabled instance: {instance}")
    print(f"[+] SITE_ID={site_id}  BUILD_KEY={build_key}")

    label = f"report-{instance}-{site_id}"
    token = hashlib.sha256((label + build_key).encode()).hexdigest()[:16]
    flag = "NCTF{systemd_eval_" + token + "}"
    print("[+] FLAG =", flag)
    return flag


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    solve(os.path.normpath(os.path.join(here, "..")))
