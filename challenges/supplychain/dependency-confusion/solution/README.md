# dependency-confusion

Dependency-confusion attack: the internal package name is also claimed on the
public registry with a higher version, so the installer pulls the attacker's
tarball.

## Vulnerability

`acme-telemetry` exists on the internal registry at `1.2.3`. An attacker
published `acme-telemetry@9.9.9` to the public npm registry. npm resolves the
**highest** semver across all configured registries, so the public `9.9.9`
tarball is installed. That tarball ships a `postinstall` hook.

## Solve

1. Parse both registry metadata dumps and pick the highest version across
   them — `9.9.9`, from `registry-public.json`.
2. Extract `package/package.json` from `acme-telemetry-9.9.9.tgz`.
3. Read `scripts.postinstall`; it runs
   `Buffer.from('<base64>','base64').toString()`.
4. base64-decode that string. It is an exfil command whose query string
   contains the flag.

Run:

```
python3 solution/solve.py
```

## Flag

```
NCTF{d3p_c0nfusion_higher_version_wins_a1f7}
```
