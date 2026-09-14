#!/usr/bin/env python3
"""Reference solver for 'vigenere-drift'.

The cipher is a Vigenere whose effective shift drifts up by one each full period:
    shift(n) = (base[n % L] + n // L) mod 26   (n counts letters only)

Because the drift term (n // L) is public, each key column is still a *constant*
unknown offset once the drift is subtracted. So for every column we try all 26
base offsets and pick the one whose recovered letters best match English letter
frequencies (chi-squared). We sweep the key length L and confirm the answer with
the flag marker "NCTF{".
"""
import os
import sys

# English letter frequencies (percent).
ENGLISH = {
    "a": 8.167,
    "b": 1.492,
    "c": 2.782,
    "d": 4.253,
    "e": 12.702,
    "f": 2.228,
    "g": 2.015,
    "h": 6.094,
    "i": 6.966,
    "j": 0.153,
    "k": 0.772,
    "l": 4.025,
    "m": 2.406,
    "n": 6.749,
    "o": 7.507,
    "p": 1.929,
    "q": 0.095,
    "r": 5.987,
    "s": 6.327,
    "t": 9.056,
    "u": 2.758,
    "v": 0.978,
    "w": 2.360,
    "x": 0.150,
    "y": 1.974,
    "z": 0.074,
}


def letter_positions(text):
    """Return list of (index_in_text, lowercase_char, is_upper) for letters."""
    res = []
    for i, ch in enumerate(text):
        if "a" <= ch <= "z":
            res.append((i, ch, False))
        elif "A" <= ch <= "Z":
            res.append((i, ch.lower(), True))
    return res


def chi_squared(counts, total):
    score = 0.0
    for c in "abcdefghijklmnopqrstuvwxyz":
        expected = ENGLISH[c] / 100.0 * total
        observed = counts.get(c, 0)
        score += (observed - expected) ** 2 / expected
    return score


def recover_key(letters, length):
    key = []
    for col in range(length):
        best_off, best_score = 0, None
        col_ns = [n for n in range(len(letters)) if n % length == col]
        for off in range(26):
            counts = {}
            for n in col_ns:
                _, ch, _ = letters[n]
                y = ord(ch) - ord("a")
                s = (off + n // length) % 26
                p = (y - s) % 26
                pc = chr(p + ord("a"))
                counts[pc] = counts.get(pc, 0) + 1
            score = chi_squared(counts, len(col_ns))
            if best_score is None or score < best_score:
                best_score, best_off = score, off
        key.append(best_off)
    return key


def decrypt(text, letters, key):
    length = len(key)
    out = list(text)
    for n, (idx, ch, is_upper) in enumerate(letters):
        y = ord(ch) - ord("a")
        s = (key[n % length] + n // length) % 26
        p = (y - s) % 26
        pc = chr(p + ord("a"))
        out[idx] = pc.upper() if is_upper else pc
    return "".join(out)


def solve(path):
    with open(path, encoding="utf-8") as fh:
        ct = fh.read()
    letters = letter_positions(ct)
    for length in range(1, 13):
        key = recover_key(letters, length)
        pt = decrypt(ct, letters, key)
        if "NCTF{" in pt:
            base = "".join(chr(k + ord("a")) for k in key)
            flag = pt[pt.index("NCTF{") : pt.index("}", pt.index("NCTF{")) + 1]
            print(f"[+] key length {length}, base key '{base}'")
            print("[+] FLAG =", flag)
            return flag
    raise SystemExit("no key length produced the flag marker")


if __name__ == "__main__":
    default = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "cipher.txt"
    )
    solve(sys.argv[1] if len(sys.argv) > 1 else default)
