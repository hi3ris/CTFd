#!/usr/bin/env python3
"""Generate the sbom-component-swap artifact bundle.

A CycloneDX SBOM lists the components of a release, each with a SHA-256 hash
and a shipped binary blob. A separate advisory file lists known-bad hashes.
Exactly one component's hash appears in the advisory; that component's blob
carries the flag (base64).
"""

import base64
import hashlib
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)

FLAG = "NCTF{sb0m_component_hash_pivot_9f4c}"


def build():
    comps = [
        ("libjpeg-turbo", "3.0.1", b"JPEG codec build; nothing to see here.\n"),
        ("zlib", "1.3", b"deflate/inflate routines, standard build.\n"),
        (
            "acme-updater",
            "2.4.0",
            b"// updater agent\nvar cfg = '"
            + base64.b64encode(FLAG.encode())
            + b"';\n",
        ),
        ("openssl", "3.2.1", b"crypto library, vendored build.\n"),
    ]
    malicious = "acme-updater"

    components = []
    bad_hash = None
    for name, version, data in comps:
        blob_name = f"component-{name}.bin"
        with open(os.path.join(OUT, blob_name), "wb") as fh:
            fh.write(data)
        digest = hashlib.sha256(data).hexdigest()
        if name == malicious:
            bad_hash = digest
        components.append(
            {
                "type": "library",
                "name": name,
                "version": version,
                "purl": f"pkg:generic/{name}@{version}",
                "hashes": [{"alg": "SHA-256", "content": digest}],
                "properties": [{"name": "blob", "value": blob_name}],
            }
        )

    bom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "version": 1,
        "metadata": {"component": {"type": "application", "name": "acme-suite"}},
        "components": components,
    }
    with open(os.path.join(OUT, "bom.json"), "w") as fh:
        json.dump(bom, fh, indent=2)
        fh.write("\n")

    advisory = (
        "# Known-bad artifact hashes (SHA-256) - internal SOC feed\n"
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  "
        "empty-placeholder\n"
        "5feceb66ffc86f38d952786c6d696c79c2dbc239dd4e91b46729d73a27fb57e9  "
        "test-vector-a\n"
        f"{bad_hash}  acme-updater-backdoor\n"
        "6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4b  "
        "test-vector-b\n"
    )
    with open(os.path.join(OUT, "known-bad-hashes.txt"), "w") as fh:
        fh.write(advisory)

    print("built sbom-component-swap artifacts")


if __name__ == "__main__":
    build()
