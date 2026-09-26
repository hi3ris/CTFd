#!/usr/bin/env python3
"""
Builder for 'webview-bridge'.

Ships an APK-like ZIP with a WebView front-end (assets/app.js) and the native
JavaScript bridge it talks to (JsBridge.java). The page calls one bridge method
with a fixed token; the bridge decrypts an embedded blob keyed by that token.

    ks[i] = sha256(token || byte(i // 32))[i % 32]
    flag  = base64_decode(ENC) XOR ks

The token literal lives in app.js; ENC and the transform live in JsBridge.java.
The plaintext flag is never stored.
"""

import base64
import hashlib
import zipfile

FLAG = "NCTF{js_br1dg3_l34ks_th3_s3cr3t}"
TOKEN = "brg_2f9a_unlock_token"


def keystream(key: bytes, n: int) -> bytes:
    out = bytearray()
    j = 0
    while len(out) < n:
        out += hashlib.sha256(key + bytes([j])).digest()
        j += 1
    return bytes(out[:n])


def encrypt(flag: str) -> str:
    ks = keystream(TOKEN.encode(), len(flag))
    ct = bytes(b ^ k for b, k in zip(flag.encode(), ks))
    return base64.b64encode(ct).decode()


MANIFEST = """<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.hybrid.shop" android:versionCode="9" android:versionName="2.0">
    <application android:label="HybridShop">
        <activity android:name="com.hybrid.shop.WebActivity" android:exported="true"/>
    </application>
</manifest>
"""

APP_JS = """// assets/app.js  (bundled WebView front-end)
(function () {
  // The native layer is injected as `AndroidBridge`.
  function reveal() {
    // one fixed bridge token unlocks the premium secret
    var token = "brg_2f9a_unlock_token";
    var secret = AndroidBridge.getSecret(token);
    document.getElementById("out").innerText = secret;
  }
  window.addEventListener("load", function () {
    document.getElementById("btn").addEventListener("click", reveal);
  });
})();
"""

INDEX_HTML = """<!doctype html>
<html>
  <body>
    <button id="btn">Reveal</button>
    <pre id="out"></pre>
    <script src="app.js"></script>
  </body>
</html>
"""

BRIDGE = """// Decompiled with jadx
package com.hybrid.shop;

import android.util.Base64;
import android.webkit.JavascriptInterface;
import java.security.MessageDigest;

public class JsBridge {{
    // ciphertext of the premium secret, keyed by the bridge token
    private static final String ENC = "{enc}";

    @JavascriptInterface
    public String getSecret(String token) {{
        try {{
            byte[] ct = Base64.decode(ENC, Base64.DEFAULT);
            byte[] key = token.getBytes();
            byte[] out = new byte[ct.length];
            for (int i = 0; i < ct.length; i++) {{
                MessageDigest md = MessageDigest.getInstance("SHA-256");
                md.update(key);
                md.update(new byte[] {{ (byte) (i / 32) }});
                out[i] = (byte) (ct[i] ^ md.digest()[i % 32]);
            }}
            return new String(out);
        }} catch (Exception e) {{ return ""; }}
    }}
}}
"""

WEBACTIVITY = """// Decompiled with jadx
package com.hybrid.shop;

import android.app.Activity;
import android.os.Bundle;
import android.webkit.WebView;

public class WebActivity extends Activity {
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        WebView w = new WebView(this);
        w.getSettings().setJavaScriptEnabled(true);
        w.addJavascriptInterface(new JsBridge(), "AndroidBridge");
        w.loadUrl("file:///android_asset/index.html");
        setContentView(w);
    }
}
"""


def main():
    enc = encrypt(FLAG)
    with zipfile.ZipFile("hybridshop.apk", "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("AndroidManifest.xml", MANIFEST)
        z.writestr("assets/app.js", APP_JS)
        z.writestr("assets/index.html", INDEX_HTML)
        z.writestr("sources/com/hybrid/shop/JsBridge.java", BRIDGE.format(enc=enc))
        z.writestr("sources/com/hybrid/shop/WebActivity.java", WEBACTIVITY)
    print("wrote hybridshop.apk")
    assert FLAG not in open("hybridshop.apk", "rb").read().decode("latin-1")


if __name__ == "__main__":
    main()
