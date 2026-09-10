# Downlink brief (partial)

We intercepted a short RF downlink and recorded the demodulated audio baseband to
`transmission.wav`. Our SDR notes are incomplete — fill in the gaps from the
recording itself.

## What we know

* It is **binary FSK** (two tones, one per bit). The two tone frequencies are
  **not** the textbook Bell-103/Bell-202 pairs — measure them from the capture.
* The modulator is **continuous-phase** (no clicks at symbol boundaries), so
  edge-triggered symbol clocking behaves.
* There are **no UART start/stop bits and no parity** on the primary link. It is
  a raw, contiguous bitstream. (An off-the-shelf `minimodem` run assuming 8N1
  Bell-202 will *not* give you the payload.)
* We do not know which tone is `1` and which is `0`, nor the bit order — you must
  recover those.

## Frame structure (once you have the raw bits)

The bitstream is a single frame in this order:

```
  PREAMBLE   0xAA, repeated          alternating tones, for symbol/clock recovery
  SYNC       2 bytes, fixed value    frame delimiter (its value is fixed but not
                                      given here — you will see the same 16 bits
                                      appear right after the preamble)
  LEN        1 byte                  number of PAYLOAD bytes that follow
  PAYLOAD    LEN bytes               ASCII message; the flag is inside it
  CRC        1 byte                  CRC-8, polynomial 0x07, init 0x00, no
                                      reflection, computed over LEN || PAYLOAD
                                      (the length byte IS included in the CRC)
```

The SYNC word is what lets you resolve the two unknowns: try both tone→bit
polarities and both bit orders, and only one lines the preamble up with a clean,
byte-aligned constant. The CRC then confirms you framed it correctly.

## Flag format

`CTF{...}` — lowercase letters, digits and underscores inside the braces.

## Note

There is a second, much fainter tone burst later in the recording. It is a
standard textbook FSK link and it decodes "too easily" — treat anything that
falls out of a default-settings tool with suspicion. The real downlink is the
loud, continuous-phase, non-standard one described above, and its payload is
CRC-verified.
