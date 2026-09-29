"""Encode the flag as a sequence of DTMF (touch-tone) digits in a WAV file.

Each flag byte becomes three decimal digits (000-255). Every digit is played as
its standard DTMF dual-tone pair, separated by short silences. Decoding the
tones back to digits and grouping them in threes recovers the flag bytes.
"""

import math
import os
import struct
import wave

FLAG = b"NCTF{dtmf_dialed_the_flag_home}"
RATE = 8000
TONE_S = 0.08
GAP_S = 0.05
AMP = 10000
OUT = os.path.join(os.path.dirname(__file__), "..", "dial.wav")

DTMF = {
    "1": (697, 1209),
    "2": (697, 1336),
    "3": (697, 1477),
    "4": (770, 1209),
    "5": (770, 1336),
    "6": (770, 1477),
    "7": (852, 1209),
    "8": (852, 1336),
    "9": (852, 1477),
    "0": (941, 1336),
}


def tone(f_low: int, f_high: int, n: int) -> list[int]:
    out = []
    for i in range(n):
        t = i / RATE
        v = 0.5 * math.sin(2 * math.pi * f_low * t)
        v += 0.5 * math.sin(2 * math.pi * f_high * t)
        out.append(int(v * AMP))
    return out


def main() -> None:
    digits = "".join(f"{b:03d}" for b in FLAG)
    n_tone = int(RATE * TONE_S)
    silence = [0] * int(RATE * GAP_S)

    samples: list[int] = list(silence)
    for d in digits:
        lo, hi = DTMF[d]
        samples += tone(lo, hi, n_tone)
        samples += silence

    frames = b"".join(struct.pack("<h", s) for s in samples)
    with wave.open(OUT, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(frames)
    print("wrote", os.path.abspath(OUT), "digits", len(digits))


if __name__ == "__main__":
    main()
