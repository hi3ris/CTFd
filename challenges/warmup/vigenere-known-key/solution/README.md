# vigenere-known-key -- solution

## TL;DR

Standard Vigenere with the key handed to you: `WARMUP`.

## Steps

1. For each letter, subtract the key letter's shift (repeating the key,
   skipping non-letters), mod 26.
2. Decrypting with `WARMUP` yields the flag directly.

Run `python3 solve.py`.

## Flag

`NCTF{vigenere_with_a_known_key}`
