"""Generate a two-platform social-media export bundle.

A Telegram export holds a "backup key" post containing hex ciphertext. A
Mastodon export holds several accounts; the one that shares the SAME email as
the Telegram account reveals the handle used as the XOR key. Correlate by email,
then XOR-decrypt the hex to recover the flag.

Run:  python3 gen.py   (writes the two JSON files to the challenge root)
"""

import json
import os

FLAG = "NCTF{same_email_diff_handle_xor_pivot}"

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# The XOR key is the Mastodon username of the account sharing the pivot email.
XOR_KEY = "shadowscribe"
PIVOT_EMAIL = "s.scribe.228@mailtg.tg"


def xor_hex(plaintext: str, key: str) -> str:
    kb = key.encode()
    out = bytes(b ^ kb[i % len(kb)] for i, b in enumerate(plaintext.encode()))
    return out.hex()


TELEGRAM = {
    "platform": "telegram",
    "account": {
        "username": "night_courier_tg",
        "display_name": "Night Courier",
        "email_on_file": PIVOT_EMAIL,
        "joined": "2024-02-11",
    },
    "messages": [
        {
            "id": 1,
            "date": "2025-06-01T08:12:00Z",
            "text": "canal ouvert. restez discrets.",
        },
        {
            "id": 2,
            "date": "2025-06-02T21:40:00Z",
            "text": "livraison Lomé -> Kara confirmée",
        },
        {
            "id": 3,
            "date": "2025-06-03T02:05:00Z",
            "text": "backup key (ne pas perdre) hex=" + xor_hex(FLAG, XOR_KEY),
        },
        {"id": 4, "date": "2025-06-04T13:00:00Z", "text": "on efface tout dans 48h"},
    ],
}

MASTODON = {
    "platform": "mastodon.social",
    "accounts": [
        {
            "username": "lome_ultras",
            "display_name": "Ultras Lomé",
            "email": "fan.club@mailtg.tg",
            "note": "supporters, actus du foot togolais",
        },
        {
            "username": "shadowscribe",
            "display_name": "s.",
            "email": PIVOT_EMAIL,
            "note": "je change de pseudo partout, mais jamais d'adresse mail. opsec 101.",
        },
        {
            "username": "kara_market",
            "display_name": "Marché de Kara",
            "email": "market@mailtg.tg",
            "note": "petites annonces",
        },
    ],
}


def main() -> None:
    with open(os.path.join(ROOT, "telegram_export.json"), "w") as fh:
        json.dump(TELEGRAM, fh, ensure_ascii=False, indent=2)
    with open(os.path.join(ROOT, "mastodon_export.json"), "w") as fh:
        json.dump(MASTODON, fh, ensure_ascii=False, indent=2)
    print("wrote telegram_export.json and mastodon_export.json")


if __name__ == "__main__":
    main()
