# Provably-Fair Rail Casino — public spec (partial)

You connect to a live per-team service over **raw TCP** and speak a small
**line-delimited JSON** protocol (one JSON object per line, UTF-8, `\n`
terminated). It is not HTTP.

## The game

An 11-card deck, cards labelled `0..10`. Each *hand*:

1. Server prompts you: `{"msg":"place_call","hand":n,"streak":s}`
2. You reply with your call **before** the deal:
   `{"call": <int 0..10>}`
3. The server deals the hand and publishes the full result:
   `{"msg":"reveal","hand":n,"shuffle":[...11 cards...],
     "high_card":h,"your_call":c,"result":"WIN"|"MISS","streak":s'}`

Land **10 correct calls in a row** and the service pays the jackpot:
`{"msg":"jackpot","flag":"NCTF{...}"}`. Any miss resets the streak to `0`.
Hands are unlimited and there is no penalty for a miss beyond the reset.

**Flag format:** `NCTF{...}`

## The "provably fair" RNG (public)

Shuffles come from a **truncated linear congruential generator**:

```
state_{n+1} = (A * state_n + C) mod M
```

with published constants

```
M = 1099511627776      # 2**40
A = 2654435761
C = 3039632973
```

Each hand advances the state once and publishes a **rank** derived from the top
bits of the new state. The rank is turned into the dealt order by a plain
**factorial-base (Lehmer) decode in lexicographic order** over the pool
`[0,1,...,10]`:

```
def decode_shuffle(rank):
    pool, perm, r = list(range(11)), [], rank
    for i in range(11):
        base = factorial(10 - i)
        idx, r = divmod(r, base)
        perm.append(pool.pop(idx))
    return perm
```

Because `2**24 < 11!`, every rank the service can publish maps to exactly one
permutation, so a published order inverts back to exactly one rank.

## Committed seed

The banner publishes `commitment = SHA-256(seed)` for auditability. The seed is
the initial LCG state, chosen fresh per connection, and is **never revealed**.

## What the spec does NOT tell you (infer it from `samples.json`)

- **How many low bits of each state are withheld** before it becomes the
  published rank (i.e. how `rank` relates to `state`). The sample transcript is
  internally consistent with the RNG above for exactly one shift — find it.
- **Which card of a dealt order is the "high card"** you are calling. The
  `high_card` field in every sample hand tells you; confirm the rule.

`samples.json` is a full transcript from a **throwaway sample seed** (not a live
instance). Everything you need to pin the encoding is in there before you ever
place a live call.

## A word on the commitment

Chasing a SHA-256 preimage of the committed seed is a dead end and unnecessary:
you never need the seed. Recover the *running state* from a couple of published
shuffles and you can call every future hand exactly.
