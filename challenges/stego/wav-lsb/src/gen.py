"""Generate a 16-bit mono WAV whose sample LSBs encode the flag.

A quiet multi-tone carrier is synthesised, then the least significant bit of
each 16-bit sample is overwritten with the flag bits (MSB first per byte),
terminated by a NUL byte.
"""

import math
import os
import struct
import wave

FLAG = b"NCTF{wav_samples_leak_one_bit}"
RATE = 8000
DURATION_S = 1.5
OUT = os.path.join(os.path.dirname(__file__), "..", "tone.wav")


def carrier(n: int) -> list[int]:
    samples = []
    for i in range(n):
        t = i / RATE
        v = 0.3 * math.sin(2 * math.pi * 440 * t)
        v += 0.2 * math.sin(2 * math.pi * 660 * t)
        samples.append(int(v * 12000))
    return samples


def flag_bits(data: bytes):
    for byte in data:
        for i in range(7, -1, -1):
            yield (byte >> i) & 1


def main() -> None:
    n = int(RATE * DURATION_S)
    samples = carrier(n)
    for idx, bit in enumerate(flag_bits(FLAG + b"\x00")):
        s = samples[idx] & ~1
        samples[idx] = s | bit
    frames = b"".join(struct.pack("<h", s) for s in samples)
    with wave.open(OUT, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(frames)
    print("wrote", os.path.abspath(OUT))


if __name__ == "__main__":
    main()
