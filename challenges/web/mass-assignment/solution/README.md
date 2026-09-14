# mass-assignment -- solution

**Summary:** `PATCH /api/me` merges the whole request body into the user record
with no field allowlist, so adding `is_admin: true` promotes the member and
unlocks the flag endpoint.

## Vulnerability

`update_me()` does `user.update(body)` on the parsed JSON. Any field in the
body -- including `is_admin`, which gates `/api/me/flag` -- is written straight
onto the record. The captured request (`capture.http`) shows the endpoint
accepting an arbitrary body and echoing the merged record, confirming the
behaviour.

`/api/me/flag` unseals the flag by XORing `SEALED_FLAG_HEX` with
`sha256("profile-svc-admin-seal-2026")`.

## Steps

1. Load the shipped member from `users.json` (`is_admin: false`).
2. Apply the mass-assignment merge with `{"is_admin": true}`.
3. Re-run the admin check and reproduce the unseal.

Run:

```
python3 solution/solve.py
```

## Flag

```
NCTF{mass_assignment_promoted_me_to_admin_role}
```
