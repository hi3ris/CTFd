#!/usr/bin/env python3
"""Reference solver for 'keystream-reuse'.

Every ciphertext is XORed with the same keystream, so c_i XOR c_j = m_i XOR m_j.
For a given column, XORing two ciphertext bytes reveals m_i XOR m_j. When one of
those plaintext bytes is a space (0x20), the XOR of a space with an ASCII letter
is that letter with its case flipped -- i.e. still an ASCII letter. So the
ciphertext byte that, XORed against the same column of the other ciphertexts,
produces the most ASCII letters is very likely a space, which pins the keystream
byte for that column (key = c XOR 0x20).

Recover the keystream column by column, XOR it back into every ciphertext, and
read the flag out of the recovered plaintexts.
"""
import os
import re
import sys

FLAG_RE = re.compile(rb"NCTF\{[ -~]*?\}")


def is_alpha(b: int) -> bool:
    return 65 <= b <= 90 or 97 <= b <= 122


def solve(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        cts = [bytes.fromhex(line.strip()) for line in fh if line.strip()]
    maxlen = max(len(c) for c in cts)
    key = bytearray(maxlen)

    for col in range(maxlen):
        present = [(i, c[col]) for i, c in enumerate(cts) if col < len(c)]
        best_i, best_score = None, -1
        for i, bi in present:
            score = 0
            for j, bj in present:
                if i == j:
                    continue
                x = bi ^ bj
                # if bi is a space, m_i XOR m_j = m_j (a letter) when m_j alpha
                if x == 0 or is_alpha(x):
                    score += 1
            if score > best_score:
                best_score, best_i = score, bi
        # the winning ciphertext byte corresponds to a space in its plaintext
        key[col] = best_i ^ 0x20

    for c in cts:
        pt = bytes(a ^ b for a, b in zip(c, key))
        m = FLAG_RE.search(pt)
        if m:
            flag = m.group().decode()
            print("[+] FLAG =", flag)
            return flag
    raise SystemExit("flag not recovered")


if __name__ == "__main__":
    default = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "messages.txt"
    )
    solve(sys.argv[1] if len(sys.argv) > 1 else default)
