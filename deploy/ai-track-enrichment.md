# AI track — enrichment pass (reference-platform alignment)

An additive pass over the existing `ai0 → ai1 → ai2 → ai3` chain (plus the
standalone `agent-tool-abuse`), drawing on well-known AI/LLM CTF platforms.
Every change is **behaviour-preserving for the anti-LLM contract**
(`anti-llm-guardrails.md`): the flag is still never in model context, the
success oracle is still a deterministic server-side effect, there is still at
most one decoy per challenge, and no win condition was changed. Each level was
re-validated against its own deterministic oracle / stub (no live model needed
for the checks below).

## Reference mapping

| Level              | Reference idea                                                                                | What was added                                                                                                                                                                            |
| ------------------ | --------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ai0`              | OWASP LLM06 — sensitive-information disclosure, noisy leaked configs                          | A single **rotated-out decoy token** in the leaked prompt; the solver now decodes every candidate and discriminates by line ("current" vs DEPRECATED).                                    |
| `ai1`              | Gandalf (Lakera) — variety of guard-bypass families                                           | Persona pool 6 → **8**: a **document-boundary** persona (quote the private CONFIG) and an **emotional-appeal / "grandma"** persona; matching solver payloads.                             |
| `ai2`              | Gandalf L4/L7 — escalating output filters                                                     | Two more surviving transforms — **`morse`** and **`fullwidth`** (case-lossy vs case-preserving distinction) — and the filter now **closes the `base32` gap** (one base32 decode layer).   |
| `ai3`              | Wiz _Prompt Airlines_ / OWASP _FinBot_ — manipulate an agent into an unauthorized transaction | Customer-pressure lore (`TCK-1000`, runbook `change-approval-policy`) and a rule-6 clause refusing **SLA tier / account-manager / "entitled customer"** framing. Win condition unchanged. |
| `agent-tool-abuse` | Mozilla **0DIN** — jailbreaking an AI agent (indirect injection)                              | A KB **security bulletin** (`cross-agent-safety`) naming the stored / indirect prompt-injection-across-a-trust-boundary class the challenge models. Guards unchanged.                     |

## Validation performed (deterministic, offline)

- **ai0** — `solution/solve.py` recovers the current flag and rejects the
  rotated decoy.
- **ai2** — booted the (LLM-free) app and ran `solution/solve.py` end to end
  (recover secret → `/verify` → flag); the blocked/survive matrix is exactly
  `{plain, base64, base32, hex, rot13, reverse, spaced, dashed}` blocked and
  `{nato, charcodes, base64x2, morse, fullwidth}` surviving; case-preserving
  survivors round-trip to the exact secret.
- **ai1** — all 8 personas render with `{SECRET}`/`{DEMO}` and no stray braces;
  `pick_index` spreads evenly; `/verify` oracle unchanged.
- **ai3** — `MODEL_BACKEND=stub` self-test passes: decoy does not unseal,
  prod-without-approval rejected, the real approve→deploy chain unseals and the
  tool flag equals `flag.py`.
- **agent-tool-abuse** — `MODEL_BACKEND=stub` self-test passes: decoy and
  no-checkout and internal-disburse all fail; only the external release chain
  unseals, tool flag equals `flag.py`.

Live-model runs (the actual jailbreaks against `llama3.1:8b` through the
admission gateway) remain a **Lot 5 rehearsal** item, as before — they need the
GPU node and are not part of the offline checks above.
