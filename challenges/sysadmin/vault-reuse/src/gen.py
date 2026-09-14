#!/usr/bin/env python3
"""Deterministic generator for the 'vault-reuse' challenge.

Ships an Ansible-style project whose vault password is *derivable* from
non-secret project metadata that is committed right next to it:

  * ``ansible.cfg``          - points ``vault_password_file`` at a helper script.
  * ``group_vars/all.yml``   - plaintext project metadata (project name, env).
  * ``bin/get-vault-pass.sh`` - the "clever" helper: it builds the vault password
                               deterministically from that metadata instead of
                               reading a real secret.
  * ``group_vars/secrets.yml`` - an Ansible-vault-*style* encrypted file holding
                               the flag.

Because the password is a pure function of committed, non-secret values, anyone
can recompute it and decrypt the vault. The flag is never stored in plaintext.

Vault envelope (stdlib-only, ansible-vault-styled):

    line 1: ``$VAULT;1.0;PBKDF2-SHA256``
    line 2: base64( salt(16) + iters(4, big-endian) + ciphertext )
    key    = PBKDF2-HMAC-SHA256(password, salt, iters)
    stream = SHA256(key || counter) for counter = 0, 1, 2, ...
    ct     = pt XOR stream
"""

import base64
import hashlib
import os

FLAG = "NCTF{ansible_vault_password_was_derivable_4e77}"

PROJECT = "kekeli"
DEPLOY_ENV = "staging"

SALT = bytes.fromhex("a1b2c3d4e5f60718293a4b5c6d7e8f90")
ITERS = 60000

ANSIBLE_CFG = """\
[defaults]
inventory = inventory.ini
host_key_checking = False
# The vault password is produced by a script rather than typed in. Convenient,
# but see bin/get-vault-pass.sh -- it derives the password from public metadata.
vault_password_file = bin/get-vault-pass.sh
"""

GROUP_VARS_ALL = f"""\
---
# group_vars/all.yml -- non-secret project metadata (committed).
project: {PROJECT}
deploy_env: {DEPLOY_ENV}
region: eu-west-1
app_port: 8080
"""

INVENTORY = """\
[web]
web01.kekeli.internal
web02.kekeli.internal

[web:vars]
ansible_user=deploy
"""

GET_VAULT_PASS = """\
#!/bin/sh
# bin/get-vault-pass.sh
# BAD: derives the vault password from committed, non-secret metadata.
# Anyone with the repo can reproduce this exact string.
set -eu

here=$(dirname "$0")
gv="$here/../group_vars/all.yml"

proj=$(awk '/^project:/ {print $2}' "$gv")
env=$(awk '/^deploy_env:/ {print $2}' "$gv")

printf '%s-%s-vault-v1' "$proj" "$env"
"""


def derive_password() -> str:
    return f"{PROJECT}-{DEPLOY_ENV}-vault-v1"


def keystream(key: bytes, n: int) -> bytes:
    out = bytearray()
    ctr = 0
    while len(out) < n:
        out += hashlib.sha256(key + ctr.to_bytes(8, "big")).digest()
        ctr += 1
    return bytes(out[:n])


def make_vault(password: str, plaintext: bytes) -> str:
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), SALT, ITERS)
    ct = bytes(a ^ b for a, b in zip(plaintext, keystream(key, len(plaintext))))
    body = base64.b64encode(SALT + ITERS.to_bytes(4, "big") + ct).decode()
    return "$VAULT;1.0;PBKDF2-SHA256\n" + body + "\n"


def main() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.normpath(os.path.join(here, ".."))
    os.makedirs(os.path.join(root, "group_vars"), exist_ok=True)
    os.makedirs(os.path.join(root, "bin"), exist_ok=True)

    with open(os.path.join(root, "ansible.cfg"), "w", encoding="utf-8") as fh:
        fh.write(ANSIBLE_CFG)
    with open(os.path.join(root, "inventory.ini"), "w", encoding="utf-8") as fh:
        fh.write(INVENTORY)
    with open(os.path.join(root, "group_vars", "all.yml"), "w", encoding="utf-8") as fh:
        fh.write(GROUP_VARS_ALL)
    script_path = os.path.join(root, "bin", "get-vault-pass.sh")
    with open(script_path, "w", encoding="utf-8") as fh:
        fh.write(GET_VAULT_PASS)
    os.chmod(script_path, 0o755)
    with open(
        os.path.join(root, "group_vars", "secrets.yml"), "w", encoding="utf-8"
    ) as fh:
        fh.write(make_vault(derive_password(), FLAG.encode()))

    print("wrote ansible project under", root)
    print("derived vault password:", derive_password())
    print("flag:", FLAG)


if __name__ == "__main__":
    main()
