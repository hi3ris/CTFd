# lockfile-integrity-drift

One tarball was swapped after the lockfile was generated, so its real hash no
longer matches the pinned `integrity`.

## Vulnerability

`package-lock.json` pins an SRI `integrity` (`sha512-<base64>`) per dependency.
Every shipped `.tgz` matches its pin except `minimist-1.2.8.tgz`, whose bytes
were replaced with an attacker build. The lockfile still carries the original
hash, so the mismatch is detectable offline.

## Solve

1. For each entry, recompute `sha512-` + base64(sha512(tarball bytes)).
2. Compare to the pinned `integrity`. `minimist` mismatches.
3. Extract `package/index.js` from the mismatched tarball; the `_sig` value is
   base64(flag). Decode it.

Run:

```
python3 solution/solve.py
```

## Flag

```
NCTF{1ntegrity_hash_mismatch_carries_flag_d3e1}
```
