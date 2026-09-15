#!/usr/bin/env python3
"""Deterministic generator for the 'vault-reuse' challenge.

Ships an Ansible project whose vault password is *derivable* from non-secret
project metadata that is committed right next to it:

  * ``ansible.cfg``          - points ``vault_password_file`` at a helper script.
  * ``group_vars/all.yml``   - plaintext project metadata (project name, env).
  * ``bin/get-vault-pass.sh`` - the "clever" helper: it builds the vault password
                               deterministically from that metadata instead of
                               reading a real secret.
  * ``group_vars/secrets.yml`` - a **genuine** ``ansible-vault`` file (format
                               ``$ANSIBLE_VAULT;1.1;AES256``) holding the flag.

Because the password is a pure function of committed, non-secret values, anyone
can recompute it and open the vault with the real tool::

    ansible-vault view --vault-password-file bin/get-vault-pass.sh \\
        group_vars/secrets.yml

The vault file is produced with the real Ansible ``VaultAES256`` scheme so it
interoperates with the stock ``ansible-vault`` CLI. The flag is never stored in
plaintext. A fixed salt keeps the output byte-for-byte reproducible.

Requires ``pycryptodome`` (for AES-256-CTR) to regenerate the vault blob.
"""

import binascii
import hashlib
import hmac
import os

from Crypto.Cipher import AES
from Crypto.Util import Counter

FLAG = "NCTF{ansible_vault_password_was_derivable_4e77}"

PROJECT = "kekeli"
DEPLOY_ENV = "staging"

# Fixed salt so the shipped vault.enc blob is reproducible across regenerations.
# ansible-vault would normally use a random 32-byte salt here; a real project
# secret is protected the same way regardless of salt.
SALT = bytes.fromhex("a1b2c3d4e5f60718293a4b5c6d7e8f90112233445566778899aabbccddeeff00")
# Ansible's VaultAES256 fixes the KDF at 10000 PBKDF2-HMAC-SHA256 rounds.
KDF_ITERATIONS = 10000

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
# Anyone with the repo can reproduce this exact string, so the ansible-vault
# file next to it protects nothing. ansible calls this script and uses whatever
# it prints on stdout as the vault password.
set -eu

here=$(dirname "$0")
gv="$here/../group_vars/all.yml"

proj=$(awk '/^project:/ {print $2}' "$gv")
env=$(awk '/^deploy_env:/ {print $2}' "$gv")

printf '%s-%s-vault-v1' "$proj" "$env"
"""


def derive_password() -> str:
    return f"{PROJECT}-{DEPLOY_ENV}-vault-v1"


def make_vault(password: str, plaintext: bytes) -> str:
    """Encrypt ``plaintext`` in Ansible's real ``VaultAES256`` (1.1) format.

    Layout, exactly as stock ansible-vault:
      dk    = PBKDF2-HMAC-SHA256(password, salt, 10000, dklen=80)
      key1  = dk[0:32]   (AES-256 key)
      key2  = dk[32:64]  (HMAC-SHA256 key)
      iv    = dk[64:80]  (AES-CTR nonce/counter seed)
      ct    = AES-256-CTR(key1, iv).encrypt(PKCS7(plaintext))
      hmac  = HMAC-SHA256(key2, ct)
      body  = hexlify( hexlify(salt) + "\\n" + hmac_hex + "\\n" + hexlify(ct) )
    prefixed with the ``$ANSIBLE_VAULT;1.1;AES256`` header line.
    """
    dk = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), SALT, KDF_ITERATIONS, dklen=80
    )
    key1, key2, iv = dk[:32], dk[32:64], dk[64:80]

    block = 16
    pad = block - (len(plaintext) % block)
    padded = plaintext + bytes([pad]) * pad

    ctr = Counter.new(128, initial_value=int.from_bytes(iv, "big"))
    ciphertext = AES.new(key1, AES.MODE_CTR, counter=ctr).encrypt(padded)

    mac = hmac.new(key2, ciphertext, hashlib.sha256).hexdigest().encode()
    combined = b"\n".join([binascii.hexlify(SALT), mac, binascii.hexlify(ciphertext)])
    body = binascii.hexlify(combined).decode()

    lines = ["$ANSIBLE_VAULT;1.1;AES256"]
    lines += [body[i : i + 80] for i in range(0, len(body), 80)]
    return "\n".join(lines) + "\n"


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
