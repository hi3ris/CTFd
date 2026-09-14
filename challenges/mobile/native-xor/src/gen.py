#!/usr/bin/env python3
"""
Builder for 'native-xor'.

Ships an APK-like ZIP that includes:

  * lib/arm64-v8a/decompiled_native.c  -> Hopper/Ghidra-style pseudocode of the
    JNI routine, including the full 256-byte substitution box SBOX and the XOR
    key bytes
  * assets/enc.bin -> the transformed flag bytes

Per-index transform used by the native check (encode):

    t = (flag[i] + i) & 0xFF
    t ^= KEY[i % len(KEY)]
    enc[i] = SBOX[t]

The pseudocode ships the exact SBOX and KEY, so the transform is invertible
statically. The plaintext flag is never stored.
"""

import zipfile

FLAG = "NCTF{n4t1v3_x0r_t4bl3_unr0ll3d}"
KEY = [0x13, 0x37, 0x42, 0x9A, 0x5C, 0xE1]


def make_sbox():
    # deterministic permutation via a small LCG shuffle (Fisher-Yates)
    box = list(range(256))
    state = 0x2545F4914F6CDD1D & 0xFFFFFFFF
    for i in range(255, 0, -1):
        state = (state * 1103515245 + 12345) & 0xFFFFFFFF
        j = state % (i + 1)
        box[i], box[j] = box[j], box[i]
    return box


def encode(flag: str, sbox):
    out = []
    for i, ch in enumerate(flag.encode()):
        t = (ch + i) & 0xFF
        t ^= KEY[i % len(KEY)]
        out.append(sbox[t])
    return bytes(out)


MANIFEST = """<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.game.native" android:versionCode="3" android:versionName="1.0">
    <application android:label="NativeGame">
        <activity android:name="com.game.native.MainActivity" android:exported="true"/>
    </application>
</manifest>
"""

NATIVE_C_HEADER = """/* Reconstructed from libnative.so with Ghidra.
 * JNI_checkFlag reads assets/enc.bin, then rebuilds the expected input.
 */
#include <stdint.h>
#include <string.h>

/* substitution box baked into the .rodata section */
static const uint8_t SBOX[256] = {{
{sbox}
}};

/* rolling xor key */
static const uint8_t KEY[{keylen}] = {{ {key} }};

/* the native code applied, per byte i of the flag:
 *     t = (flag[i] + i) & 0xff;
 *     t ^= KEY[i % {keylen}];
 *     enc[i] = SBOX[t];
 * and compared enc[] against assets/enc.bin.
 */
int JNI_checkFlag(const uint8_t *flag, int n, const uint8_t *enc) {{
    for (int i = 0; i < n; i++) {{
        uint8_t t = (uint8_t)(flag[i] + i);
        t ^= KEY[i % {keylen}];
        if (SBOX[t] != enc[i]) return 0;
    }}
    return 1;
}}
"""

MAIN = """// Decompiled with jadx
package com.game.native;

import android.app.Activity;
import android.os.Bundle;

public class MainActivity extends Activity {
    static { System.loadLibrary("native"); }
    public native boolean checkFlag(byte[] flag, byte[] enc);

    protected void onCreate(Bundle b) {
        super.onCreate(b);
        // reads assets/enc.bin and calls checkFlag(userInput, enc)
    }
}
"""


def fmt_sbox(box):
    lines = []
    for r in range(0, 256, 16):
        lines.append("    " + ", ".join("0x%02x" % v for v in box[r : r + 16]) + ",")
    return "\n".join(lines)


def main():
    sbox = make_sbox()
    enc = encode(FLAG, sbox)
    c_src = NATIVE_C_HEADER.format(
        sbox=fmt_sbox(sbox),
        key=", ".join("0x%02x" % v for v in KEY),
        keylen=len(KEY),
    )
    with zipfile.ZipFile("nativegame.apk", "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("AndroidManifest.xml", MANIFEST)
        z.writestr("lib/arm64-v8a/decompiled_native.c", c_src)
        z.writestr("assets/enc.bin", enc)
        z.writestr("sources/com/game/native/MainActivity.java", MAIN)
    print("wrote nativegame.apk")
    assert FLAG not in open("nativegame.apk", "rb").read().decode("latin-1")


if __name__ == "__main__":
    main()
