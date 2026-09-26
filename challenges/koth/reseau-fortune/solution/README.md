# reseau-fortune (KotH hill) -- notes

**Type:** shared King-of-the-Hill hill (NOT a jeopardy challenge — no
`challenge.yml`, no `flag.py`). **Class:** business-logic / MLM economy.
**Scoring:** the CTFd `koth` plugin polls `/king` each tick and awards points to
the current holder; here the holder is **the richest network right now**.

## Concept

One shared MLM arena, **Réseau Fortune**. Each team joins with its KotH token
(shown on the CTFd "King of the Hill" page) via `POST /api/join {token}` and gets
a distributor account seeded with 50 000 FCFA. Commissions (20/8/4 % over three
sponsor levels) flow up the chain on each purchase; the house keeps the rest, so
**legitimate play is a net loss** and sybil registration (phone never verified,
no SMS) mints nothing by itself. Teams must find a money-minting logic flaw and
out-earn each other; whoever is richest holds the crown and scores.

`GET /king` (header `X-Scorer-Token: SCORER_SECRET`) returns the KotH token of
the richest team (empty until someone is ahead) — this is the only scorer
surface; no flag exists.

## Minting bugs (same engine as web/reseau-pyramide, no flag gate)

- **A. Non-idempotent activation bonus** — `/api/bonus/activation` credits the
  sponsor every call, not once per filleul. Replay to mint.
- **B. Refund without commission clawback** — `/api/refund` returns the price
  but not the commission already paid to the sponsor; buy→refund→transfer-back
  between your own accounts mints the commission each cycle.

Cross-team griefing is not possible on balances (you only ever help the sponsor
code you name, and can only move money out of your own accounts). The race is
purely who mints fastest and holds the lead.

## Tuning levers (organizers, `deploy/koth-ops.md`)

- Points/tick and tick cadence set the score cap (finale: `points=5, tick=30`).
- Registration/mint rate-limit bounds throughput so the winner is the best
  automation, not the fattest pipe. (Add a reverse-proxy rate limit at the front;
  the app itself is intentionally permissive for authoring.)
- Optional harder edges for a tougher finale: a TOCTOU double-claim (run the app
  multi-threaded and add an unlocked one-time bonus) or a referral-cycle payout.
  Left out of the shipped app to keep scoring deterministic.

## Reference holder

```
python3 solution/solve.py http://HILL:PORT <koth_token> [scorer_secret] [target_gain]
```

Joins, mints past `target_gain` via bug A, and (with the scorer secret) confirms
`/king` crowns our token.

## Verification status

Verified **offline** (no Docker) against the shipped Flask app: two teams join,
the exploiting team reaches net_gain > 1 000 000 and `/king` returns its token
while the idle team stays at 0; `/king` is 403 without the scorer secret and
empty before anyone is ahead. Arena bring-up (KOTH_HILLS entry + scorer cadence)
per `deploy/koth-ops.md`.
