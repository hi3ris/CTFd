# POP1 -- partial protocol notes

Recovered from the decommissioned service. This describes the **framing** only.
The meaning of the `VERIFY` status code is intentionally missing -- infer it.

Connect with plain TCP (`nc {host} 9007`). The service speaks a small binary
framing in both directions.

## Frame layout

```
offset 0 : 0xAA               sync byte (every frame starts here)
offset 1 : opcode  (1 byte)
offset 2 : length  (2 bytes, LITTLE-ENDIAN)  -- number of 2-byte WORDS in the
                                                payload, NOT the byte count
offset 4 : payload (length * 2 bytes)
last     : checksum (1 byte) = XOR of the opcode byte and every payload byte
```

Two things that trip people up:

- **`length` counts words, not bytes.** A 64-byte payload has `length = 0x0020`
  encoded little-endian as `20 00`. If you treat it as a byte count you will
  desync immediately.
- **The checksum does not cover the sync or the length**, only the opcode byte
  and the payload bytes, XORed together into one byte. A frame with a bad
  checksum is answered with an error frame (`opcode 0xEE`, ascii reason).

Every payload the service sends or expects is an even number of bytes, so the
word count is always exact.

## Opcodes

| opcode | direction        | name    | payload                                   |
|--------|------------------|---------|-------------------------------------------|
| 0x11   | server -> client | BANNER  | ascii banner (sent once, on connect)      |
| 0x10   | client -> server | GETCT   | empty                                     |
| 0x12   | server -> client | CT      | `IV(16) || ciphertext` (ciphertext is a multiple of 16) |
| 0x20   | client -> server | VERIFY  | an `IV(16) || ciphertext` blob to test    |
| 0x21   | server -> client | STATUS  | one word (2 bytes): a status code         |
| 0x30   | client -> server | SUBMIT  | your recovered token plaintext            |
| 0x31   | server -> client | FLAG    | ascii flag                                |
| 0x32   | server -> client | NOPE    | ascii "wrong token"                       |
| 0x0xEE | server -> client | ERR     | ascii error reason                        |

The cipher is AES-128-CBC. The `STATUS` word is returned big-endian; you will
see it take exactly two distinct values across different `VERIFY` inputs. The
service never explains which is which, or what property of your blob it is
reacting to -- that is the crux of the challenge. Probe it: feed it the real
`CT` blob, feed it garbage, feed it the real blob with single bytes flipped in
different positions, and watch how the code moves.

## Worked framing example

A `GETCT` request (opcode `0x10`, empty payload, so `length = 0`, checksum =
`0x10 XOR <nothing> = 0x10`):

```
AA 10 00 00 10
```

The server's `CT` reply for a 64-byte blob would look like:

```
AA 12 20 00 <64 payload bytes> <checksum>
   ^opcode ^length=0x0020 words = 64 bytes
```

The token plaintext is 32 ascii bytes. When you have recovered it, strip the
PKCS#7 padding and send it back with `SUBMIT`.

## Note

The banner mentions a "legacy default token". It is not the token for your
instance. Submitting it is harmless (submissions are unlimited and unpenalised),
and it will simply be rejected.
