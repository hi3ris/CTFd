"""Embed the flag as zero-width characters inside an innocuous text note.

Each flag byte becomes 8 zero-width characters (MSB first): U+200B (zero-width
space) for a 0 bit and U+200C (zero-width non-joiner) for a 1 bit. The blob is
spliced into the middle of a normal-looking memo, invisible when rendered.
"""

import os

FLAG = "NCTF{zero_width_spaces_speak}"
ZERO = "​"  # zero-width space  -> bit 0
ONE = "‌"  # zero-width non-joiner -> bit 1
OUT = os.path.join(os.path.dirname(__file__), "..", "memo.txt")

COVER_HEAD = (
    "Internal memo\n"
    "-------------\n\n"
    "Team, thanks for the quick turnaround on the release notes."
)
COVER_TAIL = (
    " Please double-check the changelog before Friday and ping me with any\n"
    "questions. Great work this sprint.\n\n"
    "-- Ops\n"
)


def encode(text: str) -> str:
    out = []
    for byte in text.encode():
        for i in range(7, -1, -1):
            out.append(ONE if (byte >> i) & 1 else ZERO)
    return "".join(out)


def main() -> None:
    payload = encode(FLAG)
    content = COVER_HEAD + payload + COVER_TAIL
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(content)
    print("wrote", os.path.abspath(OUT))


if __name__ == "__main__":
    main()
