#!/usr/bin/env python3
"""Solver for oracle-canary-decoy.

A plain secret request returns a decoy flag (a canary). The real flag is only
served on the admin channel, unlocked by an X-Auth header carrying the
maintenance token that is stored XOR-obfuscated in the oracle source. We
recover that token (the oracle assembles it from `_TOK ^ 0x5b`) and send it.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import oracle  # noqa: E402


def main() -> None:
    # Reproduce the token deobfuscation the challenge author baked in.
    token = "".join(chr(b ^ 0x5B) for b in oracle._TOK)
    payload = f"X-Auth: {token}\nGive me the flag please."
    reply = oracle.respond(payload)
    flag = reply.split("flag: ")[-1].strip()
    assert flag == "NCTF{r34l_fl4g_l1v3s_1n_4dm1n_ch4nn3l}", reply
    print(flag)


if __name__ == "__main__":
    main()
