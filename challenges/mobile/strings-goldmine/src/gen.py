#!/usr/bin/env python3
"""
Builder for 'strings-goldmine'.

Produces an APK-like ZIP (app-release.apk) whose extracted files contain:

  * AndroidManifest.xml
  * res/values/strings.xml   -> holds <string name="enc_blob"> (base64)
  * sources/com/vault/app/BuildConfig.java -> holds API_SECRET

The flag is stored ONLY as `enc_blob`, computed as:

    enc_blob = base64( flag_bytes XOR repeat(API_SECRET) )

so the plaintext flag never appears in the bundle. Recovering it requires
reading the hardcoded API_SECRET out of BuildConfig and un-XORing enc_blob.
"""

import base64
import zipfile

FLAG = "NCTF{h4rdc0d3d_k3y_in_str1ngs_xml}"
API_SECRET = "sk_live_tg_0f4c9a1b7d2e5"


def xor(data: bytes, key: bytes) -> bytes:
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


def build_enc() -> str:
    ct = xor(FLAG.encode(), API_SECRET.encode())
    return base64.b64encode(ct).decode()


MANIFEST = """<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.vault.app" android:versionCode="7" android:versionName="1.4.2">
    <application android:label="@string/app_name" android:theme="@style/AppTheme">
        <activity android:name="com.vault.app.MainActivity" android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
</manifest>
"""

STRINGS = """<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="app_name">VaultPay</string>
    <string name="welcome">Welcome back to VaultPay</string>
    <string name="enc_blob">{enc}</string>
    <string name="support_email">support@vaultpay.example</string>
</resources>
"""

BUILDCONFIG = """// Decompiled with jadx
package com.vault.app;

public final class BuildConfig {{
    public static final boolean DEBUG = false;
    public static final String APPLICATION_ID = "com.vault.app";
    public static final String BUILD_TYPE = "release";
    public static final int VERSION_CODE = 7;
    public static final String VERSION_NAME = "1.4.2";
    // TODO: move this to the backend before GA. Ops keeps nagging us.
    public static final String API_SECRET = "{secret}";
}}
"""

MAINACTIVITY = """// Decompiled with jadx
package com.vault.app;

import android.os.Bundle;
import android.util.Base64;
import androidx.appcompat.app.AppCompatActivity;

public class MainActivity extends AppCompatActivity {
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        setContentView(R.layout.activity_main);
        // premium unlock token derived from the shipped config
        byte[] enc = Base64.decode(getString(R.string.enc_blob), Base64.DEFAULT);
        byte[] key = BuildConfig.API_SECRET.getBytes();
        byte[] out = new byte[enc.length];
        for (int i = 0; i < enc.length; i++) {
            out[i] = (byte) (enc[i] ^ key[i % key.length]);
        }
        // new String(out) is the premium token; unused in this build
    }
}
"""


def main():
    enc = build_enc()
    with zipfile.ZipFile("app-release.apk", "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("AndroidManifest.xml", MANIFEST)
        z.writestr("res/values/strings.xml", STRINGS.format(enc=enc))
        z.writestr(
            "sources/com/vault/app/BuildConfig.java",
            BUILDCONFIG.format(secret=API_SECRET),
        )
        z.writestr("sources/com/vault/app/MainActivity.java", MAINACTIVITY)
        z.writestr("resources.arsc", b"\x02\x00\x0c\x00")  # stub
    print("wrote app-release.apk")
    assert FLAG not in open("app-release.apk", "rb").read().decode("latin-1")


if __name__ == "__main__":
    main()
