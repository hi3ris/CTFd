# Category `os` — NyxOS, a custom teaching micro-OS

Five served challenges built on **one custom micro-OS ("NyxOS")** written for the
event — one OS, five independently-exploitable subsystems. Custom-OS challenges
are the strongest AI-resistance shape we have: the target is a **novel kernel no
model has seen**, exploitation needs real RE + exploit-dev against live state,
and there is no downloadable writeup to recall. See `deploy/anti-llm-guardrails.md`
and `deploy/ai-resistance-audit.md` for why served + novel beats static.

## The five subsystems

| slot               | pts | subsystem             | bug class → goal (design-level)                        |
| ------------------ | --- | --------------------- | ------------------------------------------------------ |
| `os/nyx-bootstrap` | 400 | bootloader/early boot | image-validation flaw → divert boot → read kernel flag |
| `os/nyx-syscall`   | 500 | syscall table         | missing arg bound → arbitrary kernel r/w → flag        |
| `os/nyx-scheduler` | 550 | scheduler             | TOCTOU race → privilege confusion → ring-0 exec → flag |
| `os/nyx-allocator` | 550 | kernel heap allocator | overflow → object control → flow hijack → flag         |
| `os/nyx-vfs`       | 500 | virtual filesystem    | permission/path bug → read the root-only flag          |

They share one kernel source tree; each challenge enables the one subsystem bug
it teaches, so a single small codebase yields five distinct challenges.

## Build contract (this is NOT the generic Flask stub)

The scaffolder stamped these as STUBS (`state: hidden`, placeholder Flask app).
For `os/` that placeholder is **wrong on purpose** — a custom-OS challenge is not
a web app. The build session replaces it with a **qemu harness**:

- **Served, per-team.** Each team gets its own qemu instance of NyxOS, reachable
  on a per-team TCP port (serial console / a tiny network shell). No downloadable
  kernel image in the public packet — the arena runs it; the player interacts
  live. (A stripped image _may_ be offered as a paid hint for local RE, without
  the flag baked in.)
- **Flag in the kernel, per team.** `entrypoint` derives the flag from the
  injected `CHALLENGE_SECRET` (same `team_hmac` contract as every served
  challenge; `flag.py` already carries the right `CHALLENGE_ID`) and places it
  where only a successful exploit of _that_ subsystem reads it (kernel memory /
  a root-only file inside NyxOS).
- **Success oracle server-side.** The flag appears only after the real effect
  (ring-0 read, root file read); never printed by a normal command.
- **Self-contained.** No attacker callback: the exploit reads the flag over the
  same per-team console it connects on.
- **Solver.** `solution/solve.py` drives the console, runs the exploit, prints
  `NCTF{...}`.

## Runtime shape (for the build session)

- Base image ships `qemu-system-<arch>` + the built NyxOS kernel/initramfs; the
  container's entrypoint injects the flag and boots qemu with a per-team serial
  or a `socat` bridge to the published port.
- The instancier already injects `FLAG` / `CHALLENGE_SECRET` and publishes one
  port per team — the same path the other served challenges use.
- **Verification is a Lot 5 gate** (needs Docker + qemu): `solution/solve.py`
  must print the instance flag against a freshly booted NyxOS before any slot
  flips `state: visible`.

## Status

All five are STUBS (`state: hidden`) — designed, not implemented. The kernel and
the per-subsystem exploits are build-session work (novel exploit code, verified
under qemu). Nothing here ships to the event until its solver passes at Lot 5.
