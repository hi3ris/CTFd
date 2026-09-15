# build/ — author tooling for forensics-dns-exfil

This challenge is a **static, downloadable forensics artifact** (no served
component, no Docker image, no per-team flag). Players receive only
`../capture.pcap`.

## Rebuild the capture

```
pip install scapy
python3 generate.py        # deterministic; writes ../capture.pcap
```

The build is seeded (`SEED`, and a fixed alphabet permutation seed), so the
produced pcap and its embedded flag are reproducible. Everything that defines the
challenge — custom base32 alphabet, the stolen note, and the flag — is at the top
of `generate.py`.

## Why there is no Dockerfile / flag.py HMAC path

* Not served: the answer lives entirely inside the captured packets, so there is
  nothing for a per-team oracle to verify. Per the guardrails, a static flag in
  `challenge.yml` is the correct choice for a pure downloadable forensics
  artifact.
* `../flag.py` still ships the standard `HMAC_SHA256(TEAM_SECRET, id)[:24]` helper
  for tooling uniformity, and documents how a served variant would regenerate the
  note.
