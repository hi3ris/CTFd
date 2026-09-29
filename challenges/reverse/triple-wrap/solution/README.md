# triple-wrap — writeup

**Category:** reverse · **Difficulty:** easy
**Flag:** `NCTF{peel_b64_rot13_x0r_layers}`
**Decoy:** `NCTF{th1s_1s_n0t_th3_r34l_0ne}`

## Summary

The flag is embedded as a base64 blob that is three transform layers deep. The
binary unwraps it at runtime to compare against your input; peeling the layers
by hand recovers the flag.

## The technique

`strings chall | grep NCTF{` finds only the banner decoy. The real flag lives in
`blob`, built (author side) as:

```
blob = base64( xor( rot13(flag), key ) )
```

`unwrap()` in the binary reverses this before the `strcmp`:

```c
n = b64decode(blob, tmp);
out[i] = rot13c(tmp[i] ^ key[i % klen]);
```

Both `blob` and `key` (`wrapkey`) are plain strings in the file.

## Solve

Peel in reverse order:

1. base64-decode `blob`
2. XOR with the key
3. ROT13 (its own inverse)

The solver enumerates the binary's strings, tries each as the key against the
base64 candidate, and keeps the combination that yields `NCTF{...}`:

```
$ python3 solve.py ../chall
key : wrapkey
flag: NCTF{peel_b64_rot13_x0r_layers}
```

Check against the binary:

```
$ ./chall 'NCTF{peel_b64_rot13_x0r_layers}'
[+] correct!
```

## Rebuilding

```
make          # regenerate src/chall.c and compile ./chall
make verify   # confirm strings shows only the decoy, then run the solver
```
