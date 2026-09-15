#!/usr/bin/env python3
"""Phantom Wire -- operator "nightly report" generator.

Intended to be run as root by the operator via the sudo rule:

    deploy ALL=(root) NOPASSWD: /usr/bin/python3 /opt/phantom/report.py

It pulls a summary from the `phantomlib` helper. Because the script is executed
by absolute path, Python puts the script's OWN directory (/opt/phantom) at the
front of sys.path -- so `import phantomlib` is resolved from /opt/phantom. That
directory is group-writable by `deploy` (stage-3 misconfig), so a `deploy` user
can drop a `phantomlib.py` there whose module-level code runs as ROOT the next
time this script is sudo-executed. Classic writable-script-directory /
library-hijack privesc.

The helper is intentionally NOT shipped: the operator's "report" only ever runs
by hand under sudo, and the missing import is exactly the hole.
"""
import phantomlib  # noqa: F401 - resolved from /opt/phantom (hijackable)


def main():
    print("[report] phantom wire nightly summary:", phantomlib.summary())


if __name__ == "__main__":
    main()
