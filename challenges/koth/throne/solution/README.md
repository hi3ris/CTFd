# KotH — The Throne — author notes / verification

**Type:** King-of-the-Hill (shared hill service + `koth` scoring plugin)
**Not** a jeopardy challenge: there is no flag to submit. Points accrue as CTFd
`Awards` every tick a team holds the throne, which the scoreboard sums like any
other score.

## How scoring works

- One shared container (`ctf-koth-throne`) is the hill. Its `POST /throne`
  accepts a claim `{team, ts, sig}` where `sig = HMAC_SHA1(HILL_KEY, "team|ts")`
  and `ts` is within `SKEW` seconds of now.
- Each team has an opaque 16-hex **token** derived by the CTFd `koth` plugin
  (`HMAC_SHA256(KOTH_GLOBAL_SECRET, "koth:<hill-id>:<account_id>")[:16]`), shown
  on the in-app **King of the Hill** page. The hill treats it as an opaque
  string; only CTFd can map a token back to a team.
- The plugin's scorer polls `GET /king` (scorer-only, `X-Scorer-Token`) every
  `KOTH_TICK` seconds; if the current claim is fresh (within
  `KOTH_FRESH_WINDOW`), it inserts an `Awards` row (`value = points`) for the
  holding team. `get_standings` sums awards, so the kart scoreboard advances the
  holder automatically.

## The intended play

1. **Stage 1 — leak `HILL_KEY` (access-control bug).** `/debug` is meant to be
   internal-only but decides that by trusting the **left-most `X-Forwarded-For`**
   value. Send `X-Forwarded-For: 127.0.0.1` and it returns `HILL_KEY`.
2. **Stage 2 — hold the throne.** Read your team token from the CTFd KotH page,
   then sign `HMAC_SHA1(HILL_KEY, "<token>|<ts>")` with a fresh `ts` and
   `POST /throne`. Re-post every few seconds (< `SKEW`): a claim decays, so
   holding is a continuous contest against the other teams.

`solve.sh http://HILL:PORT <team_token>` does both (leak, then loop-claim).

## Static verification (docker unavailable in the build env)

Validated at the logic level without a container build:

- **Hill service** — ran `app.py` live: `/debug` returns 403 normally and leaks
  `HILL_KEY` with the spoofed `X-Forwarded-For: 127.0.0.1`; a fresh signed claim
  is accepted and reflected by scorer-gated `/king`; stale-`ts` and bad-signature
  claims are rejected; `/king` without the scorer token is 403.
- **Signature parity** — the `openssl dgst -sha1 -hmac` used by `solve.sh`
  produces the exact digest Python's `hmac` expects, so the solver claims
  successfully.
- **Token derivation** — `koth_token_for` is unique per team and per hill, and a
  planted token resolves back to the correct account.
- **Plugin** — imports cleanly against CTFd 3.8.7; `KOTH_HILLS` parses; every
  `Awards` column and plugin function referenced exists.

A live run (build `ctf-koth-throne`, set `KOTH_*`, watch a held throne raise a
team's score) is deferred to the arena bring-up — see `deploy/koth-ops.md`.
