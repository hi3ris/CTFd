#!/usr/bin/env python3
"""Reference solver for auth-timeline.

    python3 solve.py ../auth.log

1. Count ``Failed password`` per source IP; the brute-force IP dominates.
2. Find that IP's ``Accepted password`` line and grab the sshd PID.
3. Find the ``audit[<pid>]`` line for that PID and pull the base64 ``cmd`` blob.
4. base64-decode it -> the flag.
"""
import base64
import re
import sys
from collections import Counter


def main(path: str) -> None:
    lines = open(path).read().splitlines()

    fails = Counter()
    fail_re = re.compile(r"Failed password for .* from (\d+\.\d+\.\d+\.\d+) ")
    for line in lines:
        m = fail_re.search(line)
        if m:
            fails[m.group(1)] += 1
    atk_ip = fails.most_common(1)[0][0]

    acc_re = re.compile(
        r"sshd\[(\d+)\]: Accepted password for root from " + re.escape(atk_ip)
    )
    atk_pid = None
    for line in lines:
        m = acc_re.search(line)
        if m:
            atk_pid = m.group(1)
            break

    audit_re = re.compile(
        r"audit\[" + atk_pid + r"\]:.*echo ([A-Za-z0-9+/=]+) \| base64"
    )
    blob = None
    for line in lines:
        m = audit_re.search(line)
        if m:
            blob = m.group(1)
            break

    decoded = base64.b64decode(blob).decode()
    flag = decoded.split("=", 1)[1] if decoded.startswith("flag=") else decoded
    print(flag)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "../auth.log")
