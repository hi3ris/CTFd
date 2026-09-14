# sub-wildcard — solution

## TL;DR

The `ci-deployer` trust policy gates the GitHub OIDC `sub` claim with
`StringLike "repo:kekeli-cloud/*"`, which admits any repo in the org — including
an attacker's fork. That fork's token assumes the role, which can read the
release secret. The secret is sealed with `SHA256(sub)`; decrypt it for the
flag.

## Technique

GitHub Actions OIDC subjects look like
`repo:<owner>/<repo>:ref:refs/heads/<branch>`. A correct trust policy pins the
full subject (repo **and** ref). This one uses a `StringLike` wildcard:

```json
"token.actions.githubusercontent.com:sub": "repo:kekeli-cloud/*"
```

Any repository under `kekeli-cloud/` matches — so `kekeli-cloud/media-svc-fork`
(an attacker fork) can call `sts:AssumeRoleWithWebIdentity` and become
`ci-deployer`, which grants `secretsmanager:GetSecretValue` on the release
secret.

## Attack

1. Read the `StringLike` condition on `sub` in `trust-policy.json`.
2. Check the captured token's `sub` in `oidc-token.json` against that wildcard
   (and confirm `aud`). It matches.
3. Confirm `role-permissions.json` grants `secretsmanager:GetSecretValue` on the
   release secret — reachable once assumed.
4. The sealed `SecretStringCiphertextB64` is XORed with a keystream derived from
   `SHA256(sub)`. Recompute and decrypt.

## Run

```
python3 solve.py
```

Output:

```
[+] FLAG = NCTF{oidc_sub_wildcard_assumed_the_role}
```

## Files

- `../trust-policy.json` — the OIDC trust policy (the wildcard bug).
- `../oidc-token.json` — decoded claims of the attacker fork's token.
- `../role-permissions.json` — proves the secret is reachable once assumed.
- `../release-secret.json` — the sealed secret value.
- `../src/gen.py` — deterministic builder (not shipped).
- `solve.py` — reference solver (stdlib only).
