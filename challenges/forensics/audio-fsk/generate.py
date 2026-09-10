#!/usr/bin/env python3
"""
generate.py -- author-side generator for the "audio-fsk" forensics challenge.

Produces transmission.wav: a continuous-phase 2-FSK downlink carrying a custom
framed bitstream. This is NOT a UART/Bell-202 signal. The framing is invented:

  Physical layer
  --------------
    sample rate : 48000 Hz
    baud        : 96 symbols/sec  (exactly 500 samples per symbol)
    mark  (1)   : 1855 Hz
    space (0)   : 3145 Hz          (note: space tone is HIGHER than mark)
    modulation  : continuous-phase FSK (phase carried across symbols)
    bit order   : MSB-first within each byte
    NO start/stop bits, NO parity -- it is a raw contiguous bitstream.

  Frame layout (the bits, in transmission order)
  ----------------------------------------------
    [ PREAMBLE ]  0xAA x 12      -> clock/symbol recovery (alternating tones)
    [ SYNC     ]  0x9E 0x3A      -> frame delimiter; fixes byte alignment,
                                    bit polarity, and MSB-first order
    [ LEN      ]  1 byte  = N    -> number of PAYLOAD bytes that follow
    [ PAYLOAD  ]  N bytes        -> ASCII message containing the flag
    [ CRC      ]  1 byte         -> CRC-8, poly 0x07, init 0x00, no reflection,
                                    computed over LEN||PAYLOAD (length included)

A small amount of Gaussian noise + a gentle amplitude envelope are added so the
recording looks like a real capture, while keeping SNR high enough for a clean
per-symbol demod.

The flag is STATIC and lives only in the payload text -- this is a pure
downloadable-artifact forensics challenge (see anti-llm-guardrails.md exception).
"""
import wave
import struct
import numpy as np

# ---- parameters (the "secret" PHY) ----------------------------------------
SR        = 48000       # sample rate (Hz)
BAUD      = 96          # symbols per second  -> 500 samples/symbol
F_MARK    = 1855.0      # tone for bit '1' (Hz)
F_SPACE   = 3145.0      # tone for bit '0' (Hz)
AMPL      = 0.6         # peak amplitude of the tone
NOISE     = 0.006       # gaussian noise std-dev
SYNC      = bytes([0x9E, 0x3A])
PREAMBLE  = bytes([0xAA]) * 12
LEAD_SIL  = 0.35        # seconds of near-silence before the burst
TRAIL_SIL = 0.40        # seconds of near-silence after the burst

FLAG    = "CTF{c0nt1nu0us_ph4se_fsk_96baud_9e3a}"
PAYLOAD = ("SIGINT downlink 0x2217 :: frame recovered :: flag=" + FLAG +
           " :: end of transmission").encode("ascii")

OUT_WAV = "transmission.wav"


def crc8(data: bytes) -> int:
    """CRC-8, polynomial 0x07, init 0x00, no input/output reflection, xorout 0."""
    crc = 0x00
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ 0x07) & 0xFF
            else:
                crc = (crc << 1) & 0xFF
    return crc


def build_frame() -> bytes:
    n = len(PAYLOAD)
    assert 0 <= n <= 255, "payload too long for a single length byte"
    body = bytes([n]) + PAYLOAD
    crc = crc8(body)
    return PREAMBLE + SYNC + body + bytes([crc])


def bytes_to_bits_msb(data: bytes):
    """MSB-first bit stream."""
    for byte in data:
        for i in range(7, -1, -1):
            yield (byte >> i) & 1


def synth(bits) -> np.ndarray:
    """Continuous-phase 2-FSK synthesis."""
    spb = SR // BAUD  # samples per symbol (exact integer: 500)
    assert SR % BAUD == 0
    phase = 0.0
    dt = 1.0 / SR
    two_pi = 2.0 * np.pi
    chunks = []
    for bit in bits:
        f = F_MARK if bit == 1 else F_SPACE
        # advance phase continuously to avoid clicks at symbol boundaries
        t = np.arange(spb) * dt
        ph = phase + two_pi * f * t
        chunks.append(np.sin(ph))
        phase = (ph[-1] + two_pi * f * dt) % two_pi
    return np.concatenate(chunks) * AMPL


# ---- decoy: a faint, textbook Bell-202 (1200 baud, mark=1200/space=2200 Hz,
# standard UART 8N1, LSB-first) burst carrying a WRONG flag. It is placed in the
# trailing silence at low amplitude (below the solver's burst-detection
# threshold) so it never perturbs the primary decode, but a player who points
# minimodem at the file with default settings will lock onto it. Refutable in
# minutes: it uses exactly the standard parameters the primary link avoids and
# carries no CRC-framed structure. ------------------------------------------
DECOY_MARK  = 1200.0
DECOY_SPACE = 2200.0
DECOY_BAUD  = 1200
DECOY_AMPL  = 0.045
DECOY_TEXT  = "CTF{b3ll202_1200_8n1_is_the_decoy}".encode("ascii")


def synth_bell202_uart(data: bytes) -> np.ndarray:
    spb = SR // DECOY_BAUD
    phase, dt, two_pi = 0.0, 1.0 / SR, 2.0 * np.pi
    chunks = []

    def emit(bit):
        nonlocal phase
        f = DECOY_MARK if bit == 1 else DECOY_SPACE
        t = np.arange(spb) * dt
        ph = phase + two_pi * f * t
        chunks.append(np.sin(ph))
        phase = (ph[-1] + two_pi * f * dt) % two_pi

    for _ in range(16):   # idle marks
        emit(1)
    for byte in data:
        emit(0)                       # start bit
        for i in range(8):            # LSB-first
            emit((byte >> i) & 1)
        emit(1)                       # stop bit
    for _ in range(16):
        emit(1)
    return np.concatenate(chunks) * DECOY_AMPL


def main():
    frame = build_frame()
    bits = list(bytes_to_bits_msb(frame))
    tone = synth(bits)

    lead = np.zeros(int(SR * LEAD_SIL))
    gap = np.zeros(int(SR * 0.25))
    decoy = synth_bell202_uart(DECOY_TEXT)
    trail = np.zeros(int(SR * TRAIL_SIL))
    sig = np.concatenate([lead, tone, gap, decoy, trail])

    # gentle 5 ms fade in/out on the burst edges via the whole signal is fine;
    # add capture-like noise across everything
    rng = np.random.default_rng(0x5A17)
    sig = sig + rng.normal(0.0, NOISE, size=sig.shape)

    # normalise to safe 16-bit range
    peak = np.max(np.abs(sig))
    sig = sig / (peak * 1.02)
    pcm = np.int16(np.clip(sig, -1.0, 1.0) * 32767)

    with wave.open(OUT_WAV, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())

    dur = len(sig) / SR
    print(f"wrote {OUT_WAV}: {len(sig)} samples, {dur:.2f}s @ {SR} Hz")
    print(f"frame bytes = {len(frame)}  payload bytes = {len(PAYLOAD)}  "
          f"crc8 = 0x{crc8(bytes([len(PAYLOAD)])+PAYLOAD):02X}")
    print(f"flag = {FLAG}")


if __name__ == "__main__":
    main()
