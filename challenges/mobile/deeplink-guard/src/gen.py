#!/usr/bin/env python3
"""
Builder for 'deeplink-guard' (iOS-style bundle).

Ships a .ipa-like ZIP (VaultApp.ipa) containing:

  * Payload/VaultApp.app/Info.plist  -> registers the custom URL scheme + the
    validation constants the router checks
  * Payload/VaultApp.app/Secrets.plist -> base64 ciphertext of the flag
  * Payload/VaultApp.app/DeepLinkRouter.swift -> decompiled router pseudocode

The router only unlocks when it receives the exact deeplink

    vaultapp://unlock/grant?code=<REQUIRED_CODE>

and derives the decryption key from the canonical form of that URL:

    canonical = "vaultapp://unlock/grant?code=" + REQUIRED_CODE
    ks[i]     = sha256(canonical || byte(i // 32))[i % 32]
    flag      = ct XOR ks

Every constant (scheme, host, path, code) ships in the plist/Swift, so the
winning URI is fully reconstructable statically.
"""

import base64
import hashlib
import zipfile

FLAG = "NCTF{d33plink_1ntent_extr4_pwn}"
SCHEME = "vaultapp"
HOST = "unlock"
PATH = "grant"
REQUIRED_CODE = "s3cr3t-grant-0x5f"


def canonical() -> str:
    return f"{SCHEME}://{HOST}/{PATH}?code={REQUIRED_CODE}"


def keystream(key: bytes, n: int) -> bytes:
    out = bytearray()
    j = 0
    while len(out) < n:
        out += hashlib.sha256(key + bytes([j])).digest()
        j += 1
    return bytes(out[:n])


def encrypt(flag: str) -> str:
    ks = keystream(canonical().encode(), len(flag))
    ct = bytes(b ^ k for b, k in zip(flag.encode(), ks))
    return base64.b64encode(ct).decode()


INFO_PLIST = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleIdentifier</key>
    <string>com.example.vaultapp</string>
    <key>CFBundleName</key>
    <string>VaultApp</string>
    <key>CFBundleShortVersionString</key>
    <string>2.3.0</string>
    <key>CFBundleURLTypes</key>
    <array>
        <dict>
            <key>CFBundleURLName</key>
            <string>com.example.vaultapp.deeplink</string>
            <key>CFBundleURLSchemes</key>
            <array>
                <string>{scheme}</string>
            </array>
        </dict>
    </array>
</dict>
</plist>
"""

SECRETS_PLIST = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>grant_ciphertext</key>
    <string>{ct}</string>
    <key>algo</key>
    <string>sha256-keystream-xor</string>
</dict>
</plist>
"""

ROUTER_SWIFT = """// Reconstructed from Hopper pseudocode
import Foundation
import CryptoKit

enum DeepLinkRouter {{
    static let kScheme = "{scheme}"
    static let kHost   = "{host}"
    static let kPath   = "/{path}"
    static let kCode   = "{code}"   // required ?code= value

    // Only this exact deeplink unlocks the grant screen.
    static func handle(_ url: URL) -> String? {{
        guard url.scheme == kScheme else {{ return nil }}
        guard url.host == kHost else {{ return nil }}
        guard url.path == kPath else {{ return nil }}
        let comps = URLComponents(url: url, resolvingAgainstBaseURL: false)
        let code = comps?.queryItems?.first {{ $0.name == "code" }}?.value
        guard code == kCode else {{ return nil }}

        // key = the canonical deeplink string
        let canonical = "\\(kScheme)://\\(kHost)/\\(kPath.dropFirst())?code=\\(kCode)"
        let ct = Data(base64Encoded: Secrets.grantCiphertext)!
        var out = [UInt8]()
        let keyBytes = Array(canonical.utf8)
        for i in 0..<ct.count {{
            var h = SHA256()
            h.update(data: Data(keyBytes))
            h.update(data: Data([UInt8(i / 32)]))
            let ks = Array(h.finalize())[i % 32]
            out.append(ct[i] ^ ks)
        }}
        return String(bytes: out, encoding: .utf8)   // the grant code
    }}
}}
"""


def main():
    ct = encrypt(FLAG)
    base = "Payload/VaultApp.app/"
    with zipfile.ZipFile("VaultApp.ipa", "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(base + "Info.plist", INFO_PLIST.format(scheme=SCHEME))
        z.writestr(base + "Secrets.plist", SECRETS_PLIST.format(ct=ct))
        z.writestr(
            base + "DeepLinkRouter.swift",
            ROUTER_SWIFT.format(
                scheme=SCHEME, host=HOST, path=PATH, code=REQUIRED_CODE
            ),
        )
    print("wrote VaultApp.ipa")
    print("winning deeplink:", canonical())
    assert FLAG not in open("VaultApp.ipa", "rb").read().decode("latin-1")


if __name__ == "__main__":
    main()
