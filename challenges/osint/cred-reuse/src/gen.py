"""Generate a leaked-credentials reuse pivot.

Artifacts:
  * dump.txt        leaked "email:sha1(password)" pairs from a low-value forum
  * wordlist.txt    candidate passwords (rockyou-style) to crack the hashes
  * services.csv    which email is registered on which service
  * admin_portal.enc a note encrypted with the reused password

Pivot: crack the hashes, find the single email registered on BOTH the breached
forum and the admin-portal (password reuse), then decrypt admin_portal.enc with
that password. The container is a STANDARD OpenSSL blob
(`openssl enc -aes-256-cbc -pbkdf2`, the "Salted__" format) so the recovered
password opens it with off-the-shelf tooling and no custom scheme to guess.

Run:  python3 gen.py
"""

import hashlib
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

FLAG = "NCTF{cr3d_reuse_forum_to_admin_portal}"

# email -> plaintext password (all present on the breached forum)
FORUM = {
    "kofi.mensah@webmail.tg": "sunshine",
    "afi.doe@webmail.tg": "Lome228!",  # the reused one
    "yao.k@webmail.tg": "letmein",
    "ama.b@webmail.tg": "password1",
    "delali@webmail.tg": "azerty123",
    "senyo@webmail.tg": "footballtg",
    "edem.a@webmail.tg": "dragon",
    "kwami@webmail.tg": "iloveyou",
}

# services.csv: email, service   (forum breach + which services each uses)
SERVICES = [
    ("kofi.mensah@webmail.tg", "forum"),
    ("afi.doe@webmail.tg", "forum"),
    ("afi.doe@webmail.tg", "admin-portal"),  # reuse: forum + admin-portal
    ("yao.k@webmail.tg", "forum"),
    ("ama.b@webmail.tg", "forum"),
    ("ama.b@webmail.tg", "webmail"),
    ("delali@webmail.tg", "forum"),
    ("senyo@webmail.tg", "forum"),
    ("senyo@webmail.tg", "gitlab"),
    ("edem.a@webmail.tg", "forum"),
    ("kwami@webmail.tg", "forum"),
    # an admin-portal account NOT in the forum breach (cannot be cracked -> decoy)
    ("root.admin@cert.tg", "admin-portal"),
]

# extra wordlist noise
NOISE = ["qwerty", "admin", "welcome", "monkey", "abc123", "trustno1", "master"]

REUSED_PASSWORD = "Lome228!"


def encrypt(plaintext: str, password: str, out_path: str) -> None:
    """Encrypt with the standard OpenSSL AES-256-CBC + PBKDF2 container."""
    subprocess.run(
        [
            "openssl",
            "enc",
            "-aes-256-cbc",
            "-pbkdf2",
            "-salt",
            "-pass",
            f"pass:{password}",
            "-out",
            out_path,
        ],
        input=plaintext.encode(),
        check=True,
    )


def main() -> None:
    with open(os.path.join(ROOT, "dump.txt"), "w") as fh:
        for email, pw in FORUM.items():
            fh.write(f"{email}:{hashlib.sha1(pw.encode()).hexdigest()}\n")

    words = list(FORUM.values()) + NOISE
    words.sort()
    with open(os.path.join(ROOT, "wordlist.txt"), "w") as fh:
        fh.write("\n".join(words) + "\n")

    with open(os.path.join(ROOT, "services.csv"), "w") as fh:
        fh.write("email,service\n")
        for email, svc in SERVICES:
            fh.write(f"{email},{svc}\n")

    note = (
        "ADMIN PORTAL - note de reprise\n"
        "compte: afi.doe (droits elevated)\n"
        f"jeton de secours: {FLAG}\n"
    )
    encrypt(note, REUSED_PASSWORD, os.path.join(ROOT, "admin_portal.enc"))

    print("wrote dump.txt, wordlist.txt, services.csv, admin_portal.enc")


if __name__ == "__main__":
    main()
