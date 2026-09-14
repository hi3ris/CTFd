#!/usr/bin/env python3
"""Deterministic generator for the 'mounted-chain' challenge.

A dump of a Kubernetes namespace: a ServiceAccount, a Role that grants
`get`/`list` on `secrets`, a RoleBinding wiring them together, a Deployment that
mounts one secret, and the Secret object itself.

Kubernetes stores Secret values base64-encoded. Here the application *also*
base64-encoded the value before storing it, so the mounted `token` decodes to
another base64 blob, which decodes to the flag.
"""

import base64
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))

FLAG = "NCTF{rbac_get_secrets_then_base64_twice}"


def b64(s: bytes) -> str:
    return base64.b64encode(s).decode()


SA = """\
apiVersion: v1
kind: ServiceAccount
metadata:
  name: media-worker
  namespace: kekeli
"""

ROLE = """\
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: secret-reader
  namespace: kekeli
rules:
  - apiGroups: [""]
    resources: ["secrets"]
    verbs: ["get", "list"]
"""

BINDING = """\
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: media-worker-secret-reader
  namespace: kekeli
subjects:
  - kind: ServiceAccount
    name: media-worker
    namespace: kekeli
roleRef:
  kind: Role
  name: secret-reader
  apiGroup: rbac.authorization.k8s.io
"""

DEPLOY = """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: media-worker
  namespace: kekeli
spec:
  replicas: 1
  selector:
    matchLabels:
      app: media-worker
  template:
    metadata:
      labels:
        app: media-worker
    spec:
      serviceAccountName: media-worker
      containers:
        - name: worker
          image: registry.kekeli.internal/media-worker:1.4.2
          volumeMounts:
            - name: vault
              mountPath: /var/run/secrets/app
              readOnly: true
      volumes:
        - name: vault
          secret:
            secretName: media-worker-vault
"""


def build_secret() -> str:
    inner = b64(FLAG.encode())  # app pre-encodes the flag
    stored = b64(inner.encode())  # k8s base64s the stored value
    return f"""\
apiVersion: v1
kind: Secret
metadata:
  name: media-worker-vault
  namespace: kekeli
type: Opaque
data:
  token: {stored}
  # a distractor: a base64 API key that is NOT the flag chain
  api_key: {b64(b"kekeli-dev-apikey-0000-not-a-flag")}
"""


def main() -> None:
    files = {
        "serviceaccount.yaml": SA,
        "role.yaml": ROLE,
        "rolebinding.yaml": BINDING,
        "deployment.yaml": DEPLOY,
        "secret.yaml": build_secret(),
    }
    for name, body in files.items():
        with open(os.path.join(ROOT, name), "w", encoding="utf-8") as fh:
            fh.write(body)
    print("[+] wrote", ", ".join(files))


if __name__ == "__main__":
    main()
