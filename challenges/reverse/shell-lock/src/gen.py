#!/usr/bin/env python3
"""
Developer-only generator for the 'shell-lock' reverse challenge.

Emits the shipped artifact lock.sh: an obfuscated, self-decrypting POSIX shell
script. The password is stored as a hex string of (pass_byte ^ 0x2A); the flag
is stored as base64(xor(flag, password)). The script reconstructs the password,
gates on it, then XOR-decrypts the flag. Neither the password nor the flag
appears in plaintext. This file is NOT shipped to players.
"""

import base64

PASS = b"sh3ll_w1zard"
FLAG = b"NCTF{sh3ll_self_d3crypt_pe3led}"

TEMPLATE = r"""#!/bin/sh
# ---------------------------------------------------------------------------
# ACME vault. usage:  sh lock.sh <password>
# (this file was minified/obfuscated by the build; nothing here is plaintext)
# ---------------------------------------------------------------------------
_k=%K%
_b=%B%
_p=$(printf '%s' "$_k" | perl -ne 'chomp;print chr(hex($1)^0x2a)while/(..)/g')
[ "$1" = "$_p" ] || { echo "access denied"; exit 1; }
printf '%s' "$_b" | base64 -d | perl -e '$k=shift;local $/;$d=<STDIN>;print join("",map{chr(ord(substr($d,$_,1))^ord(substr($k,$_%length($k),1)))}0..length($d)-1),"\n"' "$_p"
"""


def main():
    import os

    k = "".join("%02x" % (b ^ 0x2A) for b in PASS)
    enc = bytes(FLAG[i] ^ PASS[i % len(PASS)] for i in range(len(FLAG)))
    b = base64.b64encode(enc).decode()

    script = TEMPLATE.replace("%K%", k).replace("%B%", b)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, "lock.sh")
    out = os.path.normpath(out)
    with open(out, "w") as f:
        f.write(script)
    os.chmod(out, 0o755)
    print("wrote", out)
    print("pass =", PASS.decode())
    print("flag =", FLAG.decode())


if __name__ == "__main__":
    main()
