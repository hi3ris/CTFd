#!/usr/bin/env python3
"""
Builder for 'prefs-vault'.

Ships an APK-like ZIP that includes a captured SharedPreferences file
(shared_prefs/vault_prefs.xml) and the decompiled TokenStore.java that reads it.

The prefs store an encrypted session token and the per-install salt. The key is
derived from a hardcoded app pepper plus that salt, then RC4 is applied:

    key = sha256(PEPPER_bytes + salt_hex_bytes).digest()
    enc_token = base64( RC4(flag, key) )

Both the salt and the pepper ship with the app, so the token is recoverable
offline. The plaintext flag is never stored.
"""

import base64
import hashlib
import zipfile

FLAG = "NCTF{sh4r3dpr3fs_ar3_n0t_s3cur3}"
PEPPER = "app_pepper_v2_9c1f"
SALT_HEX = "a1b2c3d4e5f60718"


def rc4(key: bytes, data: bytes) -> bytes:
    s = list(range(256))
    j = 0
    for i in range(256):
        j = (j + s[i] + key[i % len(key)]) & 0xFF
        s[i], s[j] = s[j], s[i]
    out = bytearray()
    i = j = 0
    for b in data:
        i = (i + 1) & 0xFF
        j = (j + s[i]) & 0xFF
        s[i], s[j] = s[j], s[i]
        out.append(b ^ s[(s[i] + s[j]) & 0xFF])
    return bytes(out)


def encrypt(flag: str) -> str:
    key = hashlib.sha256(PEPPER.encode() + SALT_HEX.encode()).digest()
    return base64.b64encode(rc4(key, flag.encode())).decode()


MANIFEST = """<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.notes.vault" android:versionCode="4" android:versionName="1.1">
    <application android:label="QuickNotes" android:allowBackup="true">
        <activity android:name="com.notes.vault.MainActivity" android:exported="true"/>
    </application>
</manifest>
"""

PREFS = """<?xml version='1.0' encoding='utf-8' standalone='yes' ?>
<map>
    <boolean name="onboarded" value="true" />
    <string name="device_salt">{salt}</string>
    <string name="enc_token">{enc}</string>
    <long name="last_sync" value="1725900000000" />
    <int name="schema" value="2" />
</map>
"""

TOKENSTORE = """// Decompiled with jadx
package com.notes.vault;

import android.content.SharedPreferences;
import android.util.Base64;
import java.security.MessageDigest;

public class TokenStore {{
    // never rotated across builds; ops asked and were ignored
    private static final String PEPPER = "{pepper}";

    /* RC4 keystream cipher */
    static byte[] rc4(byte[] key, byte[] in) {{
        int[] s = new int[256];
        for (int i = 0; i < 256; i++) s[i] = i;
        int j = 0;
        for (int i = 0; i < 256; i++) {{
            j = (j + s[i] + (key[i % key.length] & 0xFF)) & 0xFF;
            int t = s[i]; s[i] = s[j]; s[j] = t;
        }}
        byte[] out = new byte[in.length];
        int i = 0; j = 0;
        for (int k = 0; k < in.length; k++) {{
            i = (i + 1) & 0xFF;
            j = (j + s[i]) & 0xFF;
            int t = s[i]; s[i] = s[j]; s[j] = t;
            out[k] = (byte) (in[k] ^ s[(s[i] + s[j]) & 0xFF]);
        }}
        return out;
    }}

    String readToken(SharedPreferences p) throws Exception {{
        String salt = p.getString("device_salt", "");
        MessageDigest md = MessageDigest.getInstance("SHA-256");
        md.update(PEPPER.getBytes());
        md.update(salt.getBytes());
        byte[] key = md.digest();
        byte[] enc = Base64.decode(p.getString("enc_token", ""), Base64.DEFAULT);
        return new String(rc4(key, enc));
    }}
}}
"""


def main():
    enc = encrypt(FLAG)
    with zipfile.ZipFile("quicknotes.apk", "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("AndroidManifest.xml", MANIFEST)
        z.writestr(
            "shared_prefs/vault_prefs.xml",
            PREFS.format(salt=SALT_HEX, enc=enc),
        )
        z.writestr(
            "sources/com/notes/vault/TokenStore.java",
            TOKENSTORE.format(pepper=PEPPER),
        )
    print("wrote quicknotes.apk")
    assert FLAG not in open("quicknotes.apk", "rb").read().decode("latin-1")


if __name__ == "__main__":
    main()
