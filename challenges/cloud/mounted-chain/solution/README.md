# mounted-chain — solution

## TL;DR

The RoleBinding grants the `media-worker` ServiceAccount `get`/`list` on
Secrets. The mounted Secret's `token` value is double base64-encoded (once by
the app, once by Kubernetes), so decoding it twice yields the flag.

## Technique

Two ideas:

1. **RBAC reachability.** `role.yaml` grants `get`/`list` on `secrets` in the
   `kekeli` namespace, and `rolebinding.yaml` binds that Role to the
   `media-worker` ServiceAccount used by the Deployment. So the workload can
   read `media-worker-vault`.
2. **Double base64.** Kubernetes stores everything under `data:` base64-encoded.
   The application also base64-encoded the secret before handing it to
   Kubernetes, so `data.token` is `base64(base64(flag))`.

## Attack

1. Confirm the RoleBinding → Role → `secrets` `get` path.
2. Read `data.token` from `secret.yaml`.
3. `base64 -d` once → another base64 string; `base64 -d` again → the flag.

The `api_key` field is a distractor (decodes to a dev API key, not a flag).

## Run

```
python3 solve.py
```

Output:

```
[+] FLAG = NCTF{rbac_get_secrets_then_base64_twice}
```

## Files

- `../secret.yaml` — the mounted Secret (double-encoded token).
- `../role.yaml`, `../rolebinding.yaml`, `../serviceaccount.yaml` — the RBAC path.
- `../deployment.yaml` — shows the Secret is mounted by the SA's pod.
- `../src/gen.py` — deterministic builder (not shipped).
- `solve.py` — reference solver (stdlib only).
