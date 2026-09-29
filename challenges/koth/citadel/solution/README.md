# KotH — The Citadel — author notes / verification

**Type:** King-of-the-Hill (shared SSH "root-wars" box + the `koth` scoring plugin)
**Not** a jeopardy challenge: no flag to submit. Points accrue as CTFd `Awards`
every tick a team holds the Citadel.

## How it works

- One shared container runs `sshd`. Teams log in as `player` (password `player`).
- **Privesc:** `sudo -l` shows `player ALL=(root) NOPASSWD: /usr/bin/env` →
  GTFOBins `sudo env sh` gives a root shell.
- **Claim:** as root, write your team token (from the CTFd **King of the Hill**
  page) into `/koth/king` (root:root `600`, so only root can write it).
- **Score:** a root scorer inside the container exposes
  `GET /king` (scorer-token gated) → `{token: <content of /koth/king>, ts: <mtime>}`.
  The `koth` plugin maps the token to a team and awards `points`/tick while the
  claim is fresh — so holding means staying root and re-writing `/koth/king`
  faster than rivals overwrite it.

`solve.sh HOST PORT <team_token>` SSHes in, roots via `sudo env`, and loops the
claim (needs `sshpass`).

## Static verification (docker daemon unavailable in the build env)

- **Scorer `/king`** — confirmed live: returns an empty token before any claim,
  the file content + mtime after a claim, and 403 without `X-Scorer-Token`.
- **Privesc** — `sudo env <shell>` is the documented GTFOBins root; the sudoers
  rule validates with `visudo -cf` at build.
- **Plugin integration** — reuses the same `koth` plugin/contract as The Throne
  (token derivation, token→team mapping, Awards, freshness window). Add the
  Citadel as a second entry in `KOTH_HILLS` (url = the scorer, player_url = ssh).

A live `docker build` + end-to-end run (sshd + real sudo + the scorer scored by
CTFd) is deferred to the arena bring-up; `make local-koth` wires it locally.
