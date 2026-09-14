#!/usr/bin/env python3
"""Deterministic generator for the 'mask-slip' challenge.

Ships a GitHub Actions workflow and a captured job log. GitHub Actions replaces
any *literal* occurrence of a registered secret with ``***`` in logs. It does
NOT understand transformations of that secret: if you pipe the secret through
``base64`` (or ``rev``, ``xxd``, ...), the transformed bytes are printed in the
clear because they no longer match the literal secret string.

The workflow here:
  * echoes the secret directly (correctly masked as ``***`` in the log), then
  * "for debugging" pipes it through ``base64`` — and that line leaks.

The base64 blob in the shipped ``run.log`` decodes straight back to the secret,
which is the flag. Nothing is stored in plaintext.
"""

import base64
import os

FLAG = "NCTF{ci_secret_masking_is_only_literal_b64}"

WORKFLOW = """\
name: deploy
on:
  push:
    branches: [main]

jobs:
  ship:
    runs-on: ubuntu-latest
    env:
      DEPLOY_TOKEN: ${{ secrets.DEPLOY_TOKEN }}
    steps:
      - uses: actions/checkout@v4

      - name: Echo token (masked)
        run: |
          echo "using token: $DEPLOY_TOKEN"

      - name: Debug token length
        run: |
          echo -n "$DEPLOY_TOKEN" | wc -c

      # BAD: base64 of the secret is NOT masked, GitHub only masks the literal.
      - name: Debug token (base64)
        run: |
          echo -n "$DEPLOY_TOKEN" | base64

      - name: Deploy
        run: ./deploy.sh
"""


def build_log(secret: str) -> str:
    b64 = base64.b64encode(secret.encode()).decode()
    return f"""\
2024-05-02T09:14:03.1Z ##[group]Run echo "using token: $DEPLOY_TOKEN"
2024-05-02T09:14:03.2Z using token: ***
2024-05-02T09:14:03.3Z ##[endgroup]
2024-05-02T09:14:03.4Z ##[group]Run echo -n "$DEPLOY_TOKEN" | wc -c
2024-05-02T09:14:03.5Z {len(secret)}
2024-05-02T09:14:03.6Z ##[endgroup]
2024-05-02T09:14:03.7Z ##[group]Run echo -n "$DEPLOY_TOKEN" | base64
2024-05-02T09:14:03.8Z {b64}
2024-05-02T09:14:03.9Z ##[endgroup]
2024-05-02T09:14:04.0Z ##[group]Run ./deploy.sh
2024-05-02T09:14:04.1Z deploying to staging...
2024-05-02T09:14:04.2Z ok
2024-05-02T09:14:04.3Z ##[endgroup]
"""


def main() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.normpath(os.path.join(here, ".."))
    wf_dir = os.path.join(root, ".github", "workflows")
    os.makedirs(wf_dir, exist_ok=True)
    with open(os.path.join(wf_dir, "deploy.yml"), "w", encoding="utf-8") as fh:
        fh.write(WORKFLOW)
    with open(os.path.join(root, "run.log"), "w", encoding="utf-8") as fh:
        fh.write(build_log(FLAG))
    print("wrote workflow and run.log under", root)
    print("flag:", FLAG)


if __name__ == "__main__":
    main()
