#!/usr/bin/env python3
"""
Builder for 'obfuscated-strings'.

Ships an APK-like ZIP whose decompiled `StringFog.java` contains an obfuscated
byte array and the routine that turns it back into a string at runtime. The
flag is stored ONLY as that obfuscated array.

Per-byte obfuscation (encode), for index i over the flag bytes:

    x = (flag[i] + (i * 7 + 3)) & 0xFF
    x = ROL8(x, (i % 5) + 1)
    x ^= 0xA5
    data[i] = x

The runtime decode (shown in the Java) inverts each step.
"""

import zipfile

FLAG = "NCTF{r3v3rs3_th3_0bfusc4t0r_l00p}"


def rol8(v: int, r: int) -> int:
    r &= 7
    return ((v << r) | (v >> (8 - r))) & 0xFF if r else v & 0xFF


def encode(flag: str):
    out = []
    for i, ch in enumerate(flag.encode()):
        x = (ch + (i * 7 + 3)) & 0xFF
        x = rol8(x, (i % 5) + 1)
        x ^= 0xA5
        out.append(x)
    return out


MANIFEST = """<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.stashbox.app" android:versionCode="12" android:versionName="3.0">
    <application android:label="StashBox">
        <activity android:name="com.stashbox.app.MainActivity" android:exported="true"/>
    </application>
</manifest>
"""

STRINGFOG = """// Decompiled with jadx
package com.stashbox.app;

/* String obfuscation helper injected by the build plugin. */
public final class StringFog {{
    // obfuscated bytes for the license string
    private static final int[] DATA = new int[] {{
        {data}
    }};

    public static String unfog() {{
        byte[] out = new byte[DATA.length];
        for (int i = 0; i < DATA.length; i++) {{
            int x = DATA[i] ^ 0xA5;
            // rotate right by (i % 5) + 1
            int r = (i % 5) + 1;
            x = ((x >>> r) | (x << (8 - r))) & 0xFF;
            x = (x - (i * 7 + 3)) & 0xFF;
            out[i] = (byte) x;
        }}
        return new String(out);
    }}
}}
"""

MAIN = """// Decompiled with jadx
package com.stashbox.app;

import android.app.Activity;
import android.os.Bundle;

public class MainActivity extends Activity {
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        String license = StringFog.unfog();
        // license is checked against the server; value not stored in cleartext
    }
}
"""


def main():
    data = encode(FLAG)
    data_str = ", ".join(str(v) for v in data)
    with zipfile.ZipFile("app.apk", "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("AndroidManifest.xml", MANIFEST)
        z.writestr(
            "sources/com/stashbox/app/StringFog.java",
            STRINGFOG.format(data=data_str),
        )
        z.writestr("sources/com/stashbox/app/MainActivity.java", MAIN)
    print("wrote app.apk")
    assert FLAG not in open("app.apk", "rb").read().decode("latin-1")


if __name__ == "__main__":
    main()
