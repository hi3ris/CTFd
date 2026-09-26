#!/usr/bin/env python3
"""
Builder for 'keystore-alias'.

Ships an APK-like ZIP with a custom keystore blob (assets/vault.keystore) and
the decompiled KeyDeriver.java that reads it.

Keystore binary format:

    magic   : 4 bytes  b"AKS1"
    count   : 1 byte
    entries (count of):
        alias_len : 1 byte
        alias     : alias_len bytes
        salt      : 16 bytes
        enc_len   : 2 bytes big-endian
        enc       : enc_len bytes

For each entry the app derives a per-alias key and XORs a keystream:

    master = sha256(alias || salt || PASSPHRASE).digest()
    ks[i]  = sha256(master || byte(i // 32))[i % 32]
    plain  = enc XOR ks

Only the "grant" alias holds the real flag; the "legacy" alias holds a single
decoy. PASSPHRASE is a hardcoded constant in KeyDeriver.java.
"""

import hashlib
import struct
import zipfile

FLAG = "NCTF{k3yst0r3_al14s_d3r1v4t10n}"
DECOY = "NCTF{wr0ng_al14s_try_ag41n}"
PASSPHRASE = "changeit_but_nobody_did_v3"

ENTRIES = [
    ("legacy", b"\x11" * 16, DECOY),
    ("grant", bytes(range(16, 32)), FLAG),
]


def keystream(master: bytes, n: int) -> bytes:
    out = bytearray()
    j = 0
    while len(out) < n:
        out += hashlib.sha256(master + bytes([j])).digest()
        j += 1
    return bytes(out[:n])


def encrypt(alias: str, salt: bytes, plain: str) -> bytes:
    master = hashlib.sha256(alias.encode() + salt + PASSPHRASE.encode()).digest()
    ks = keystream(master, len(plain))
    return bytes(b ^ k for b, k in zip(plain.encode(), ks))


def build_keystore() -> bytes:
    out = bytearray(b"AKS1")
    out.append(len(ENTRIES))
    for alias, salt, plain in ENTRIES:
        enc = encrypt(alias, salt, plain)
        out.append(len(alias))
        out += alias.encode()
        out += salt
        out += struct.pack(">H", len(enc))
        out += enc
    return bytes(out)


MANIFEST = """<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.enterprise.vault" android:versionCode="15" android:versionName="4.4">
    <application android:label="EntVault">
        <activity android:name="com.enterprise.vault.MainActivity" android:exported="true"/>
    </application>
</manifest>
"""

KEYDERIVER = """// Decompiled with jadx
package com.enterprise.vault;

import java.io.DataInputStream;
import java.security.MessageDigest;

public class KeyDeriver {{
    // shipped in the app; never rotated
    private static final String PASSPHRASE = "{passphrase}";

    // custom keystore format:
    //   magic "AKS1", count, then per entry:
    //   [aliasLen][alias][salt(16)][encLen(2 BE)][enc]
    // The app unlocks the "grant" alias.
    public static byte[] unlock(DataInputStream in, String wantAlias) throws Exception {{
        byte[] magic = new byte[4];
        in.readFully(magic);                 // "AKS1"
        int count = in.readUnsignedByte();
        for (int e = 0; e < count; e++) {{
            int al = in.readUnsignedByte();
            byte[] alias = new byte[al];
            in.readFully(alias);
            byte[] salt = new byte[16];
            in.readFully(salt);
            int enclen = in.readUnsignedShort();
            byte[] enc = new byte[enclen];
            in.readFully(enc);
            if (!new String(alias).equals(wantAlias)) continue;

            MessageDigest md = MessageDigest.getInstance("SHA-256");
            md.update(alias);
            md.update(salt);
            md.update(PASSPHRASE.getBytes());
            byte[] master = md.digest();

            byte[] out = new byte[enclen];
            for (int i = 0; i < enclen; i++) {{
                MessageDigest k = MessageDigest.getInstance("SHA-256");
                k.update(master);
                k.update(new byte[] {{ (byte) (i / 32) }});
                out[i] = (byte) (enc[i] ^ k.digest()[i % 32]);
            }}
            return out;   // for "grant" this is the license
        }}
        return null;
    }}
}}
"""


def main():
    blob = build_keystore()
    with zipfile.ZipFile("entvault.apk", "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("AndroidManifest.xml", MANIFEST)
        z.writestr("assets/vault.keystore", blob)
        z.writestr(
            "sources/com/enterprise/vault/KeyDeriver.java",
            KEYDERIVER.format(passphrase=PASSPHRASE),
        )
    print("wrote entvault.apk")
    assert FLAG not in open("entvault.apk", "rb").read().decode("latin-1")


if __name__ == "__main__":
    main()
