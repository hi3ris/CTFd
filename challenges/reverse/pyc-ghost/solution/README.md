# pyc-ghost — writeup

**Category:** reverse · **Difficulty:** medium
**Flag:** `NCTF{marsh4l_unp1ckl3d_th3_c0de}`

## Summary

The artifact is a marshalled CPython `.pyc`. The flag is never stored — it is
rebuilt from a data array XORed with an LCG keystream. Unmarshal the bytecode,
recover the routine, and run it.

## The technique

`grep NCTF{ vault.pyc` finds nothing. Unmarshalling the module (`.pyc` header is
16 bytes on CPython 3.7+, then `marshal.loads`) or decompiling it shows:

```python
DATA = [35, 2, 93, 126, 214, ...]        # flag[i] ^ keystream[i]

def _ks(n):
    x = 0x1337
    for _ in range(n):
        x = (x * 1103515245 + 12345) & 0x7FFFFFFF
        yield (x >> 16) & 0xFF

def unlock():
    return bytes(d ^ k for d, k in zip(DATA, _ks(len(DATA))))
```

`main()` only compares `unlock()` with your input, so the flag exists only
transiently at runtime.

## Solve

Reproduce the LCG and XOR it against `DATA`, or simply unmarshal the module,
exec it (the `__main__` guard stops `main()` from running), and call `unlock()`:

```
$ python3 solve.py ../vault.pyc
flag: NCTF{marsh4l_unp1ckl3d_th3_c0de}
```

Confirm against the module:

```
$ echo 'NCTF{marsh4l_unp1ckl3d_th3_c0de}' | python3 vault.pyc
flag? [+] correct
```

## Rebuilding

```
make          # compile src/vault.py -> ./vault.pyc
make verify   # confirm no plaintext flag, then run the solver
```

The `.pyc` is CPython-3.11 bytecode. `src/vault.py` and `src/gen.py` are
developer-only and are not shipped.
