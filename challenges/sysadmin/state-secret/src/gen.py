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

The blob is encrypted with the scheme documented (and implemented) in the
shipped ``encrypt.py`` -- the same program ``main.tf`` invokes as a
``data.external`` source:

    salt   = 16 bytes (stored in the blob header)
    key    = PBKDF2-HMAC-SHA256(passphrase, salt, iters)
    stream = SHA256(key || counter) for counter = 0, 1, 2, ...
    ct     = pt XOR stream

Because ``encrypt.py`` ships with the handout, the format is fully documented to
the player; they just need the passphrase, which the tfstate leaks. This
generator imports ``encrypt.py`` so there is a single source of truth for the
format. A fixed salt keeps ``vault.enc`` reproducible. The flag never appears in
plaintext.
"""

import json
import os
import sys

# Single source of truth for the blob format: the shipped encrypt.py.
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..")))
import encrypt  # noqa: E402

FLAG = "NCTF{tfstate_stores_secrets_in_plaintext_9d21}"

# Obviously-fake dev values.
VAULT_PASSPHRASE = "tf-dev-vault-pass-2024"
DECOY_AWS_SECRET = "AKIAFAKE0000EXAMPLE/notThePassphraseAtAll"

# Fixed salt so vault.enc is reproducible across regenerations.
SALT = bytes.fromhex("0f1e2d3c4b5a69788796a5b4c3d2e1f0")
ITERS = 50000

MAIN_TF = """\
terraform {
  required_providers {
    random   = { source = "hashicorp/random" }
    local    = { source = "hashicorp/local" }
    external = { source = "hashicorp/external" }
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

# The encryptor. encrypt.py is committed alongside this config (see its header
# for the exact blob format) and is invoked with the generated passphrase.
data "external" "encrypt" {
  program = ["python3", "${path.module}/encrypt.py"]
  query = {
    passphrase = random_password.vault.result
    infile     = "secret.txt" # local plaintext, not committed
  }
}

# encrypt.py writes ${path.module}/vault.enc directly and returns its path.
resource "local_file" "vault_marker" {
  filename = "${path.module}/.vault-written"
  content  = data.external.encrypt.result["path"]
}
"""


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
                "mode": "data",
                "type": "external",
                "name": "encrypt",
                "provider": 'provider["registry.terraform.io/hashicorp/external"]',
                "instances": [
                    {
                        "attributes": {
                            "id": "-",
                            "program": ["python3", "./encrypt.py"],
                            "query": {
                                # Passphrase also leaks here, via the data source
                                # query stored in state.
                                "passphrase": VAULT_PASSPHRASE,
                                "infile": "secret.txt",
                            },
                            "result": {"path": "vault.enc"},
                        }
                    }
                ],
            },
            {
                "mode": "managed",
                "type": "local_file",
                "name": "vault_marker",
                "provider": 'provider["registry.terraform.io/hashicorp/local"]',
                "instances": [
                    {
                        "attributes": {
                            "filename": "./.vault-written",
                            "content": "vault.enc",
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
        fh.write(encrypt.encrypt(VAULT_PASSPHRASE, FLAG.encode(), SALT, ITERS))
    print("wrote terraform bundle under", root)
    print("decoy aws secret:", DECOY_AWS_SECRET)
    print("flag:", FLAG)


if __name__ == "__main__":
    main()
