# rotate-root — solution

## TL;DR

logrotate's `postrotate` runs `rotate-hook.sh` as root (and sudoers lets
`deploy` trigger it too). The hook writes a rotation token to
`$SECRET_DIR/app-$CYCLE-$HOSTID.token`, derived from `rotate.conf`. Deduce that
path, read the raw token, and wrap it as
`NCTF{logrotate_postrotate_root_<token>}`. No file contains the flag literally.

## The privilege path

- `etc/logrotate.d/app` has a `postrotate` block. logrotate runs from
  `/etc/cron.daily` **as root**, so anything in `postrotate` runs as root.
- `etc/sudoers.d/deploy` additionally grants `deploy` NOPASSWD to run the same
  `rotate-hook.sh` as root on demand.
- So `rotate-hook.sh` is the root-privileged write. It drops its output into
  `/var/lib/app/secrets/` (mode `0700`, root-owned) — unreadable to normal
  users, but the filename is fully predictable.

## Deducing the path

`rotate-hook.sh` sources `etc/app/rotate.conf` and builds:

```
NAME = "app-<CYCLE>-<HOSTID>.token"
OUT  = "$SECRET_DIR/$NAME"
```

With `SECRET_DIR=/var/lib/app/secrets`, `CYCLE=2024w18`, `HOSTID=kbz07`, the file
is `/var/lib/app/secrets/app-2024w18-kbz07.token`. It holds a raw token
(`9f3ac1d20b` in this snapshot); the flag is that token wrapped in the documented
format.

## Attack

1. Parse `SECRET_DIR`, `CYCLE`, `HOSTID` from `rotate.conf`.
2. Apply the hook's naming rule to get the token path.
3. Read the raw token from that path under `fs/`.
4. Wrap: `NCTF{logrotate_postrotate_root_<token>}`.

## Run

```
python3 solve.py
```

Output:

```
[+] deduced root-written token path: /var/lib/app/secrets/app-2024w18-kbz07.token
[+] raw rotation token: 9f3ac1d20b
[+] FLAG = NCTF{logrotate_postrotate_root_9f3ac1d20b}
```

## Files

- `../fs/...` — the ops bundle (mirror of the host paths).
- `../src/gen.py` — deterministic builder.
- `solve.py` — reference solver (stdlib only).
