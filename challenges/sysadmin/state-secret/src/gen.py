#!/usr/bin/env python3
"""Deterministic generator for the 'state-secret' challenge.

Ships a Terraform bundle:

  * ``main.tf``            - the config: a ``random_password`` used as a vault
                             passphrase and a ``local_file`` that writes an
                             encrypted secrets blob with it.
  * ``terraform.tfstate``  - the state file. Terraform stores *every* resource
                             attribute in plaintext JSON, sensitive ones
                             included, so the passphrase (and a decoy AWS key)
                             sit right there.
  * ``vault.enc``          - the encrypted blob produced by the config.

The blob is encrypted with a stdlib-only scheme:

    salt   = 16 random bytes (stored in the blob header)
    key    = PBKDF2-HMAC-SHA256(passphrase, salt, iters)
    stream = SHA256(key || counter) for counter = 0, 1, 2, ...
    ct     = pt XOR stream

Recovering the passphrase from the state file lets you decrypt the blob to the
flag. The flag never appears in plaintext.
"""

import hashlib
import json
import os

FLAG = "NCTF{tfstate_stores_secrets_in_plaintext_9d21}"

# Obviously-fake dev values.
VAULT_PASSPHRASE = "tf-dev-vault-pass-2024"
DECOY_AWS_SECRET = "AKIAFAKE0000EXAMPLE/notThePassphraseAtAll"

SALT = bytes.fromhex("0f1e2d3c4b5a69788796a5b4c3d2e1f0")
ITERS = 50000
MAGIC = b"ENC1"

MAIN_TF = """\
terraform {
  required_providers {
    random = { source = "hashicorp/random" }
    local  = { source = "hashicorp/local" }
  }
}

# Dev-only. In real life the backend + provider creds would not be committed.
provider "aws" {
  region     = "eu-west-1"
  access_key = "AKIAFAKEACCESSKEY123"
  secret_key = "AKIAFAKE0000EXAMPLE/notThePassphraseAtAll"
}

resource "random_password" "vault" {
  length  = 22
  special = false
}

# Writes the encrypted secrets blob using the generated passphrase.
resource "local_file" "vault" {
  filename       = "${path.module}/vault.enc"
  content_base64 = base64encode(data.external.encrypt.result["blob"])
}
"""


def keystream(key: bytes, n: int) -> bytes:
    out = bytearray()
    ctr = 0
    while len(out) < n:
        out += hashlib.sha256(key + ctr.to_bytes(8, "big")).digest()
        ctr += 1
    return bytes(out[:n])


def encrypt(passphrase: str, plaintext: bytes) -> bytes:
    key = hashlib.pbkdf2_hmac("sha256", passphrase.encode(), SALT, ITERS)
    ks = keystream(key, len(plaintext))
    ct = bytes(a ^ b for a, b in zip(plaintext, ks))
    return MAGIC + SALT + ITERS.to_bytes(4, "big") + ct


def build_tfstate() -> str:
    state = {
        "version": 4,
        "terraform_version": "1.7.5",
        "serial": 3,
        "lineage": "d3adb33f-0000-4000-8000-000000000000",
        "outputs": {},
        "resources": [
            {
                "mode": "managed",
                "type": "random_password",
                "name": "vault",
                "provider": 'provider["registry.terraform.io/hashicorp/random"]',
                "instances": [
                    {
                        "schema_version": 3,
                        "attributes": {
                            "id": "none",
                            "length": 22,
                            "special": False,
                            # Sensitive in HCL, but stored in cleartext here:
                            "result": VAULT_PASSPHRASE,
                        },
                        "sensitive_attributes": [
                            [{"type": "get_attr", "value": "result"}]
                        ],
                    }
                ],
            },
            {
                "mode": "managed",
                "type": "local_file",
                "name": "vault",
                "provider": 'provider["registry.terraform.io/hashicorp/local"]',
                "instances": [
                    {
                        "attributes": {
                            "filename": "./vault.enc",
                            "id": "aa11bb22cc33",
                        }
                    }
                ],
            },
        ],
    }
    return json.dumps(state, indent=2)


def main() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.normpath(os.path.join(here, ".."))
    with open(os.path.join(root, "main.tf"), "w", encoding="utf-8") as fh:
        fh.write(MAIN_TF)
    with open(os.path.join(root, "terraform.tfstate"), "w", encoding="utf-8") as fh:
        fh.write(build_tfstate() + "\n")
    with open(os.path.join(root, "vault.enc"), "wb") as fh:
        fh.write(encrypt(VAULT_PASSPHRASE, FLAG.encode()))
    print("wrote terraform bundle under", root)
    print("decoy aws secret:", DECOY_AWS_SECRET)
    print("flag:", FLAG)


if __name__ == "__main__":
    main()
