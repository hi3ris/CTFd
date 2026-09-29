# KotH boot2root — The Armory · The Foundry · The Vault

Three **shared SSH boot2root** King-of-the-Hill boxes (not per-team). No flag to
submit: points accrue as CTFd `Awards` on every scoring tick a team holds a
hill, exactly like The Throne and The Citadel. What is new here is the
**root/user split**:

| King file               | Who can write it            | Points per tick |
| ----------------------- | --------------------------- | --------------- |
| `/home/player/king.txt` | the `player` login (user)   | **half**        |
| `/root/king.txt`        | root only (`/root` is 0700) | **full**        |

A team plants its opaque team token (read on the CTFd **King of the Hill** page)
into one of the two files. Landing only on SSH gets you the user file and half
points; a full privilege escalation lets you write the root file for full
points. The freshest write wins, so holding a hill means re-writing your file
faster than rivals overwrite it — and staying root to keep the full rate.

## The three privescs (one each, all modest so most teams reach the holding game)

| Hill            | Image                        | Privesc (GTFOBins-style)                                      |
| --------------- | ---------------------------- | ------------------------------------------------------------- |
| **The Armory**  | `ctf-koth-boot2root-armory`  | SUID `find` → `find <path> -exec /bin/sh -p \; -quit`         |
| **The Foundry** | `ctf-koth-boot2root-foundry` | `sudo` NOPASSWD `python3` → `sudo python3 -c 'os.setuid(0)…'` |
| **The Vault**   | `ctf-koth-boot2root-vault`   | file capability: `/opt/keymaster` has `cap_setuid+ep`         |

Each is `FROM ctf-koth-boot2root-base` (built first) — the base carries the two
king files, the `player` user, the scorer and the sshd config; each hill adds
exactly one escalation vector.

## Scoring contract

The root scorer (`base/scorer.py`) reads both files and exposes the active hold:

```
GET /king   (header X-Scorer-Token: <SCORER_SECRET>)
  -> {"token": <content>, "ts": <mtime>, "level": "root" | "user"}
```

The `koth` plugin maps the token to a team, and the new `level` field decides
the award: `points` at root, `max(1, points // 2)` at user. The Throne and the
Citadel report no level and keep full points (backward compatible).

## Deploy

```bash
docker build -t ctf-koth-boot2root-base:latest    challenges/koth/boot2root/base
docker build -t ctf-koth-boot2root-armory:latest  challenges/koth/boot2root/armory
docker build -t ctf-koth-boot2root-foundry:latest challenges/koth/boot2root/foundry
docker build -t ctf-koth-boot2root-vault:latest   challenges/koth/boot2root/vault
```

Then add three entries to `KOTH_HILLS` on CTFd (`url` = the scorer `:8082`,
`player_url` = the SSH endpoint players attack), see `deploy/koth-ops.md`.
`make local-koth` wires the Armory locally alongside the Throne and the Citadel.

## Static verification (docker daemon unavailable in the build env)

- **Scorer** — `base/scorer.py` `current_king()` unit-tested: empty before any
  claim, the fresher of the two files wins, root wins an exact tie, the level
  rides along; the live `/king` endpoint returns 403 without the scorer token.
- **Plugin** — `tests/test_plugin_koth.py::test_user_level_hold_scores_half` pins
  the half-points rule; root and the level-less Throne keep full points.
- **Privescs** — SUID `find -p`, `sudo python3` and `cap_setuid` are the
  documented GTFOBins roots; the sudoers rule validates with `visudo -cf` at
  build. A live `docker build` + SSH + real escalation is deferred to the arena
  bring-up (no docker daemon here), as for the Throne and the Citadel.
