#!/usr/bin/env python3
"""Generate ``auth.log`` for the auth-timeline challenge.

A Linux ``auth.log`` full of SSH noise. Exactly one source IP shows a
brute-force burst (many ``Failed password`` lines) followed by an
``Accepted password``. The ``sshd`` PID from that acceptance ties to a later
``audit`` line whose ``cmd=`` field carries a base64 blob. Only the blob from
the correct (post-brute-force) session decodes to the flag; the legitimate
sessions carry innocuous decoy blobs.
"""
import base64
import random

FLAG = "NCTF{brut3f0rc3_th3n_succ3ss_0n_r00t}"

random.seed(20240311)

HOST = "web01"
USERS = ["admin", "root", "test", "oracle", "postgres", "git", "deploy", "ubuntu"]
MONTHS = "Mar"


def ts(minute_offset: int) -> str:
    base_min = 31
    total = base_min + minute_offset
    hh = 9 + total // 60
    mm = total % 60
    ss = random.randint(0, 59)
    return f"{MONTHS} 11 {hh:02d}:{mm:02d}:{ss:02d}"


def rand_ip() -> str:
    return f"{random.randint(11, 210)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(2, 250)}"


def main() -> None:
    lines = []
    minute = 0
    used_pids = set()

    def new_pid() -> int:
        while True:
            p = random.randint(1200, 29999)
            if p not in used_pids:
                used_pids.add(p)
                return p

    # ---- scattered benign failures (noise) ----
    for _ in range(40):
        ip = rand_ip()
        user = random.choice(USERS)
        pid = new_pid()
        lines.append(
            (
                minute,
                f"{ts(minute)} {HOST} sshd[{pid}]: Failed password for "
                f"{'invalid user ' if random.random() < 0.5 else ''}{user} "
                f"from {ip} port {random.randint(30000, 60000)} ssh2",
            )
        )
        minute += random.randint(0, 2)

    # ---- three legitimate logins with innocuous audit cmds (decoys) ----
    for user, decoy in [
        ("deploy", "systemctl restart nginx"),
        ("ubuntu", "tail -n 200 /var/log/syslog"),
        ("git", "git pull --ff-only origin main"),
    ]:
        ip = rand_ip()
        pid = new_pid()
        lines.append(
            (
                minute,
                f"{ts(minute)} {HOST} sshd[{pid}]: Accepted publickey for {user} "
                f"from {ip} port {random.randint(30000, 60000)} ssh2",
            )
        )
        minute += 1
        blob = base64.b64encode(decoy.encode()).decode()
        lines.append(
            (
                minute,
                f"{ts(minute)} {HOST} audit[{pid}]: USER_CMD uid=0 "
                f'cmd="echo {blob} | base64 -d"',
            )
        )
        minute += random.randint(1, 3)

    # ---- the attacker: brute-force burst from ONE ip, then success ----
    atk_ip = "203.0.113.45"
    for _ in range(28):
        user = random.choice(["root", "admin", "root", "root"])
        pid = new_pid()
        lines.append(
            (
                minute,
                f"{ts(minute)} {HOST} sshd[{pid}]: Failed password for {user} "
                f"from {atk_ip} port {random.randint(40000, 41000)} ssh2",
            )
        )
        minute += 0  # rapid-fire, same minute cluster
        if random.random() < 0.4:
            minute += 1

    atk_pid = new_pid()
    minute += 1
    lines.append(
        (
            minute,
            f"{ts(minute)} {HOST} sshd[{atk_pid}]: Accepted password for root "
            f"from {atk_ip} port 41200 ssh2",
        )
    )
    minute += 1
    lines.append(
        (
            minute,
            f"{ts(minute)} {HOST} sshd[{atk_pid}]: pam_unix(sshd:session): "
            f"session opened for user root by (uid=0)",
        )
    )
    minute += 1
    flag_blob = base64.b64encode(f"flag={FLAG}".encode()).decode()
    lines.append(
        (
            minute,
            f"{ts(minute)} {HOST} audit[{atk_pid}]: USER_CMD uid=0 "
            f'cmd="echo {flag_blob} | base64 -d > /root/.ok"',
        )
    )

    # ---- more benign failures after the fact (noise tail) ----
    for _ in range(25):
        ip = rand_ip()
        user = random.choice(USERS)
        pid = new_pid()
        minute += random.randint(0, 2)
        lines.append(
            (
                minute,
                f"{ts(minute)} {HOST} sshd[{pid}]: Failed password for "
                f"{'invalid user ' if random.random() < 0.5 else ''}{user} "
                f"from {ip} port {random.randint(30000, 60000)} ssh2",
            )
        )

    lines.sort(key=lambda x: x[0])
    text = "\n".join(line for _, line in lines) + "\n"
    with open("auth.log", "w") as fh:
        fh.write(text)
    print(f"wrote auth.log ({len(text)} bytes, {len(lines)} lines), flag={FLAG}")


if __name__ == "__main__":
    main()
