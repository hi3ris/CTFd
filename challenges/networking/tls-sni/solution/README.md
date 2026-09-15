# tls-sni — solution

**Summary:** Parse the TLS ClientHello structure, read the SNI hostname, and
hex-decode its labels into the flag.

## Technique

No cryptography — pure structure parsing:

```
record:    type(1)=0x16 | version(2) | length(2)
handshake: type(1)=0x01 | length(3)
body:      client_version(2) | random(32) | session_id(len+data)
           | cipher_suites(len2+data) | compression(len1+data)
           | extensions(len2 + [type(2) len(2) data]...)
```

The **server_name** extension (type `0x0000`) holds the SNI hostname. Its body
is `list_len(2) | name_type(1=host_name) | name_len(2) | hostname`.

The hostname is dot-separated **hex** labels followed by the fixed suffix
`.v.nctf`. Drop the suffix, join the hex labels, and hex-decode.

Decoys are planted in the client `random` field and in an ALPN entry, so a
`grep NCTF{` finds only fake data — you must actually parse to the SNI.

## Steps

1. Read `clienthello.bin`; validate record type `0x16` and handshake type `0x01`.
2. Skip client_version, random, session_id, cipher_suites, compression.
3. Iterate extensions; find type `0x0000`, read the hostname.
4. Strip the `.v.nctf` suffix, concatenate the hex labels, hex-decode.

Run:

```
python3 solution/solve.py
```

## Flag

```
NCTF{tls_client_hello_sni_extension_parsed_no_crypto}
```
