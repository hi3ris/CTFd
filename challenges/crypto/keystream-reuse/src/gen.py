#!/usr/bin/env python3
"""Deterministic generator for the 'keystream-reuse' challenge.

A batch of English messages is XOR-encrypted with one and the same keystream
(a many-time pad). One message carries the flag. Ciphertexts are shipped as hex
lines in messages.txt.
"""
import os
import random

SEED = 1337

MESSAGES = [
    "The quarterly logistics review is scheduled for the second week of March.",
    "Please remember to rotate the backup tapes before the end of every shift.",
    "Our field agents reported unusually heavy traffic near the eastern depot.",
    "The maintenance crew replaced the failing pump on the northern pipeline.",
    "All personnel must badge in through the main lobby starting next Monday.",
    "The weather station lost power again during the storm on Thursday evening.",
    "Shipping manifests should be filed in triplicate and archived off-site.",
    "The new intern keeps forgetting to lock the server cabinet after hours.",
    "Budget projections for the coming fiscal year look cautiously optimistic.",
    "The courier confirmed that the sealed package arrived at the safe house.",
    "Remember that the parking garage closes at midnight on public holidays.",
    "Our analysts flagged several anomalies in last month's access logs today.",
    "The bridge inspection was postponed because of the rising river levels.",
    "The vault code NCTF{never_reuse_a_one_time_pad_keystream} works.",
    "Kindly submit your travel reimbursement forms before the deadline passes.",
    "The generator ran for eleven hours straight before the technicians came.",
    "We upgraded the radios but reception in the basement is still very poor.",
    "The catering order for the retirement party was cancelled at short notice.",
    "Security cameras in the loading dock have been offline since last Tuesday.",
    "The board approved the acquisition after a lengthy afternoon discussion.",
    "Downloading the entire archive over the satellite link took most of a day.",
    "The librarian catalogued the donated manuscripts throughout the weekend.",
    "Ticket sales for the annual gala exceeded every expectation this season.",
    "The auditors requested copies of all invoices dated after the first of June.",
    "Nobody remembered to water the office plants during the long summer break.",
]


def main() -> None:
    rng = random.Random(SEED)
    maxlen = max(len(m) for m in MESSAGES)
    keystream = bytes(rng.getrandbits(8) for _ in range(maxlen))
    lines = []
    for m in MESSAGES:
        mb = m.encode()
        ct = bytes(a ^ b for a, b in zip(mb, keystream))
        lines.append(ct.hex())
    rng.shuffle(lines)  # hide which line is the flag

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "..", "messages.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"wrote messages.txt: {len(lines)} ciphertexts, keystream {maxlen} bytes")


if __name__ == "__main__":
    main()
