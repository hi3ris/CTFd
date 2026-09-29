# alias-slip — solution

## TL;DR

The nginx site uses `location /assets` (no trailing slash) with
`alias /srv/kekeli/public/assets/` (trailing slash). That off-by-slash lets a
request escape the assets directory into its sibling `config/`, where a stale
`settings.py.bak` still holds the admin token. The flag is that token wrapped as
`NCTF{nginx_alias_offbyslash_<token>}` (no file contains the flag literally).

## The misconfiguration

`alias` replaces the matched `location` prefix with the alias path. When the
location has no trailing slash but the alias does, nginx keeps whatever the
client typed after the prefix and appends it to the alias verbatim — dot-dot
included. So:

```
request:  /assets../config/settings.py.bak
maps to:  /srv/kekeli/public/assets/ + ../config/settings.py.bak
        = /srv/kekeli/public/config/settings.py.bak
```

The `location /config { deny all; }` rule is bypassed entirely because the
request never matches `/config` — it matches `/assets`.

## Attack

1. Parse `nginx.conf`; find the `location`/`alias` pair whose slashes disagree.
2. Build `/assets../config/settings.py.bak` and normalize it to the real server
   path.
3. Resolve that path against the shipped `webroot/` mirror and read the backup.
4. Take `ADMIN_API_TOKEN` and wrap it as `NCTF{nginx_alias_offbyslash_<token>}`.

## Run

```
python3 solve.py
```

Output:

```
[+] vulnerable block: location /assets  alias /srv/kekeli/public/assets/
[+] request /assets../config/settings.py.bak  ->  /srv/kekeli/public/config/settings.py.bak
[+] leaked admin token: a7f3c0de91
[+] FLAG = NCTF{nginx_alias_offbyslash_a7f3c0de91}
```

## Files

- `../nginx.conf` — the vulnerable site config.
- `../webroot/...` — the served document tree (mirror of the server paths).
- `../src/gen.py` — deterministic builder.
- `solve.py` — reference solver (stdlib only).
