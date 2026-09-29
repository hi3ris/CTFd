#!/usr/bin/env python3
"""Deterministic generator for the 'gcp-token-scope' challenge.

A leaked GCP service-account key (`sa-key.json`) for a CI helper, the project's
IAM policy (`iam-policy.json`), and a bucket inventory (`bucket-listing.json`).
The CI service account was granted `roles/storage.objectViewer` at the *project*
level (not scoped to its own bucket), so a token minted from this key can read
every bucket -- including the private artifacts bucket that holds the flag.

The flag object is XOR-sealed with a keystream derived from the key's
`private_key_id` (the material the OAuth token is minted from).
"""

import base64
import hashlib
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))

FLAG = b"NCTF{sa_token_scope_read_the_bucket}"
PROJECT = "kekeli-media-212121"
SA_EMAIL = f"ci-helper@{PROJECT}.iam.gserviceaccount.com"
PRIVATE_KEY_ID = "0a1b2c3d4e5f60718293a4b5c6d7e8f900112233"

FAKE_PEM = (
    "-----BEGIN PRIVATE KEY-----\n"
    "MIIBVAIBADANBgkqhkiG9w0BAQEFAASCAT4wggE6AgEAAkEA0FAKEdevKEYdoNOTuse\n"
    "THISisAfakeDEVELOPMENTkeyForCTFonlyAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\n"
    "AAAAAAAAAAAAAAAAAAAAAAIDAQABAkEAfakefakefakefakefakefakefakefakefake\n"
    "fakefakefakefakefakefakefakefakefakefakefakefakefakefakefakefQIhAPfa\n"
    "-----END PRIVATE KEY-----\n"
)


def keystream(key: bytes, n: int) -> bytes:
    out = bytearray()
    ctr = 0
    while len(out) < n:
        out += hashlib.sha256(key + ctr.to_bytes(4, "big")).digest()
        ctr += 1
    return bytes(out[:n])


SA_KEY = {
    "type": "service_account",
    "project_id": PROJECT,
    "private_key_id": PRIVATE_KEY_ID,
    "private_key": FAKE_PEM,
    "client_email": SA_EMAIL,
    "client_id": "104729183746501928374",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
}

IAM_POLICY = {
    "version": 1,
    "bindings": [
        {
            "role": "roles/editor",
            "members": ["user:ops@kekeli.example"],
        },
        {
            # BUG: project-wide objectViewer for the CI helper. Should have been
            # a bucket-scoped IAM binding on gs://kekeli-ci-cache only.
            "role": "roles/storage.objectViewer",
            "members": [f"serviceAccount:{SA_EMAIL}"],
        },
        {
            "role": "roles/logging.viewer",
            "members": ["group:sre@kekeli.example"],
        },
    ],
}

BUCKETS = {
    "buckets": [
        {
            "name": "kekeli-ci-cache",
            "objects": ["cache/deps.tar", "cache/build-123.log"],
        },
        {
            "name": "kekeli-public-web",
            "objects": ["index.html", "style.css"],
        },
        {
            # private artifacts bucket -- readable only because of the broad grant
            "name": "kekeli-prod-artifacts",
            "objects": [
                "releases/media-svc-1.4.2.tar.gz",
                "releases/RELEASE_TOKEN.enc",
            ],
        },
    ]
}


def main() -> None:
    with open(os.path.join(ROOT, "sa-key.json"), "w", encoding="utf-8") as fh:
        json.dump(SA_KEY, fh, indent=2)
        fh.write("\n")
    with open(os.path.join(ROOT, "iam-policy.json"), "w", encoding="utf-8") as fh:
        json.dump(IAM_POLICY, fh, indent=2)
        fh.write("\n")
    with open(os.path.join(ROOT, "bucket-listing.json"), "w", encoding="utf-8") as fh:
        json.dump(BUCKETS, fh, indent=2)
        fh.write("\n")

    ks = keystream(hashlib.sha256(PRIVATE_KEY_ID.encode()).digest(), len(FLAG))
    ct = bytes(a ^ b for a, b in zip(FLAG, ks))
    obj = {
        "_comment": "gs://kekeli-prod-artifacts/releases/RELEASE_TOKEN.enc (sealed).",
        "seal": "XOR keystream = SHA256(service-account key private_key_id)",
        "ciphertext_b64": base64.b64encode(ct).decode(),
    }
    with open(os.path.join(ROOT, "release-token.json"), "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2)
        fh.write("\n")
    print(
        "[+] wrote sa-key.json, iam-policy.json, bucket-listing.json, release-token.json"
    )


if __name__ == "__main__":
    main()
