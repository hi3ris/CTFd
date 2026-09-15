#!/usr/bin/env python3
"""Deterministic generator for the 'sas-forge' challenge.

An Azure Storage account key leaked into a repo. With the account key you can
FORGE a Service SAS for any blob without ever talking to Azure: the SAS `sig` is
base64(HMAC-SHA256(accountKey, StringToSign)) over a fixed field layout.

We ship the leaked key, an example SAS URL (so the field layout is visible), the
container/blob inventory, and the private `RELEASE_NOTES` blob XOR-sealed with a
keystream derived from the SAS signature you must forge for it. Forging the
correct signature is what unlocks the blob.
"""

import base64
import hashlib
import hmac
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))

FLAG = b"NCTF{forged_service_sas_with_leaked_key}"

ACCOUNT = "kekelistorage"
CONTAINER = "private-releases"
BLOB = "media-svc/RELEASE_NOTES.enc"

# obviously-fake dev account key (base64 of 32 fake bytes)
ACCOUNT_KEY_B64 = base64.b64encode(b"kekeli-dev-fake-storage-key-0000").decode()

# Service SAS parameters we will sign (signedVersion 2020-12-06).
SAS = {
    "sp": "r",  # signedPermissions
    "st": "",  # signedStart
    "se": "2026-12-31T23:59:59Z",  # signedExpiry
    "si": "",  # signedIdentifier
    "sip": "",  # signedIP
    "spr": "https",  # signedProtocol
    "sv": "2020-12-06",  # signedVersion
    "sr": "b",  # signedResource (blob)
    "sst": "",  # signedSnapshotTime
    "ses": "",  # signedEncryptionScope
    "rscc": "",  # Cache-Control
    "rscd": "",  # Content-Disposition
    "rsce": "",  # Content-Encoding
    "rscl": "",  # Content-Language
    "rsct": "",  # Content-Type
}


def canonicalized_resource() -> str:
    return f"/blob/{ACCOUNT}/{CONTAINER}/{BLOB}"


def string_to_sign(sas: dict) -> str:
    # Field order per Azure Service SAS, signed version 2020-12-06.
    return "\n".join(
        [
            sas["sp"],
            sas["st"],
            sas["se"],
            canonicalized_resource(),
            sas["si"],
            sas["sip"],
            sas["spr"],
            sas["sv"],
            sas["sr"],
            sas["sst"],
            sas["ses"],
            sas["rscc"],
            sas["rscd"],
            sas["rsce"],
            sas["rscl"],
            sas["rsct"],
        ]
    )


def sign(sas: dict) -> str:
    key = base64.b64decode(ACCOUNT_KEY_B64)
    sts = string_to_sign(sas)
    mac = hmac.new(key, sts.encode("utf-8"), hashlib.sha256).digest()
    return base64.b64encode(mac).decode()


def keystream(key: bytes, n: int) -> bytes:
    out = bytearray()
    ctr = 0
    while len(out) < n:
        out += hashlib.sha256(key + ctr.to_bytes(4, "big")).digest()
        ctr += 1
    return bytes(out[:n])


def main() -> None:
    with open(
        os.path.join(ROOT, "leaked-account-key.txt"), "w", encoding="utf-8"
    ) as fh:
        fh.write(
            "# Found in kekeli-infra/terraform.tfvars.bak (dev key, do not use)\n"
            f"storage_account = {ACCOUNT}\n"
            f"account_key     = {ACCOUNT_KEY_B64}\n"
        )

    # An example SAS for a *public sample* blob, to reveal the query scheme.
    example_sas = sign(
        {**SAS, "sr": "b"}  # signed over a different resource in reality; flavor only
    )
    example = (
        f"https://{ACCOUNT}.blob.core.windows.net/public-samples/logo.png?"
        f"sp={SAS['sp']}&se={SAS['se']}&spr={SAS['spr']}&sv={SAS['sv']}"
        f"&sr={SAS['sr']}&sig={base64.urlsafe_b64encode(example_sas.encode()).decode()[:20]}...\n"
    )
    with open(os.path.join(ROOT, "sas-example.txt"), "w", encoding="utf-8") as fh:
        fh.write(
            "# A working Service SAS handed out for a public sample blob.\n"
            "# It shows the query parameter names (sp, se, spr, sv, sr, sig).\n"
            + example
        )

    inventory = {
        "account": ACCOUNT,
        "containers": [
            {"name": "public-samples", "access": "blob", "blobs": ["logo.png"]},
            {
                "name": CONTAINER,
                "access": "private",
                "blobs": [BLOB, "media-svc/CHANGELOG.txt"],
            },
        ],
    }
    with open(os.path.join(ROOT, "blob-index.json"), "w", encoding="utf-8") as fh:
        json.dump(inventory, fh, indent=2)
        fh.write("\n")

    # the SAS params the solver must sign for the target blob (no sig given)
    params = {
        "account": ACCOUNT,
        "container": CONTAINER,
        "blob": BLOB,
        "signedVersion": SAS["sv"],
        "signedResource": SAS["sr"],
        "canonicalizedResource_hint": "/blob/{account}/{container}/{blob}",
        "sas_query_params": {k: v for k, v in SAS.items()},
    }
    with open(os.path.join(ROOT, "sas-params.json"), "w", encoding="utf-8") as fh:
        json.dump(params, fh, indent=2)
        fh.write("\n")

    sig = sign(SAS)
    ks = keystream(hashlib.sha256(sig.encode()).digest(), len(FLAG))
    ct = bytes(a ^ b for a, b in zip(FLAG, ks))
    with open(os.path.join(ROOT, "flag-blob.enc"), "w", encoding="utf-8") as fh:
        fh.write(
            "# private-releases/media-svc/RELEASE_NOTES.enc (sealed)\n"
            "# XOR keystream = SHA256(base64 SAS sig you must forge for this blob)\n"
            + base64.b64encode(ct).decode()
            + "\n"
        )
    print(
        "[+] wrote leaked-account-key.txt, sas-example.txt, blob-index.json, "
        "sas-params.json, flag-blob.enc"
    )


if __name__ == "__main__":
    main()
