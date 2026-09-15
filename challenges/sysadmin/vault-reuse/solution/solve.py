#!/usr/bin/env python3
"""Reference solver for 'vault-reuse'.

``ansible.cfg`` sets ``vault_password_file = bin/get-vault-pass.sh``, and that
helper derives the vault password from committed, non-secret metadata in
``group_vars/all.yml``:

    password = "<project>-<deploy_env>-vault-v1"

So ``group_vars/secrets.yml`` is a *genuine* ansible-vault file whose password is
reproducible straight from the repo. The intended solve is simply::

    ansible-vault view --vault-password-file bin/get-vault-pass.sh \\
        group_vars/secrets.yml

This solver reproduces that. If the ``ansible-vault`` CLI is on ``PATH`` it uses
it directly; otherwise it falls back to decrypting the real ``VaultAES256``
(1.1) envelope itself (PBKDF2-HMAC-SHA256, 10000 rounds -> AES-256-CTR + HMAC),
which requires ``pycryptodome``.
"""

import binascii
import hashlib
import hmac
import os
import re
import shutil
import subprocess


def read_password(root: str) -> str:
    """Reproduce bin/get-vault-pass.sh: '<project>-<deploy_env>-vault-v1'."""
    meta = {}
    with open(os.path.join(root, "group_vars", "all.yml"), encoding="utf-8") as fh:
        for line in fh:
            m = re.match(r"^(\w+):\s*(\S+)\s*$", line)
            if m:
                meta[m.group(1)] = m.group(2)
    return f"{meta['project']}-{meta['deploy_env']}-vault-v1"


def via_ansible_vault(root: str) -> str:
    """Open the vault with the stock ansible-vault CLI (the intended path)."""
    proc = subprocess.run(
        [
            "ansible-vault",
            "view",
            "--vault-password-file",
            "bin/get-vault-pass.sh",
            "group_vars/secrets.yml",
        ],
        cwd=root,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


def via_builtin(root: str, password: str) -> str:
    """Fallback: decrypt the real VaultAES256 (1.1) envelope directly."""
    from Crypto.Cipher import AES
    from Crypto.Util import Counter

    with open(os.path.join(root, "group_vars", "secrets.yml"), encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    if not lines[0].startswith("$ANSIBLE_VAULT;1.1;AES256"):
        raise SystemExit("not a recognised ansible-vault 1.1 file")

    body = binascii.unhexlify("".join(lines[1:]))
    salt_hex, mac_hex, ct_hex = body.split(b"\n")
    salt = binascii.unhexlify(salt_hex)
    ciphertext = binascii.unhexlify(ct_hex)

    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 10000, dklen=80)
    key1, key2, iv = dk[:32], dk[32:64], dk[64:80]

    if not hmac.compare_digest(
        hmac.new(key2, ciphertext, hashlib.sha256).hexdigest().encode(), mac_hex
    ):
        raise SystemExit("HMAC mismatch -- wrong password")

    ctr = Counter.new(128, initial_value=int.from_bytes(iv, "big"))
    padded = AES.new(key1, AES.MODE_CTR, counter=ctr).decrypt(ciphertext)
    return padded[: -padded[-1]].decode()


def solve(root: str) -> str:
    password = read_password(root)
    print("[+] derived vault password:", password)

    if shutil.which("ansible-vault"):
        try:
            flag = via_ansible_vault(root)
            print("[+] opened with ansible-vault CLI")
            print("[+] FLAG =", flag)
            return flag
        except (subprocess.CalledProcessError, OSError) as exc:
            print("[!] ansible-vault CLI failed, using built-in decryptor:", exc)

    flag = via_builtin(root, password)
    print("[+] FLAG =", flag)
    return flag


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    solve(os.path.normpath(os.path.join(here, "..")))
