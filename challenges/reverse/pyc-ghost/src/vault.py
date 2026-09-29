"""vault -- reverse challenge source (compiled to vault.pyc; not shipped).

The flag is never stored in plaintext. DATA holds flag[i] ^ keystream[i], where
the keystream comes from a linear congruential generator seeded with SEED. The
program reconstructs the expected flag only to compare it with the user's guess.
"""

SEED = 0x1337
MUL = 1103515245
ADD = 12345
MASK = 0x7FFFFFFF

DATA = [
    35,
    2,
    93,
    126,
    214,
    144,
    42,
    42,
    66,
    158,
    25,
    83,
    5,
    44,
    8,
    182,
    154,
    253,
    26,
    56,
    4,
    224,
    139,
    52,
    163,
    227,
    114,
    138,
    235,
    161,
    100,
    234,
]


def _ks(n):
    x = SEED
    for _ in range(n):
        x = (x * MUL + ADD) & MASK
        yield (x >> 16) & 0xFF


def unlock():
    return bytes(d ^ k for d, k in zip(DATA, _ks(len(DATA))))


def main():
    try:
        guess = input("flag? ").strip()
    except EOFError:
        return
    if guess.encode() == unlock():
        print("[+] correct")
    else:
        print("[-] nope")


if __name__ == "__main__":
    main()
