# agent-tool-abuse (ai, hard, SERVED)

A live, per-team **two-agent** LLM pipeline for "Halcyon Vault Co." The player
chats with **RELAY** (front office, no vault access); a second agent,
**CUSTODIAN** (back office), drains a shared **handoff log** and performs
fulfilment with privileged vault-custody tools. The tool registry is
over-privileged across an **A2A trust boundary**: CUSTODIAN trusts the handoff
log, but anonymous users can write to it through RELAY.

The intended exploit is a **stored, cross-agent prompt injection / confused
deputy**: poison the handoff log so CUSTODIAN checks the sealed `release-manifest`
(`art-9`) out of the vault and disburses it to an **external** destination. The
flag is emitted by the `disburse` tool **only** on that real custody effect --
verified against per-session mutable server state, never a prompt shape.

- Flag: `NCTF{ HMAC_SHA256(TEAM_SECRET, "ai-agent-tool-abuse")[:24] }`, per team,
  via `flag.py` (`FLAG` / `CHALLENGE_SECRET` injected by the instancier).
- Model: `llama3.1:8b` (tool-capable) reached at `OLLAMA_URL` through the
  admission gateway (`AI_PROXY_TOKEN` bearer) -- same infra as `ai3-tool-abuse`.
- Standalone: no prerequisites.

## Files
- `challenge.yml` -- ctfcli manifest (`type: team_instance`, category `ai`,
  `flags: [{type: team_hmac, content: ai-agent-tool-abuse}]`).
- `Dockerfile`, `docker-compose.yml` -- image `ctf-agent-tool-abuse:latest`.
- `flag.py` -- per-team flag derivation (`get_flag()`).
- `app/app.py` -- two-agent orchestration (RELAY turn, then CUSTODIAN drains the
  queue) + UI.
- `app/tools.py` -- the two tool sets, KB evidence, per-agent dispatch (enforces
  the trust boundary), and the deterministic effect oracle (`disburse`).
- `app/prompts.py` -- RELAY (light guard) and CUSTODIAN (hardened) system prompts.
- `app/model_backends.py` -- Ollama-via-gateway backend + a deterministic offline
  `stub` (CI only) that plays both agents.
- `solution/solve.md` -- full writeup + soundness argument.
- `solution/solve.py` -- offline stub self-test (mechanism/oracle/flag) and a
  `--live` iteration helper.

## Author self-test (offline, no GPU)
```
MODEL_BACKEND=stub TEAM_SECRET=local-demo-team-secret python3 solution/solve.py
```
Proves: read tools work; the `art-3` decoy does not unseal; sealed disburse
without checkout is rejected; sealed + internal disburse does not unseal; the
real checkout + external disburse unseals the gate and returns a flag equal to
`flag.py`. Live model run is marked **Lot 5**.
