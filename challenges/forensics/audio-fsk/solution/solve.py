#!/usr/bin/env python3
"""
solve.py -- reference solver for "audio-fsk".

Pure signal processing, numpy + stdlib only (no listening required).

Pipeline
--------
1. Load the mono 16-bit WAV.
2. Find the two FSK tones as the two dominant spectral peaks (FFT of the burst).
3. Build a per-sample tone decision (Goertzel power at each tone over a short
   sliding window) and recover the symbol period from the shortest transition
   run-lengths -> baud.
4. Slice the burst into symbols, majority-vote each symbol to a raw bit.
5. Resolve the two unknowns -- which tone is '1', and the byte alignment --
   by scanning for the invented SYNC word 0x9E3A under MSB-first order and
   both polarities.
6. Read LEN, PAYLOAD, CRC-8 (poly 0x07 over LEN||PAYLOAD) to verify, print flag.

Usage: python3 solve.py [path/to/transmission.wav]
"""
import sys
import wave
import numpy as np

SYNC = bytes([0x9E, 0x3A])


def load_wav(path):
    with wave.open(path, "rb") as w:
        assert w.getsampwidth() == 2, "expected 16-bit PCM"
        sr = w.getframerate()
        n = w.getnframes()
        raw = w.readframes(n)
        data = np.frombuffer(raw, dtype="<i2").astype(np.float64)
        if w.getnchannels() > 1:
            data = data.reshape(-1, w.getnchannels())[:, 0]
    return sr, data / 32768.0


def find_burst(sig, sr):
    """Return [start,end) sample indices of the energetic burst."""
    win = max(1, sr // 200)  # ~5 ms
    env = np.convolve(np.abs(sig), np.ones(win) / win, mode="same")
    thr = 0.15 * env.max()
    idx = np.where(env > thr)[0]
    return idx[0], idx[-1] + 1


def top_two_tones(sig, sr):
    """Two dominant spectral peaks (in a sane audio band)."""
    N = len(sig)
    spec = np.abs(np.fft.rfft(sig * np.hanning(N)))
    freqs = np.fft.rfftfreq(N, 1.0 / sr)
    band = (freqs > 300) & (freqs < 8000)
    spec = np.where(band, spec, 0.0)
    binw = sr / N  # Hz per bin
    guard = int(round(200.0 / binw))  # null +/-200 Hz around a found peak
    peaks = []
    s = spec.copy()
    for _ in range(2):
        k = int(np.argmax(s))
        peaks.append(freqs[k])
        lo = max(0, k - guard)
        hi = min(len(s), k + guard)
        s[lo:hi] = 0.0
    return sorted(peaks)


def goertzel_power(block, f, sr):
    n = len(block)
    k = 2.0 * np.pi * f / sr
    coeff = 2.0 * np.cos(k)
    s0 = s1 = s2 = 0.0
    for x in block:
        s0 = x + coeff * s1 - s2
        s2 = s1
        s1 = s0
    return s1 * s1 + s2 * s2 - coeff * s1 * s2


def sliding_decision(sig, sr, f_lo, f_hi, win):
    """Per-window sign of (power(f_lo) - power(f_hi)); +1 => f_lo dominates."""
    n = len(sig)
    step = win // 4
    centers = np.arange(0, n - win, step)
    dec = np.zeros(len(centers), dtype=np.int8)
    for i, c in enumerate(centers):
        blk = sig[c:c + win]
        p_lo = goertzel_power(blk, f_lo, sr)
        p_hi = goertzel_power(blk, f_hi, sr)
        dec[i] = 1 if p_lo >= p_hi else 0
    return dec, centers, step


def estimate_spb(dec, step):
    """Shortest common transition spacing -> samples per symbol."""
    edges = np.where(np.diff(dec) != 0)[0]
    if len(edges) < 3:
        return None
    runs = np.diff(edges) * step
    runs = runs[runs > 0]
    # symbol period ~ the small, most-frequent run length (preamble alternates
    # every symbol so it dominates the short runs)
    lo = np.percentile(runs, 5)
    hi = np.percentile(runs, 40)
    core = runs[(runs >= lo) & (runs <= hi)]
    return float(np.median(core)) if len(core) else float(np.median(runs))


def crc8(data):
    crc = 0
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = ((crc << 1) ^ 0x07) & 0xFF if (crc & 0x80) else (crc << 1) & 0xFF
    return crc


def bits_to_bytes_msb(bits, offset):
    out = bytearray()
    i = offset
    while i + 8 <= len(bits):
        v = 0
        for b in bits[i:i + 8]:
            v = (v << 1) | b
        out.append(v)
        i += 8
    return bytes(out)


def try_decode(sym_bits):
    """Resolve polarity + byte alignment via SYNC, then parse frame."""
    for polarity in (0, 1):
        bits = [b ^ polarity for b in sym_bits]
        # search bit offsets for the SYNC word (MSB-first)
        as_str = "".join(map(str, bits))
        sync_str = "".join(f"{byte:08b}" for byte in SYNC)
        pos = as_str.find(sync_str)
        if pos < 0:
            continue
        after = pos + len(sync_str)
        frame = bits_to_bytes_msb(bits, after)
        if len(frame) < 2:
            continue
        n = frame[0]
        if n + 2 > len(frame):
            continue
        payload = frame[1:1 + n]
        crc = frame[1 + n]
        if crc8(bytes([n]) + payload) == crc:
            return payload, polarity, pos, True
        # tolerate a missing/garbled CRC but still surface a printable payload
    return None


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "../transmission.wav"
    sr, sig = load_wav(path)

    b0, b1 = find_burst(sig, sr)
    burst = sig[b0:b1]

    f_lo, f_hi = top_two_tones(burst, sr)
    print(f"[*] tones: {f_lo:.1f} Hz and {f_hi:.1f} Hz")

    win = int(sr / 250)  # ~4 ms analysis window for tone decision
    dec, centers, step = sliding_decision(burst, sr, f_lo, f_hi, win)
    spb = estimate_spb(dec, step)
    baud = sr / spb
    print(f"[*] samples/symbol ~ {spb:.1f}  -> baud ~ {baud:.2f}")

    def symbolize(spb_i, offset):
        sym = []
        s = offset
        while s + spb_i <= len(burst):
            seg = burst[s:s + spb_i]
            m0, m1 = spb_i // 3, 2 * spb_i // 3
            mid = seg[m0:m1]
            p_lo = goertzel_power(mid, f_lo, sr)
            p_hi = goertzel_power(mid, f_hi, sr)
            sym.append(1 if p_lo >= p_hi else 0)
            s += spb_i
        return sym

    # The run-length estimate is close; refine samples/symbol and the start
    # phase by searching for the setting that yields a CRC-valid frame.
    est = int(round(spb))
    res = None
    found_spb = None
    for cand in sorted(range(max(20, est - 60), est + 61), key=lambda c: abs(c - est)):
        for offset in range(0, cand, max(1, cand // 4)):
            sym_bits_lo = symbolize(cand, offset)
            r = try_decode(sym_bits_lo)
            if r:
                res, found_spb = r, cand
                break
        if res:
            break

    if not res:
        print("[!] decode failed")
        sys.exit(1)
    print(f"[*] locked samples/symbol = {found_spb}  (baud {sr/found_spb:.2f})")
    payload, polarity, pos, ok = res
    which = f_lo if polarity == 0 else f_hi
    print(f"[*] '1' bit maps to {which:.1f} Hz ; sync at symbol bit {pos}")
    print(f"[*] CRC-8 OK: {ok}")
    text = payload.decode("ascii", "replace")
    print(f"[*] payload: {text}")
    import re
    m = re.search(r"CTF\{[^}]*\}", text)
    print("\nFLAG:", m.group(0) if m else "(not found)")


if __name__ == "__main__":
    main()
