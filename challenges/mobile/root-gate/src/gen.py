#!/usr/bin/env python3
"""
Builder for 'root-gate'.

Ships an APK-like ZIP. The decompiled MainActivity has two branches:

  * if the device looks rooted/tampered -> shows a decoy string (a red herring)
  * otherwise -> derives a key from the build constant RELEASE_CHANNEL and
    decrypts the real payload

The real payload is stored ONLY as base64 ciphertext in strings.xml:

    keystream[i] = sha256(RELEASE_CHANNEL_bytes + bytes([i // 32]))[i % 32]
    ct = flag XOR keystream

RELEASE_CHANNEL is a hardcoded constant, so the gate is trivially bypassed by
reading the code: the constant IS the key.
"""

import base64
import hashlib
import zipfile

FLAG = "NCTF{r00t_g4te_const_is_th3_k3y}"
RELEASE_CHANNEL = "prod-ch_88f2a"
DECOY = "NCTF{n1ce_try_but_r00ted}"  # single decoy shown on the tamper path


def keystream(key: bytes, n: int) -> bytes:
    out = bytearray()
    j = 0
    while len(out) < n:
        out += hashlib.sha256(key + bytes([j])).digest()
        j += 1
    return bytes(out[:n])


def encrypt(flag: str) -> str:
    ks = keystream(RELEASE_CHANNEL.encode(), len(flag))
    ct = bytes(b ^ k for b, k in zip(flag.encode(), ks))
    return base64.b64encode(ct).decode()


MANIFEST = """<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.securebank.app" android:versionCode="21" android:versionName="5.1">
    <application android:label="SecureBank">
        <activity android:name="com.securebank.app.MainActivity" android:exported="true"/>
    </application>
</manifest>
"""

STRINGS = """<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="app_name">SecureBank</string>
    <string name="secure_payload">{ct}</string>
</resources>
"""

BUILDCONFIG = """// Decompiled with jadx
package com.securebank.app;

public final class BuildConfig {{
    public static final String BUILD_TYPE = "release";
    public static final String RELEASE_CHANNEL = "{channel}";
}}
"""

MAIN = """// Decompiled with jadx
package com.securebank.app;

import android.app.Activity;
import android.os.Bundle;
import android.util.Base64;
import java.security.MessageDigest;

public class MainActivity extends Activity {{
    private boolean isTampered() {{
        // checks for su, Magisk, test-keys, frida... (elided)
        return RootBeer.check(this);
    }}

    protected void onCreate(Bundle b) {{
        super.onCreate(b);
        if (isTampered()) {{
            // dead-end shown to rooted devices
            show("{decoy}");
            return;
        }}
        try {{
            byte[] key = BuildConfig.RELEASE_CHANNEL.getBytes();
            byte[] ct = Base64.decode(getString(R.string.secure_payload), 0);
            byte[] out = new byte[ct.length];
            for (int i = 0; i < ct.length; i++) {{
                MessageDigest md = MessageDigest.getInstance("SHA-256");
                md.update(key);
                md.update(new byte[] {{ (byte) (i / 32) }});
                byte ks = md.digest()[i % 32];
                out[i] = (byte) (ct[i] ^ ks);
            }}
            show(new String(out));   // the real unlock code
        }} catch (Exception e) {{ }}
    }}

    private void show(String s) {{ /* renders to a TextView */ }}
}}
"""


def main():
    ct = encrypt(FLAG)
    with zipfile.ZipFile("securebank.apk", "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("AndroidManifest.xml", MANIFEST)
        z.writestr("res/values/strings.xml", STRINGS.format(ct=ct))
        z.writestr(
            "sources/com/securebank/app/BuildConfig.java",
            BUILDCONFIG.format(channel=RELEASE_CHANNEL),
        )
        z.writestr(
            "sources/com/securebank/app/MainActivity.java",
            MAIN.format(decoy=DECOY),
        )
    print("wrote securebank.apk")
    assert FLAG not in open("securebank.apk", "rb").read().decode("latin-1")


if __name__ == "__main__":
    main()
