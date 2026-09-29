#!/usr/bin/env python3
"""Deterministic generator for the 'rbac-reveal' challenge.

Ships a small Kubernetes manifest bundle:

  * ``rbac.yaml``       - an over-permissive Role that grants ``get``/``list``
                          on ``secrets`` to the app's ServiceAccount (a
                          namespace-wide secret reader — it should be scoped to
                          one named secret, if it should exist at all).
  * ``secret.yaml``     - an Opaque Secret. Its ``data`` values are base64 (as
                          all Secret ``data`` is). Someone pre-encoded the value
                          before pasting it in, so it is base64 *of* base64.
  * ``deployment.yaml`` - mounts that Secret into the pod.

Since the RBAC lets the ServiceAccount read the Secret, and a Secret is only
base64 (encoding, not encryption), the value is trivially recoverable. Decoding
the shipped ``token`` value twice yields the flag. No plaintext flag ships.
"""

import base64
import os

FLAG = "NCTF{k8s_secret_is_base64_not_encryption}"


def double_b64(s: str) -> str:
    once = base64.b64encode(s.encode()).decode()
    return base64.b64encode(once.encode()).decode()


RBAC = """\
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: app-reader
  namespace: kekeli
rules:
  # Over-permissive: reads EVERY secret in the namespace. Should be limited to
  # resourceNames: ["app-api"] at most.
  - apiGroups: [""]
    resources: ["secrets"]
    verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: app-reader-binding
  namespace: kekeli
subjects:
  - kind: ServiceAccount
    name: app
    namespace: kekeli
roleRef:
  kind: Role
  name: app-reader
  apiGroup: rbac.authorization.k8s.io
"""

DEPLOYMENT = """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
  namespace: kekeli
spec:
  replicas: 1
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api
    spec:
      serviceAccountName: app
      containers:
        - name: api
          image: kekeli/internal-api:staging
          volumeMounts:
            - name: creds
              mountPath: /etc/creds
              readOnly: true
      volumes:
        - name: creds
          secret:
            secretName: app-api
"""


def build_secret() -> str:
    token = double_b64(FLAG)
    username = base64.b64encode(b"api").decode()
    return f"""\
apiVersion: v1
kind: Secret
metadata:
  name: app-api
  namespace: kekeli
type: Opaque
data:
  username: {username}
  # NOTE: value was already base64'd by the deploy script before `kubectl` also
  # base64'd it as Secret data. Whoops.
  token: {token}
"""


def main() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.normpath(os.path.join(here, ".."))
    with open(os.path.join(root, "rbac.yaml"), "w", encoding="utf-8") as fh:
        fh.write(RBAC)
    with open(os.path.join(root, "secret.yaml"), "w", encoding="utf-8") as fh:
        fh.write(build_secret())
    with open(os.path.join(root, "deployment.yaml"), "w", encoding="utf-8") as fh:
        fh.write(DEPLOYMENT)
    print("wrote manifests under", root)
    print("flag:", FLAG)


if __name__ == "__main__":
    main()
