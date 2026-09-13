#!/usr/bin/env python3
"""
Reference solver for forensics/evasion-timeline.

    python3 solve.py ../sysmon.jsonl

Approach (pure timeline correlation -- no signature matching on process names):

  1. Parse the newline-delimited Sysmon events.
  2. Index every Process-Create (EventID 1) by ProcessGuid, and record the
     earliest Process-Terminate (EventID 5) time per ProcessGuid.
  3. For every child Process-Create that names a ParentProcessGuid we actually
     saw created in this capture, check the parent was ALIVE when the child was
     born:
         parent.create_time <= child.create_time  AND
         (parent has no terminate, OR child.create_time <= parent.terminate_time)
     Exactly one event violates this: the child is created ~28 s AFTER its
     claimed parent already terminated. A dead process cannot spawn a child ->
     the recorded ancestry is forged (PPID spoofing, MITRE T1134.004).
  4. The malicious process's CommandLine carries a PowerShell -EncodedCommand
     (base64 of UTF-16LE). Decode it and read the flag.

The decoy PowerShell downloader (which also contains an NCTF{...}-shaped token)
is NOT flagged: its parent (explorer.exe) is still alive, so its ancestry is
sound. The real flag is only on the event with the impossible parentage.
"""
import base64
import json
import re
import sys
from datetime import datetime


def parse_time(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d %H:%M:%S.%f")


def decode_encoded_commands(cmdline: str):
    """Yield decoded strings for each -enc / -EncodedCommand base64 blob."""
    for m in re.finditer(r"-(?:enc|encodedcommand)\s+([A-Za-z0-9+/=]{8,})",
                         cmdline, re.IGNORECASE):
        blob = m.group(1)
        try:
            raw = base64.b64decode(blob)
        except Exception:
            continue
        # PowerShell -EncodedCommand is UTF-16LE
        yield raw.decode("utf-16-le", errors="replace")


def main(path):
    creates = {}      # guid -> event
    terminated = {}   # guid -> earliest terminate datetime
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            ev = json.loads(line)
            eid = ev.get("EventID")
            if eid == 1:
                creates[ev["ProcessGuid"]] = ev
            elif eid == 5:
                t = parse_time(ev["UtcTime"])
                g = ev["ProcessGuid"]
                if g not in terminated or t < terminated[g]:
                    terminated[g] = t

    print(f"[*] {len(creates)} process-create events, "
          f"{len(terminated)} distinct terminations")

    anomalies = []
    for guid, child in creates.items():
        pguid = child.get("ParentProcessGuid")
        parent = creates.get(pguid)
        if not parent:
            continue  # root / parent outside the capture window -> can't judge
        c_time = parse_time(child["UtcTime"])
        p_time = parse_time(parent["UtcTime"])
        p_end = terminated.get(pguid)
        # parent must exist before the child and still be alive at child birth
        if p_time > c_time:
            anomalies.append(("parent-created-after-child", child, parent, None))
        elif p_end is not None and c_time > p_end:
            anomalies.append(("parent-already-terminated", child, parent, p_end))

    print(f"[*] impossible-ancestry events found: {len(anomalies)}")
    if len(anomalies) != 1:
        sys.exit(f"[!] expected exactly one anomaly, got {len(anomalies)}")

    reason, child, parent, p_end = anomalies[0]
    c_time = parse_time(child["UtcTime"])
    print("\n[+] Defense-evasion IOC (forged parent / PPID spoof):")
    print(f"      reason           : {reason}")
    print(f"      malicious Image  : {child['Image']}")
    print(f"      malicious PID    : {child['ProcessId']}  "
          f"guid {child['ProcessGuid']}")
    print(f"      created          : {child['UtcTime']}")
    print(f"      claimed parent   : PID {child['ParentProcessId']} "
          f"({child['ParentImage']}) guid {child['ParentProcessGuid']}")
    print(f"      parent created   : {parent['UtcTime']}")
    print(f"      parent TERMINATED: {p_end}  "
          f"({(c_time - p_end).total_seconds():.0f}s before the child)")

    flag = None
    for decoded in decode_encoded_commands(child["CommandLine"]):
        print(f"\n[*] decoded -EncodedCommand:\n      {decoded}")
        m = re.search(r"NCTF\{[^}]+\}", decoded)
        if m:
            flag = m.group(0)

    print("\n[+] FLAG:", flag if flag else "<not found>")
    return flag


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "../sysmon.jsonl")
