"""Recover the flag from the sample LSBs of the shipped WAV.

Reads the 16-bit mono samples, collects the low bit of each, packs them
MSB-first, and stops at the NUL terminator.
"""

import os
import struct
import wave

ART = os.path.join(os.path.dirname(__file__), "..", "tone.wav")


def solve(path: str) -> str:
    with wave.open(path, "rb") as w:
        assert w.getsampwidth() == 2 and w.getnchannels() == 1
        frames = w.readframes(w.getnframes())
    samples = struct.unpack("<%dh" % (len(frames) // 2), frames)
    bits = [s & 1 for s in samples]
    out = bytearray()
    for i in range(0, len(bits) - 7, 8):
        byte = 0
        for b in bits[i : i + 8]:
            byte = (byte << 1) | b
        if byte == 0:
            break
        out.append(byte)
    return out.decode()


if __name__ == "__main__":
    print(solve(ART))
