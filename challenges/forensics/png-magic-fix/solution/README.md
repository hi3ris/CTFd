# png-magic-fix — writeup

**Category:** forensics · **Difficulty:** beginner
**Flag:** `NCTF{png_m4gic_byt3s_r3st0r3d}` (static)

## One-line summary

The PNG signature has been zeroed out; restore it and read the flag from a
`tEXt` metadata chunk.

## Technique

Every PNG begins with the fixed 8-byte signature
`89 50 4E 47 0D 0A 1A 0A`. In `evidence.png` those 8 bytes are `00`, so viewers
reject the file even though every chunk after it is valid. This is a classic
"fix the header magic" carve.

## Step by step

1. Inspect the first bytes: `xxd evidence.png | head`. They are all zeros where a
   PNG signature should be.
2. Overwrite bytes 0–7 with the canonical PNG signature.
3. The file now opens. The image is a flat teal square — a decoy; the answer is
   in the metadata.
4. Read the `tEXt` chunks (`exiftool fixed.png`, `pnginfo`, or parse manually).
   The `Comment` keyword holds the flag.

## Run the reference solver

```
python3 solve.py ../evidence.png
```

It repairs the signature in memory and prints the `Comment` chunk value.

## Flag

`NCTF{png_m4gic_byt3s_r3st0r3d}`
