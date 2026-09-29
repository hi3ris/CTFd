"""Decode the DTMF tones in the shipped WAV back into the flag.

Splits the audio into tone bursts by energy, runs the Goertzel algorithm at the
eight DTMF frequencies on each burst to identify the digit, then groups the
digits three at a time into flag bytes.
"""

import math
import os
import struct
import wave

ART = os.path.join(os.path.dirname(__file__), "..", "dial.wav")

LOW = [697, 770, 852, 941]
HIGH = [1209, 1336, 1477, 1633]
TABLE = {
    (697, 1209): "1",
    (697, 1336): "2",
    (697, 1477): "3",
    (770, 1209): "4",
    (770, 1336): "5",
    (770, 1477): "6",
    (852, 1209): "7",
    (852, 1336): "8",
    (852, 1477): "9",
    (941, 1336): "0",
}


def goertzel(samples, rate, freq):
    n = len(samples)
    k = int(0.5 + n * freq / rate)
    w = 2 * math.pi * k / n
    coeff = 2 * math.cos(w)
    s_prev = s_prev2 = 0.0
    for x in samples:
        s = x + coeff * s_prev - s_prev2
        s_prev2 = s_prev
        s_prev = s
    return s_prev2**2 + s_prev**2 - coeff * s_prev * s_prev2


def bursts(samples, rate):
    """Yield lists of samples for each non-silent run, using windowed energy."""
    win = max(1, int(rate * 0.01))  # 10 ms windows
    peak = max((abs(s) for s in samples), default=1)
    thresh = (peak * 0.15) ** 2  # compare mean-square energy
    loud = []
    for start in range(0, len(samples), win):
        window = samples[start : start + win]
        energy = sum(s * s for s in window) / len(window)
        loud.append(energy > thresh)

    run = []
    for i, is_loud in enumerate(loud):
        if is_loud:
            run.extend(samples[i * win : (i + 1) * win])
        elif run:
            if len(run) > rate * 0.03:
                yield run
            run = []
    if run and len(run) > rate * 0.03:
        yield run


def decode_digit(seg, rate) -> str:
    lo = max(LOW, key=lambda f: goertzel(seg, rate, f))
    hi = max(HIGH, key=lambda f: goertzel(seg, rate, f))
    return TABLE[(lo, hi)]


def solve(path: str) -> str:
    with wave.open(path, "rb") as w:
        rate = w.getframerate()
        frames = w.readframes(w.getnframes())
    samples = list(struct.unpack("<%dh" % (len(frames) // 2), frames))

    digits = "".join(decode_digit(seg, rate) for seg in bursts(samples, rate))
    out = bytes(int(digits[i : i + 3]) for i in range(0, len(digits), 3))
    return out.decode()


if __name__ == "__main__":
    print(solve(ART))
