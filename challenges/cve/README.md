# Category `cve` — live exploitation of real CVEs

This category exists for one reason: the static jeopardy paliers (a file + a
transformation + a flag) are the epreuves an AI agent clears in one shot, and
they are the ones deciding the mid-board. `cve` challenges are the opposite
shape — a **live, per-team service** carrying a **real, recent CVE** that the
player must exploit against _their_ instance. There is no artifact to paste into
a chat, and recalling a writeup is not enough.

See `deploy/anti-llm-guardrails.md` for the reasoning; this file is the recipe.

## Design rules

Every `cve` challenge is:

1. **Served** (`type: team_instance`), never a static download. Flag derived per
   team via the `team_hmac` class (`flag.py` with `CHALLENGE_ID = "cve-<name>"`),
   written into the container at boot, reachable only through the exploit.
2. **Anchored to a real, published CVE.** Prefer **recent** (post-training-cutoff
   for current models: aim mid-2026) and avoid anything with a popular
   Metasploit module or a one-click PoC — those an agent recites. The value is
   deriving the exploit against a live target, not obscurity.
3. **CVE id is a paid hint, never in the description.** The description names the
   symptom (e.g. "an old release of a popular Git library"); identifying _which_
   advisory is part of the work. A cheap first hint narrows the class; a dearer
   hint gives the CVE id and, where it exists, the **patch diff**.
4. **Patch-diff framing where possible.** Ship the fixing commit's diff as the
   hint artifact: the player does patch-diffing (the real vuln-research skill);
   the agent cannot just fetch a PoC.
5. **Self-contained read channel.** The flag comes back to the player without an
   attacker callback server (drop into a served scratch dir, reflect via an
   error, etc.) — a public CTF cannot assume every team runs a collaborator host.

Harder variant for a 500: **partial patch** — apply the official fix but leave
the bug reachable by a neighbouring path, so the public PoC fails. That is the
one that best resists an agent.

## Layout (match the served-challenge convention)

```
cve/<name>/
  challenge.yml        # type: team_instance, flags: team_hmac cve-<name>, paid hints
  Dockerfile           # ctf-cve-<name>:latest ; drop privilege after root boot
  docker-compose.yml   # local build + smoke-test notes
  flag.py              # CHALLENGE_ID = "cve-<name>" (copy an existing served one)
  app/                 # the vulnerable service + entrypoint.sh
  solution/
    README.md          # the vuln, the intended path, verification status
    solve.py           # reference solver: python3 solve.py http://HOST:PORT -> NCTF{...}
```

`make local-seed` picks it up automatically (it globs `challenges/*/*/challenge.yml`);
`make preflight` counts it; `make local-build-images` builds `ctf-cve-<name>`.

## Verification gate

Static checks (imports, byte-compile, flag derivation, YAML, lint) run at author
time. **Live end-to-end exploit is a Lot 5 rehearsal gate** — needs Docker to
build the image and run the exploit — exactly like the other served challenges.
No `cve` challenge ships to the event without its `solution/solve.py` printing
the instance flag against a freshly built container.

## Current entries

| name        | value | CVE            | class                   | status                   |
| ----------- | ----- | -------------- | ----------------------- | ------------------------ |
| `hookrelay` | 350   | CVE-2022-24439 | GitPython arg/URL → RCE | built; Lot 5 live-verify |

Planned slate (choose recent CVEs, span classes): an entry-level one with the CVE
in the description, two mid-hard patch-diff epreuves, one 500 partial-patch.
